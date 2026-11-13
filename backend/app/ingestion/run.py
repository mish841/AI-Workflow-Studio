"""Ingest Northstar reference requirements and policy passages into pgvector.

Usage (from backend/):

    python -m app.ingestion.run --parse-only
    python -m app.ingestion.run --requirements
    python -m app.ingestion.run --policies
    python -m app.ingestion.run --all
    python -m app.ingestion.run --eval-retrieval
"""

from __future__ import annotations

import argparse
import json


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse, embed, and inspect compliance retrieval collections."
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse and validate 18 requirements without calling OpenAI.",
    )
    parser.add_argument("--requirements", action="store_true")
    parser.add_argument("--policies", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--eval-retrieval",
        action="store_true",
        help="Score the independent query set and labeled-quote recovery. Uses embeddings, not chat.",
    )
    args = parser.parse_args()

    from app.ingestion.requirement_parser import parse_reference_requirements

    documents = parse_reference_requirements()
    print(f"Parsed {len(documents)} requirements:")
    for document in documents:
        print(
            f"  {document.metadata['requirement_id']} "
            f"({document.metadata['source_file']}, "
            f"{document.metadata['category']})"
        )

    if args.parse_only:
        return

    run_requirements = args.requirements or args.all or not (
        args.policies or args.eval_retrieval
    )
    run_policies = args.policies or args.all

    if run_requirements or run_policies or args.eval_retrieval:
        from app.ingestion.ingest import (
            ingest_policies,
            ingest_requirements,
            verify_stored_policies,
            verify_stored_requirements,
        )

    if run_requirements:
        ingest_requirements()
        result = verify_stored_requirements()
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
        if not result["ok"]:
            raise SystemExit("Requirement ingestion verification failed")
        print("Verification passed: 18 unique requirement vectors stored.")

    if run_policies:
        chunks = ingest_policies()
        print(f"Ingested {len(chunks)} policy passages.")
        result = verify_stored_policies()
        print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
        if not result["ok"]:
            raise SystemExit("Policy ingestion verification failed")
        print("Verification passed: policy passages stored for V1 and V2.")

    if args.eval_retrieval:
        from app.services.retrieval_eval import (
            evaluate_policy_evidence_coverage,
            evaluate_requirement_queries,
        )

        requirement_score = evaluate_requirement_queries()
        print("Requirement search:")
        print(
            json.dumps(
                {k: v for k, v in requirement_score.items() if k != "rows"},
                indent=2,
            )
        )
        for version in ("v1", "v2"):
            coverage = evaluate_policy_evidence_coverage(version)
            print(f"Policy {version} labeled-quote recovery:")
            print(
                json.dumps(
                    {k: v for k, v in coverage.items() if k != "rows"},
                    indent=2,
                )
            )


if __name__ == "__main__":
    main()
