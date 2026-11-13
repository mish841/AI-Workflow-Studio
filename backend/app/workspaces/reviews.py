from __future__ import annotations

from fastapi import HTTPException

from app.models.review import ReviewResult, WorkspaceId
from app.services.content_evaluator import evaluate_content
from app.services.project_qa_evaluator import evaluate_project_qa
from app.services.sox_evaluator import evaluate_sox


def run_workspace_review(workspace: WorkspaceId) -> ReviewResult:
    if workspace == "sox":
        return evaluate_sox()
    if workspace == "project_qa":
        return evaluate_project_qa()
    if workspace == "content":
        return evaluate_content()
    raise HTTPException(
        status_code=400,
        detail="Use the compliance evaluation endpoints for the security workspace.",
    )
