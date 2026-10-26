"""Ingest Northstar reference requirements into pgvector.

Usage (from backend/):

    python -m app.ingestion.run
    python -m app.ingestion.run --parse-only
"""

from __future__ import annotations

import argparse
import json

from app.ingestion.requirement_parser import parse_reference_requirements


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse and embed compliance reference requirements."
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse and validate 18 requirements without calling OpenAI.",
    )
    args = parser.parse_args()

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

    from app.ingestion.ingest import ingest_requirements, verify_stored_requirements

    ingest_requirements()
    result = verify_stored_requirements()
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    if not result["ok"]:
        raise SystemExit("Ingestion verification failed")
    print("Verification passed: 18 unique requirement vectors stored.")


if __name__ == "__main__":
    main()
