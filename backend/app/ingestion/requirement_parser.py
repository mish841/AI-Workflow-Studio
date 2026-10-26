from __future__ import annotations

import re
from pathlib import Path

from langchain_core.documents import Document

EXPECTED_REQUIREMENT_IDS = (
    "AC-01",
    "AC-02",
    "AC-03",
    "AC-04",
    "AC-05",
    "AUTH-01",
    "AUTH-02",
    "AUTH-03",
    "AUTH-04",
    "AUTH-05",
    "DP-01",
    "DP-02",
    "DP-03",
    "DP-04",
    "IR-01",
    "IR-02",
    "IR-03",
    "IR-04",
)

CATEGORY_BY_FILENAME = {
    "access_control_standard.txt": "access_control",
    "authentication_standard.txt": "authentication",
    "data_protection_standard.txt": "data_protection",
    "incident_response_standard.txt": "incident_response",
}

REQUIREMENT_HEADER = re.compile(
    r"^(AC|AUTH|DP|IR)-\d{2}\b.*$",
    re.MULTILINE,
)
NEXT_NUMBERED_SECTION = re.compile(r"\n\d+\.\s+\S")


def default_reference_dir() -> Path:
    # backend/app/ingestion/requirement_parser.py → repo root
    return Path(__file__).resolve().parents[3] / "synthetic_data" / "reference"


def parse_reference_requirements(
    reference_dir: Path | None = None,
) -> list[Document]:
    """Parse each numbered requirement into one LangChain Document."""
    directory = reference_dir or default_reference_dir()
    if not directory.is_dir():
        raise FileNotFoundError(f"Reference directory not found: {directory}")

    documents: list[Document] = []
    for filename, category in CATEGORY_BY_FILENAME.items():
        path = directory / filename
        if not path.is_file():
            raise FileNotFoundError(f"Reference file not found: {path}")
        documents.extend(_parse_file(path, category))

    _validate_documents(documents)
    return documents


def _parse_file(path: Path, category: str) -> list[Document]:
    text = path.read_text(encoding="utf-8")
    matches = list(REQUIREMENT_HEADER.finditer(text))
    if not matches:
        raise ValueError(f"No numbered requirements found in {path.name}")

    documents: list[Document] = []
    for index, match in enumerate(matches):
        start = match.start()
        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            section = NEXT_NUMBERED_SECTION.search(text[start:])
            end = start + section.start() if section else len(text)

        content = text[start:end].strip()
        requirement_id = match.group(0).split()[0]
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "requirement_id": requirement_id,
                    "source_file": path.name,
                    "category": category,
                },
            )
        )
    return documents


def _validate_documents(documents: list[Document]) -> None:
    ids = [doc.metadata["requirement_id"] for doc in documents]
    unique_ids = set(ids)

    if len(ids) != 18:
        raise ValueError(f"Expected 18 requirements, parsed {len(ids)}: {ids}")
    if len(unique_ids) != 18:
        raise ValueError(f"Requirement IDs are not unique: {ids}")
    if unique_ids != set(EXPECTED_REQUIREMENT_IDS):
        missing = set(EXPECTED_REQUIREMENT_IDS) - unique_ids
        extra = unique_ids - set(EXPECTED_REQUIREMENT_IDS)
        raise ValueError(
            f"Parsed IDs do not match the expected catalog. "
            f"missing={sorted(missing)} extra={sorted(extra)}"
        )
    for document in documents:
        if not document.page_content.strip():
            raise ValueError(
                f"Empty content for {document.metadata['requirement_id']}"
            )
