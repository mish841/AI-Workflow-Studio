from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


ComplianceClassification = Literal[
    "satisfied",
    "partial",
    "missing",
    "contradicted",
]
EvaluationState = Literal["completed", "needs_review", "failed"]
EvidenceVerification = Literal["verified", "missing", "unverified"]
PolicyVersion = Literal["v1", "v2"]
EvaluationMode = Literal["direct", "rag"]
RequestedEvaluationMode = Literal["auto", "direct", "rag"]


class RequirementSummary(BaseModel):
    requirement_id: str
    title: str
    category: str
    source_file: str
    text: str


class PolicySummary(BaseModel):
    id: PolicyVersion
    filename: str
    title: str


class ModelFinding(BaseModel):
    """Structured output requested from the model. No ground-truth fields."""

    requirement_id: str
    requirement_title: str
    classification: ComplianceClassification
    explanation: str
    supporting_quote: Optional[str] = None
    needs_review: bool = False
    uncertainty_note: Optional[str] = None


class RetrievedPassage(BaseModel):
    chunk_id: str
    source_document: str
    policy_version: PolicyVersion
    section_number: str = ""
    section_title: str = ""
    text: str
    distance: Optional[float] = None
    used_in_finding: bool = False


class RetrievalHit(BaseModel):
    id: str
    text: str
    distance: Optional[float] = None
    metadata: dict = Field(default_factory=dict)


class ComplianceFinding(BaseModel):
    requirement_id: str
    requirement_title: str
    requirement_text: str
    category: str = ""
    classification: Optional[ComplianceClassification] = None
    explanation: str
    supporting_quote: Optional[str] = None
    source_document: str
    evidence_verified: bool
    evidence_verification: EvidenceVerification
    needs_review: bool
    evaluation_state: EvaluationState
    uncertainty_note: Optional[str] = None
    retrieved_passages: list[RetrievedPassage] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    policy_version: PolicyVersion = Field(
        description="Northstar policy to evaluate: v1 or v2.",
    )
    requirement_ids: Optional[list[str]] = Field(
        default=None,
        max_length=18,
        description=(
            "Optional subset of requirement IDs for development tests. "
            "Omit or leave empty to evaluate the full 18-requirement inventory."
        ),
    )
    evaluation_mode: RequestedEvaluationMode = Field(
        default="auto",
        description=(
            "User-facing assessments use auto (prefer retrieved passages; "
            "full-document fallback only if COMPLIANCE_ALLOW_DIRECT_FALLBACK "
            "is enabled). Engineering clients may send direct or rag."
        ),
    )
    retrieval_k: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Number of policy passages to retrieve per requirement in rag mode.",
    )


class EvaluationResult(BaseModel):
    id: str
    policy_version: PolicyVersion
    source_document: str
    evaluation_mode: EvaluationMode = "direct"
    requested_mode: RequestedEvaluationMode = "auto"
    fallback_used: bool = False
    retrieval_ready: Optional[bool] = None
    model: str = "gpt-4o-mini"
    duration_ms: Optional[int] = None
    findings: list[ComplianceFinding]


class StatusBreakdown(BaseModel):
    satisfied: int = 0
    partial: int = 0
    missing: int = 0
    contradicted: int = 0
    unlabeled: int = 0


class EvaluationMetrics(BaseModel):
    total_requirements_evaluated: int
    successful_classifications: int
    classification_accuracy: Optional[float]
    per_status_predicted: StatusBreakdown
    per_status_expected: StatusBreakdown
    evidence_verification_pass_rate: float
    failed_or_uncertain: int
    note: str
