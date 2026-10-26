from __future__ import annotations

from langchain_core.documents import Document
from sqlalchemy import text

from app.database import engine
from app.ingestion.requirement_parser import (
    EXPECTED_REQUIREMENT_IDS,
    parse_reference_requirements,
)
from app.ingestion.vector_store import COLLECTION_NAME, get_vector_store


def ingest_requirements() -> list[Document]:
    """Parse, embed, and upsert the 18 reference requirements."""
    documents = parse_reference_requirements()
    ids = [document.metadata["requirement_id"] for document in documents]
    store = get_vector_store()
    store.add_documents(documents, ids=ids)
    return documents


def verify_stored_requirements() -> dict:
    """Inspect PGVector rows without running similarity search."""
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
        rows = connection.execute(
            query, {"collection_name": COLLECTION_NAME}
        ).mappings().all()

    ids = [row["id"] for row in rows]
    issues: list[str] = []

    if len(rows) != 18:
        issues.append(f"Expected 18 stored vectors, found {len(rows)}")
    if len(set(ids)) != len(ids):
        issues.append(f"Duplicate embedding ids: {ids}")
    if set(ids) != set(EXPECTED_REQUIREMENT_IDS):
        issues.append(
            f"Stored ids {sorted(ids)} do not match expected requirement ids"
        )

    for row in rows:
        if not (row["document"] or "").strip():
            issues.append(f"{row['id']} has empty content")
        if not row["has_embedding"]:
            issues.append(f"{row['id']} is missing an embedding")
        elif not row["embedding_dims"] or row["embedding_dims"] <= 0:
            issues.append(f"{row['id']} has an invalid embedding")

        metadata = row["cmetadata"] or {}
        if metadata.get("requirement_id") != row["id"]:
            issues.append(f"{row['id']} metadata.requirement_id mismatch")
        if not metadata.get("source_file"):
            issues.append(f"{row['id']} missing source_file")
        if not metadata.get("category"):
            issues.append(f"{row['id']} missing category")

    return {
        "count": len(rows),
        "ids": ids,
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
