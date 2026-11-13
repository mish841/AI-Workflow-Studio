from __future__ import annotations

import re

from langchain_core.documents import Document

from app.models.evaluation import PolicyVersion

SECTION_HEADER = re.compile(r"^(\d+)\.\s+(.+)$", re.MULTILINE)


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "section"


def chunk_policy_documents(
    text: str,
    *,
    policy_version: PolicyVersion,
    filename: str,
    title: str,
) -> list[Document]:
    """Split a policy into header + numbered sections.

    Each chunk keeps document name, version, and section metadata so V1 and V2
    can be filtered independently at retrieval time.
    """
    matches = list(SECTION_HEADER.finditer(text))
    spans: list[tuple[str, str, int, int]] = []

    if matches:
        if matches[0].start() > 0:
            spans.append(("0", "Document header", 0, matches[0].start()))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            spans.append((match.group(1), match.group(2).strip(), match.start(), end))
    else:
        spans.append(("0", "Full document", 0, len(text)))

    documents: list[Document] = []
    for number, section_title, start, end in spans:
        content = text[start:end].strip()
        if not content:
            continue
        chunk_id = f"{policy_version}:{number}-{_slug(section_title)}"
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "chunk_id": chunk_id,
                    "policy_version": policy_version,
                    "source_file": filename,
                    "document_title": title,
                    "section_number": number,
                    "section_title": section_title,
                },
            )
        )
    if not documents:
        raise ValueError(f"No policy chunks produced for {filename}")
    return documents
