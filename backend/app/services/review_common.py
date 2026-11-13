from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.models.evaluation import ComplianceClassification
from app.models.review import ReviewDimension, ReviewFinding


def finding(
    *,
    finding_id: str,
    title: str,
    category: str,
    dimension: ReviewDimension,
    full_text: str,
    classification: ComplianceClassification,
    explanation: str,
    evidence: Optional[str],
    source_document: str,
) -> ReviewFinding:
    return ReviewFinding(
        id=finding_id,
        title=title,
        category=category,
        dimension=dimension,
        full_text=full_text,
        classification=classification,
        explanation=explanation,
        evidence=evidence,
        source_document=source_document,
        evidence_verified=bool(evidence),
        evaluation_state="completed",
        needs_review=False,
    )


def parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported timestamp: {value}")
