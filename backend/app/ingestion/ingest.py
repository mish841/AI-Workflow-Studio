from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from sqlalchemy import text

from app.database import engine
from app.ingestion.policy_chunker import chunk_policy_documents
from app.ingestion.requirement_parser import (
    EXPECTED_REQUIREMENT_IDS,
    parse_reference_requirements,
)
from app.ingestion.vector_store import (
    POLICY_COLLECTION,
    REQUIREMENT_COLLECTION,
    get_vector_store,
)
from app.services.policy_loader import POLICY_FILES, POLICY_TITLES, load_policy_text


def _row_id(collection_name: str, native_id: str) -> str:
    """LangChain PGVector ids are globally unique, so namespace by collection."""
    return f"{collection_name}:{native_id}"


def upsert_documents(store: PGVector, documents: list[Document], ids: list[str]) -> None:
    """Replace rows for these ids so re-ingestion does not duplicate vectors."""
    if not documents:
        return
    if len(documents) != len(ids):
        raise ValueError("documents and ids must be the same length")
    store.delete(ids=ids, collection_only=True)
    store.add_documents(documents, ids=ids)


def ingest_requirements(
    *,
    embeddings: Embeddings | None = None,
    collection_name: str = REQUIREMENT_COLLECTION,
) -> list[Document]:
    """Parse, embed, and upsert the 18 reference requirements."""
    documents = parse_reference_requirements()
    ids = [
        _row_id(collection_name, document.metadata["requirement_id"])
        for document in documents
    ]
    store = get_vector_store(collection_name, embeddings=embeddings)
    upsert_documents(store, documents, ids)
    return documents


def ingest_policies(
    *,
    embeddings: Embeddings | None = None,
    collection_name: str = POLICY_COLLECTION,
) -> list[Document]:
    """Chunk, embed, and upsert Policy V1 and V2 passages."""
    documents: list[Document] = []
    for version in ("v1", "v2"):
        documents.extend(
            chunk_policy_documents(
                load_policy_text(version),
                policy_version=version,
                filename=POLICY_FILES[version],
                title=POLICY_TITLES[version],
            )
        )
    ids = [
        _row_id(collection_name, document.metadata["chunk_id"])
        for document in documents
    ]
    store = get_vector_store(collection_name, embeddings=embeddings)
    upsert_documents(store, documents, ids)
    return documents


def _rows_for_collection(collection_name: str) -> list[dict]:
    query = text(
        """
        SELECT
            e.id,
            e.document,
            e.cmetadata,
            e.embedding IS NOT NULL AS has_embedding,
            vector_dims(e.embedding) AS embedding_dims
        FROM langchain_pg_embedding AS e
        JOIN langchain_pg_collection AS c
            ON c.uuid = e.collection_id
        WHERE c.name = :collection_name
        ORDER BY e.id
        """
    )
    with engine.connect() as connection:
        return list(
            connection.execute(query, {"collection_name": collection_name}).mappings()
        )


def verify_stored_requirements(
    collection_name: str = REQUIREMENT_COLLECTION,
) -> dict:
    """Inspect PGVector requirement rows without running similarity search."""
    rows = _rows_for_collection(collection_name)
    native_ids = [(row["cmetadata"] or {}).get("requirement_id") for row in rows]
    issues: list[str] = []

    if len(rows) != 18:
        issues.append(f"Expected 18 stored vectors, found {len(rows)}")
    if len(set(native_ids)) != len(native_ids):
        issues.append(f"Duplicate requirement ids: {native_ids}")
    if set(native_ids) != set(EXPECTED_REQUIREMENT_IDS):
        issues.append(
            f"Stored ids {sorted(str(item) for item in native_ids)} "
            "do not match expected requirement ids"
        )

    for row in rows:
        metadata = row["cmetadata"] or {}
        requirement_id = metadata.get("requirement_id")
        if not (row["document"] or "").strip():
            issues.append(f"{requirement_id} has empty content")
        if not row["has_embedding"]:
            issues.append(f"{requirement_id} is missing an embedding")
        elif not row["embedding_dims"] or row["embedding_dims"] <= 0:
            issues.append(f"{requirement_id} has an invalid embedding")
        if row["id"] != _row_id(collection_name, requirement_id or ""):
            issues.append(f"{row['id']} does not match namespaced requirement id")
        if not metadata.get("source_file"):
            issues.append(f"{row['id']} missing source_file")
        if not metadata.get("category"):
            issues.append(f"{row['id']} missing category")

    return {
        "collection": collection_name,
        "count": len(rows),
        "ids": native_ids,
        "ok": not issues,
        "issues": issues,
        "rows": [
            {
                "id": (row["cmetadata"] or {}).get("requirement_id") or row["id"],
                "content_preview": (row["document"] or "")[:80],
                "has_embedding": bool(row["has_embedding"]),
                "embedding_dims": row["embedding_dims"],
                "metadata": row["cmetadata"],
            }
            for row in rows
        ],
    }


def verify_stored_policies(collection_name: str = POLICY_COLLECTION) -> dict:
    """Inspect policy passage rows, including version isolation metadata."""
    rows = _rows_for_collection(collection_name)
    native_ids = [(row["cmetadata"] or {}).get("chunk_id") for row in rows]
    issues: list[str] = []
    versions = {((row["cmetadata"] or {}).get("policy_version")) for row in rows}

    if not rows:
        issues.append("No policy passages stored")
    if len(set(native_ids)) != len(native_ids):
        issues.append(f"Duplicate chunk ids: {native_ids}")
    if versions != {"v1", "v2"}:
        issues.append(f"Expected both policy versions, found {sorted(v for v in versions if v)}")

    for row in rows:
        metadata = row["cmetadata"] or {}
        if row["id"] != _row_id(collection_name, metadata.get("chunk_id") or ""):
            issues.append(f"{row['id']} does not match namespaced chunk id")
        if metadata.get("policy_version") not in {"v1", "v2"}:
            issues.append(f"{row['id']} missing policy_version")
        if not metadata.get("source_file"):
            issues.append(f"{row['id']} missing source_file")
        if not metadata.get("section_title"):
            issues.append(f"{row['id']} missing section_title")
        if not (row["document"] or "").strip():
            issues.append(f"{row['id']} has empty content")
        if not row["has_embedding"]:
            issues.append(f"{row['id']} is missing an embedding")

        text = row["document"] or ""
        version = metadata.get("policy_version")
        if version == "v1" and "twenty-four (24) hours" in text:
            issues.append(f"{row['id']} looks like V2 termination language stored as V1")
        if version == "v2" and "thirty (30) days" in text:
            issues.append(f"{row['id']} looks like V1 termination language stored as V2")

    return {
        "collection": collection_name,
        "count": len(rows),
        "ids": native_ids,
        "versions": sorted(v for v in versions if v),
        "ok": not issues,
        "issues": issues,
        "rows": [
            {
                "id": row["id"],
                "content_preview": (row["document"] or "")[:80],
                "has_embedding": bool(row["has_embedding"]),
                "embedding_dims": row["embedding_dims"],
                "metadata": row["cmetadata"],
            }
            for row in rows
        ],
    }


def vector_store_status() -> dict:
    requirements = verify_stored_requirements()
    policies = verify_stored_policies()
    return {
        "pgvector": True,
        "requirements": {
            "ok": requirements["ok"],
            "count": requirements["count"],
            "issues": requirements["issues"],
        },
        "policies": {
            "ok": policies["ok"],
            "count": policies["count"],
            "versions": policies["versions"],
            "issues": policies["issues"],
        },
    }
