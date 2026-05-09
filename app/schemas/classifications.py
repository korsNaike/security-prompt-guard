from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClassificationCreateRequest(BaseModel):
    model_code: str = Field(min_length=1, examples=["prompt_guard"])
    mode: str = Field(min_length=1, examples=["standard"])
    text: str = Field(min_length=1, max_length=20_000)


class ClassificationCreateResponse(BaseModel):
    request_id: UUID
    status: str
    model_code: str
    mode: str
    estimated_cost: int


class ClassificationResultResponse(BaseModel):
    request_id: UUID
    status: str
    model_code: str
    product_name: str
    label: str
    risk_level: str
    confidence: float
    recommended_action: str
    explanation: str | None
    cost: int


def new_request_id() -> UUID:
    return uuid4()
