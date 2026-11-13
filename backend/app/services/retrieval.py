from __future__ import annotations

from collections.abc import Callable
from typing import Optional

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.ingestion.vector_store import (
    POLICY_COLLECTION,
    REQUIREMENT_COLLECTION,
    get_vector_store,
)
from app.models.evaluation import (
    PolicyVersion,
    RetrievedPassage,
    RetrievalHit,
)

RetrieverFn = Callable[[str, int, Optional[dict]], list[tuple[Document, float]]]


def _hits_from_docs(pairs: list[tuple[Document, float]]) -> list[RetrievalHit]:
    hits: list[RetrievalHit] = []
    for document, distance in pairs:
        metadata = document.metadata or {}
        hits.append(
            RetrievalHit(
                id=str(
                    metadata.get("chunk_id")
                    or metadata.get("requirement_id")
                    or document.id
                    or ""
                ),
                text=document.page_content,
                distance=float(distance) if distance is not None else None,
                metadata=metadata,
            )
        )
    return hits


def _store_search(
    collection_name: str,
    query: str,
    k: int,
    metadata_filter: dict | None,
    embeddings: Embeddings | None,
) -> list[tuple[Document, float]]:
    store = get_vector_store(collection_name, embeddings=embeddings)
    return store.similarity_search_with_score(
        query,
        k=k,
        filter=metadata_filter,
    )


def search_requirements(
    query: str,
    *,
    k: int = 5,
    embeddings: Embeddings | None = None,
    search: RetrieverFn | None = None,
    collection_name: str = REQUIREMENT_COLLECTION,
) -> list[RetrievalHit]:
    if not query.strip():
        raise ValueError("query must not be empty")
    search_fn = search or (
        lambda q, top_k, metadata_filter: _store_search(
            collection_name, q, top_k, metadata_filter, embeddings
        )
    )
    return _hits_from_docs(search_fn(query, k, None))


def search_policy_passages(
    query: str,
    policy_version: PolicyVersion,
    *,
    k: int = 4,
    embeddings: Embeddings | None = None,
    search: RetrieverFn | None = None,
    collection_name: str = POLICY_COLLECTION,
) -> list[RetrievalHit]:
    if not query.strip():
        raise ValueError("query must not be empty")
    metadata_filter = {"policy_version": policy_version}
    search_fn = search or (
        lambda q, top_k, filt: _store_search(
            collection_name, q, top_k, filt, embeddings
        )
    )
    hits = _hits_from_docs(search_fn(query, k, metadata_filter))
    mixed = [
        hit
        for hit in hits
        if hit.metadata.get("policy_version") not in {None, policy_version}
    ]
    if mixed:
        raise RuntimeError(
            f"Policy retrieval mixed versions for {policy_version}: "
            f"{[hit.id for hit in mixed]}"
        )
    return hits


def passages_for_requirement(
    requirement_text: str,
    policy_version: PolicyVersion,
    *,
    k: int = 4,
    embeddings: Embeddings | None = None,
    search: RetrieverFn | None = None,
    collection_name: str = POLICY_COLLECTION,
) -> list[RetrievedPassage]:
    hits = search_policy_passages(
        requirement_text,
        policy_version,
        k=k,
        embeddings=embeddings,
        search=search,
        collection_name=collection_name,
    )
    passages: list[RetrievedPassage] = []
    for hit in hits:
        passages.append(
            RetrievedPassage(
                chunk_id=hit.id,
                source_document=str(hit.metadata.get("source_file") or ""),
                policy_version=policy_version,
                section_number=str(hit.metadata.get("section_number") or ""),
                section_title=str(hit.metadata.get("section_title") or ""),
                text=hit.text,
                distance=hit.distance,
                used_in_finding=False,
            )
        )
    return passages


def format_passages_for_prompt(passages: list[RetrievedPassage]) -> str:
    if not passages:
        return (
            "No policy passages were retrieved for this requirement. "
            "Do not invent quotes. Set needs_review to true."
        )
    blocks = []
    for index, passage in enumerate(passages, start=1):
        heading = (
            f"[Passage {index} | {passage.source_document} | "
            f"{passage.section_number}. {passage.section_title}]"
        )
        blocks.append(f"{heading}\n{passage.text}")
    return "\n\n".join(blocks)


def mark_used_passages(
    passages: list[RetrievedPassage],
    quote: str | None,
) -> list[RetrievedPassage]:
    if not quote or not quote.strip():
        return passages
    needle = quote.strip()
    return [
        passage.model_copy(update={"used_in_finding": needle in passage.text})
        for passage in passages
    ]
