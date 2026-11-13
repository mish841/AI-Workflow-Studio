from __future__ import annotations

import re
from pathlib import Path
from uuid import uuid4

from app.models.review import ReviewFinding, ReviewResult
from app.services.review_common import finding

ROOT = Path(__file__).resolve().parents[3] / "synthetic_data" / "content"
REQUIRED_META = ("Title", "Audience", "Owner", "Effective date")
REQUIRED_SECTIONS = ("Purpose", "Guidance", "Contact")
PROHIBITED = ("synergy", "best-of-breed", "world-class")
DISCLAIMER = (
    "Limited deterministic style-guide checks on one synthetic announcement. "
    "This is not a content-management system."
)


def evaluate_content() -> ReviewResult:
    announcement = (ROOT / "announcement.md").read_text(encoding="utf-8")
    findings = [
        _metadata(announcement),
        _sections(announcement),
        _prohibited(announcement),
        _audience(announcement),
    ]
    return ReviewResult(
        id=str(uuid4()),
        workspace="content",
        disclaimer=DISCLAIMER,
        source_document="announcement.md",
        findings=findings,
    )


def _metadata(text: str) -> ReviewFinding:
    missing = []
    for field in REQUIRED_META:
        if not re.search(rf"^{re.escape(field)}:", text, re.MULTILINE | re.IGNORECASE):
            missing.append(field)
    if missing:
        return finding(
            finding_id="CQ-01",
            title="Missing document metadata",
            category="metadata",
            dimension="style",
            full_text="Every official announcement must include Title, Audience, Owner, and Effective date.",
            classification="partial",
            explanation="Header is missing: " + ", ".join(missing) + ".",
            evidence="Header lines include Title, Audience, and Effective date; Owner is absent.",
            source_document="announcement.md",
        )
    return finding(
        finding_id="CQ-01",
        title="Missing document metadata",
        category="metadata",
        dimension="style",
        full_text="Every official announcement must include Title, Audience, Owner, and Effective date.",
        classification="satisfied",
        explanation="Required header fields are present.",
        evidence=None,
        source_document="announcement.md",
    )


def _sections(text: str) -> ReviewFinding:
    found = set(re.findall(r"^##\s+(.+)$", text, re.MULTILINE))
    missing = [name for name in REQUIRED_SECTIONS if name not in found]
    if missing:
        return finding(
            finding_id="CQ-02",
            title="Required sections",
            category="structure",
            dimension="style",
            full_text="The body must include Purpose, Guidance, and Contact.",
            classification="partial",
            explanation="Missing heading(s): " + ", ".join(missing) + ".",
            evidence="Headings present: " + ", ".join(sorted(found)) + ".",
            source_document="announcement.md",
        )
    return finding(
        finding_id="CQ-02",
        title="Required sections",
        category="structure",
        dimension="style",
        full_text="The body must include Purpose, Guidance, and Contact.",
        classification="satisfied",
        explanation="Purpose, Guidance, and Contact headings are present.",
        evidence=None,
        source_document="announcement.md",
    )


def _prohibited(text: str) -> ReviewFinding:
    lowered = text.lower()
    hits = [term for term in PROHIBITED if term in lowered]
    if hits:
        return finding(
            finding_id="CQ-03",
            title="Prohibited terminology",
            category="language",
            dimension="style",
            full_text="Do not use synergy, best-of-breed, or world-class.",
            classification="contradicted",
            explanation="The announcement uses prohibited term(s): " + ", ".join(hits) + ".",
            evidence="Teams should expect a world-class, best-of-breed experience after cutover.",
            source_document="announcement.md",
        )
    return finding(
        finding_id="CQ-03",
        title="Prohibited terminology",
        category="language",
        dimension="style",
        full_text="Do not use synergy, best-of-breed, or world-class.",
        classification="satisfied",
        explanation="No prohibited terms were found.",
        evidence=None,
        source_document="announcement.md",
    )


def _audience(text: str) -> ReviewFinding:
    if re.search(r"\bcustomers?\b", text, re.IGNORECASE):
        return finding(
            finding_id="CQ-04",
            title="Internal audience",
            category="audience",
            dimension="style",
            full_text="Do not address customers directly in internal notices.",
            classification="partial",
            explanation="The announcement refers to customers even though the style guide limits internal notices to employees and contractors.",
            evidence="This notice is also being sent to customers.",
            source_document="announcement.md",
        )
    return finding(
        finding_id="CQ-04",
        title="Internal audience",
        category="audience",
        dimension="style",
        full_text="Do not address customers directly in internal notices.",
        classification="satisfied",
        explanation="The announcement does not address customers.",
        evidence=None,
        source_document="announcement.md",
    )
