from __future__ import annotations

import json
from pathlib import Path

from app.ingestion.requirement_parser import parse_reference_requirements
from app.services.compliance_evaluator import inventory_from_documents
from app.services.ground_truth import expected_for_policy
from app.services.retrieval import search_policy_passages, search_requirements
from app.models.evaluation import PolicyVersion


def default_query_set_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / "synthetic_data"
        / "evaluation"
        / "retrieval_queries.json"
    )


def load_retrieval_queries(path: Path | None = None) -> dict:
    query_path = path or default_query_set_path()
    return json.loads(query_path.read_text(encoding="utf-8"))


def evaluate_requirement_queries(
    *,
    k: int = 5,
    search=None,
) -> dict:
    """Score independently defined requirement searches. Does not call an LLM."""
    payload = load_retrieval_queries()
    rows = []
    hits = 0
    for item in payload["requirement_search"]:
        results = search_requirements(item["query"], k=k, search=search)
        top_ids = [hit.metadata.get("requirement_id") or hit.id for hit in results]
        expected = item["expected_requirement_ids"]
        matched = expected[0] in top_ids if expected else False
        rank = top_ids.index(expected[0]) + 1 if expected and expected[0] in top_ids else None
        if matched:
            hits += 1
        rows.append(
            {
                "id": item["id"],
                "query": item["query"],
                "expected": expected,
                "top_ids": top_ids,
                "hit": matched,
                "rank": rank,
            }
        )
    total = len(rows)
    return {
        "total": total,
        "hits": hits,
        "hit_rate": (hits / total) if total else 0.0,
        "rows": rows,
    }


def evaluate_policy_evidence_coverage(
    policy_version: PolicyVersion,
    *,
    k: int = 4,
    search=None,
) -> dict:
    """Check whether labeled quotes appear in retrieved passages.

    Ground-truth quotes are used only as a retrieval metric. They are not sent
    to the evaluator model.
    """
    expected = expected_for_policy(policy_version)
    inventory = inventory_from_documents(parse_reference_requirements())
    rows = []
    comparable = 0
    recovered = 0
    for requirement in inventory:
        label = expected[requirement.requirement_id]
        quote = label.get("expected_evidence")
        passages = search_policy_passages(
            requirement.text,
            policy_version,
            k=k,
            search=search,
        )
        blob = "\n".join(hit.text for hit in passages)
        found = bool(quote) and quote in blob
        if quote:
            comparable += 1
            if found:
                recovered += 1
        rows.append(
            {
                "requirement_id": requirement.requirement_id,
                "has_labeled_quote": bool(quote),
                "recovered_labeled_quote": found,
                "passage_ids": [hit.id for hit in passages],
            }
        )
    return {
        "policy_version": policy_version,
        "requirements": len(rows),
        "labeled_quotes": comparable,
        "recovered_labeled_quotes": recovered,
        "recovery_rate": (recovered / comparable) if comparable else 0.0,
        "direct_context_quote_availability": 1.0 if comparable else 0.0,
        "note": (
            "Direct-context evaluation always includes the full source policy, so "
            "labeled quotes that exist in the file are available. RAG recovery "
            "is the share of those quotes that appear in the top-k passages."
        ),
        "rows": rows,
    }
