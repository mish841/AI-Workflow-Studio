from pydantic import BaseModel, Field


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=20_000)


class WorkflowResponse(BaseModel):
    id: int
    name: str
    instruction: str
