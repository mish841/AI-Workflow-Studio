from fastapi import FastAPI, HTTPException

from app.models.document import DocumentCreate, DocumentResponse

app = FastAPI(
    title="AI Workflow Studio API",
    description="Backend API for building and running configurable AI workflows.",
    version="0.1.0"
)

documents: list[DocumentResponse] = []
_next_document_id = 1


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