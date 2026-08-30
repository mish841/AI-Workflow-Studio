from pydantic import BaseModel


class RunCreate(BaseModel):
    document_id: int
    workflow_id: int


class RunResponse(BaseModel):
    id: int
    document_id: int
    workflow_id: int
    status: str
    result: dict
