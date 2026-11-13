from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.evaluation import ComplianceClassification, EvaluationState


WorkspaceId = Literal["security", "sox", "project_qa", "content"]
ReviewDimension = Literal[
    "design",
    "completeness",
    "operating_effectiveness",
    "artifact_quality",
    "style",
]


class ReviewFinding(BaseModel):
    id: str
    title: str
    category: str
    dimension: ReviewDimension
    full_text: str
    classification: ComplianceClassification
    explanation: str
    evidence: Optional[str] = None
    source_document: str
    evidence_verified: bool = True
    evaluation_state: EvaluationState = "completed"
    needs_review: bool = False


class ReviewResult(BaseModel):
    id: str
    workspace: WorkspaceId
    evaluation_mode: Literal["deterministic"] = "deterministic"
    disclaimer: str
    source_document: str
    findings: list[ReviewFinding]


class WorkspaceDocument(BaseModel):
    id: str
    kind: str
    title: str
    file: str
    content: str


class WorkspaceSummary(BaseModel):
    id: WorkspaceId
    title: str
    status: Literal["available"]
    summary: str
    disclaimer: str
    compare_enabled: bool = False


class ReviewRequest(BaseModel):
    workspace: WorkspaceId = Field(description="Workspace to review.")
