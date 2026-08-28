from pydantic import BaseModel


class DocumentCreate(BaseModel):
    name: str
    content: str


class DocumentResponse(BaseModel):
    id: int
    name: str
    content: str
