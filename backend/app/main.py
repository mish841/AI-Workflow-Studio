from contextlib import asynccontextmanager
import time

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.db_models import Document, Run, Workflow
from app.models.document import DocumentCreate, DocumentResponse
from app.models.evaluation import EvaluationRequest, EvaluationResult
from app.models.run import RunCreate, RunResponse
from app.models.workflow import WorkflowCreate, WorkflowResponse
from app.services.compliance_evaluator import (
    evaluate_policy,
    load_requirement_inventory,
)
from app.services.evaluation_mode import resolve_evaluation_mode
from app.models.review import ReviewResult, WorkspaceId
from app.services.evaluation_store import (
    get_evaluation,
    get_review,
    save_evaluation,
    save_review,
)
from app.workspaces.catalog import list_workspaces, load_workspace_documents
from app.workspaces.reviews import run_workspace_review
from app.services.policy_loader import list_policies
from app.services.retrieval import search_policy_passages, search_requirements
from app.services.request_guards import (
    evaluation_limiter,
    require_paid_openai,
    retrieval_limiter,
    workflow_run_limiter,
)
from app.services.workflow_executor import execute_workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


MAX_BODY_BYTES = 120_000


class LimitRequestBodyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        length = request.headers.get("content-length")
        if length:
            try:
                size = int(length)
            except ValueError:
                size = 0
            if size > MAX_BODY_BYTES:
                return JSONResponse(
                    {"detail": "Request body is too large."},
                    status_code=413,
                )
        return await call_next(request)


app = FastAPI(
    title="AI Workflow Studio API",
    description="Backend API for building and running configurable AI workflows.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(LimitRequestBodyMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/")
def root():
    return {
        "message": "Welcome to AI Workflow Studio"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }


@app.post("/documents", response_model=DocumentResponse)
def create_document(payload: DocumentCreate, db: Session = Depends(get_db)):
    document = Document(name=payload.name, content=payload.content)
    db.add(document)
    db.commit()
    db.refresh(document)
    return DocumentResponse(
        id=document.id,
        name=document.name,
        content=document.content,
    )


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=document.id,
        name=document.name,
        content=document.content,
    )


@app.post("/workflows", response_model=WorkflowResponse)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    workflow = Workflow(name=payload.name, instruction=payload.instruction)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        instruction=workflow.instruction,
    )


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        instruction=workflow.instruction,
    )


@app.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate, db: Session = Depends(get_db)):
    document = db.get(Document, payload.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    workflow = db.get(Workflow, payload.workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    require_paid_openai()
    workflow_run_limiter.check()
    result = execute_workflow(document.content, workflow.instruction)
    run = Run(
        document_id=document.id,
        workflow_id=workflow.id,
        status="completed",
        result=result,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return RunResponse(
        id=run.id,
        document_id=run.document_id,
        workflow_id=run.workflow_id,
        status=run.status,
        result=run.result,
    )


@app.get("/compliance/policies")
def compliance_policies():
    return {"policies": list_policies()}


@app.get("/compliance/requirements")
def compliance_requirements():
    return {"requirements": load_requirement_inventory()}


@app.get("/compliance/retrieval/status")
def compliance_retrieval_status():
    from app.ingestion.ingest import vector_store_status

    try:
        return vector_store_status()
    except Exception as exc:  # noqa: BLE001 - inspectability
        raise HTTPException(
            status_code=503,
            detail="The source library is not ready.",
        ) from exc


@app.get("/compliance/retrieval/requirements")
def compliance_requirement_search(
    q: str = Query(..., min_length=1, max_length=500),
    k: int = Query(5, ge=1, le=12),
):
    require_paid_openai()
    retrieval_limiter.check()
    try:
        hits = search_requirements(q, k=k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="Requirement search is unavailable.",
        ) from exc
    return {"query": q, "k": k, "hits": [hit.model_dump() for hit in hits]}


@app.get("/compliance/retrieval/policies")
def compliance_policy_search(
    q: str = Query(..., min_length=1, max_length=500),
    policy_version: str = Query(..., min_length=2, max_length=8),
    k: int = Query(4, ge=1, le=12),
):
    if policy_version not in {"v1", "v2"}:
        raise HTTPException(status_code=400, detail="policy_version must be v1 or v2")
    require_paid_openai()
    retrieval_limiter.check()
    try:
        hits = search_policy_passages(q, policy_version, k=k)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail="Document search is unavailable.",
        ) from exc
    return {
        "query": q,
        "policy_version": policy_version,
        "k": k,
        "hits": [hit.model_dump() for hit in hits],
    }


@app.post("/compliance/evaluations", response_model=EvaluationResult)
def create_compliance_evaluation(payload: EvaluationRequest):
    require_paid_openai()
    evaluation_limiter.check()
    resolved = resolve_evaluation_mode(payload.evaluation_mode)
    started = time.perf_counter()
    result = evaluate_policy(
        payload.policy_version,
        requirement_ids=payload.requirement_ids,
        evaluation_mode=resolved["evaluation_mode"],
        retrieval_k=payload.retrieval_k,
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    result = result.model_copy(
        update={
            "requested_mode": resolved["requested_mode"],
            "fallback_used": resolved["fallback_used"],
            "retrieval_ready": resolved["retrieval_ready"],
            "model": "gpt-4o-mini",
            "duration_ms": duration_ms,
        }
    )
    return save_evaluation(result)


@app.get("/compliance/evaluations/{evaluation_id}", response_model=EvaluationResult)
def get_compliance_evaluation(evaluation_id: str):
    result = get_evaluation(evaluation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return result


@app.get("/workspaces")
def workspaces():
    return {"workspaces": list_workspaces()}


@app.get("/workspaces/{workspace_id}/documents")
def workspace_documents(workspace_id: WorkspaceId):
    if workspace_id == "security":
        raise HTTPException(
            status_code=400,
            detail="Security documents are loaded from the compliance dataset.",
        )
    return {"documents": load_workspace_documents(workspace_id)}


@app.post("/workspaces/{workspace_id}/reviews", response_model=ReviewResult)
def create_workspace_review(workspace_id: WorkspaceId):
    return save_review(run_workspace_review(workspace_id))


@app.get("/workspaces/reviews/{review_id}", response_model=ReviewResult)
def get_workspace_review(review_id: str):
    result = get_review(review_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return result
