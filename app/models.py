from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    airport: str = Field(..., description="IATA код аэропорта (например, DXB)")
    question: str = Field(..., min_length=5, description="Вопрос пользователя")


class QueryResponse(BaseModel):
    answer: str
