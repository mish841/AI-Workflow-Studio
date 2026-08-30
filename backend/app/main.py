from fastapi import FastAPI, HTTPException

from app.models.document import DocumentCreate, DocumentResponse
from app.models.run import RunCreate, RunResponse
from app.models.workflow import WorkflowCreate, WorkflowResponse

app = FastAPI(
    title="AI Workflow Studio API",
    description="Backend API for building and running configurable AI workflows.",
    version="0.1.0"
)

documents: list[DocumentResponse] = []
_next_document_id = 1

workflows: list[WorkflowResponse] = []
_next_workflow_id = 1

runs: list[RunResponse] = []
_next_run_id = 1


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
def create_document(payload: DocumentCreate):
    global _next_document_id

    document = DocumentResponse(
        id=_next_document_id,
        name=payload.name,
        content=payload.content,
    )
    documents.append(document)
    _next_document_id += 1
    return document


@app.get("/documents/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int):
    for document in documents:
        if document.id == document_id:
            return document
    raise HTTPException(status_code=404, detail="Document not found")


@app.post("/workflows", response_model=WorkflowResponse)
def create_workflow(payload: WorkflowCreate):
    global _next_workflow_id

    workflow = WorkflowResponse(
        id=_next_workflow_id,
        name=payload.name,
        instruction=payload.instruction,
    )
    workflows.append(workflow)
    _next_workflow_id += 1
    return workflow


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: int):
    for workflow in workflows:
        if workflow.id == workflow_id:
            return workflow
    raise HTTPException(status_code=404, detail="Workflow not found")


@app.post("/runs", response_model=RunResponse)
def create_run(payload: RunCreate):
    global _next_run_id

    document = None
    for item in documents:
        if item.id == payload.document_id:
            document = item
            break
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    workflow = None
    for item in workflows:
        if item.id == payload.workflow_id:
            workflow = item
            break
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    run = RunResponse(
        id=_next_run_id,
        document_id=payload.document_id,
        workflow_id=payload.workflow_id,
        status="completed",
        result={
            "summary": f"Mock summary of '{document.name}' using '{workflow.name}'.",
            "key_points": [
                workflow.instruction,
                f"Processed document: {document.name}",
            ],
        },
    )
    runs.append(run)
    _next_run_id += 1
    return run