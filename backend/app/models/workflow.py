from pydantic import BaseModel


class WorkflowCreate(BaseModel):
    name: str
    instruction: str


class WorkflowResponse(BaseModel):
    id: int
    name: str
    instruction: str
