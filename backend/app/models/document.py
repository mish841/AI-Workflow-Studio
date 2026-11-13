from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=100_000)


class DocumentResponse(BaseModel):
    id: int
    name: str
    content: str
