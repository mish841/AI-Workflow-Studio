from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.db_models import Document, Run, Workflow
from app.models.document import DocumentCreate, DocumentResponse
from app.models.run import RunCreate, RunResponse
from app.models.workflow import WorkflowCreate, WorkflowResponse
from app.services.workflow_executor import execute_workflow


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Workflow Studio API",
    description="Backend API for building and running configurable AI workflows.",
    version="0.1.0",
    lifespan=lifespan,
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
