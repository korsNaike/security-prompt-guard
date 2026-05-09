from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClassificationCreateRequest(BaseModel):
    model_code: str = Field(min_length=1, examples=["prompt_guard"])
    mode: str = Field(min_length=1, examples=["standard"])
    text: str = Field(min_length=1, max_length=20_000)


class ClassificationBatchCreateRequest(BaseModel):
    model_code: str = Field(min_length=1, examples=["prompt_guard"])
    mode: str = Field(min_length=1, examples=["standard"])
    texts: list[str] = Field(min_length=1, max_length=50)


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
    mode: str | None = None
    product_name: str | None = None
    label: str | None = None
    risk_level: str | None = None
    confidence: float | None = None
    recommended_action: str | None = None
    explanation: str | None
    raw_scores: dict[str, float] | None = None
    metadata: dict | None = None
    cost: int | None = None
    estimated_cost: int | None = None
    final_cost: int | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ClassificationItemResponse(BaseModel):
    request_id: UUID
    status: str
    model_code: str
    mode: str
    estimated_cost: int
    final_cost: int | None = None
    label: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class ClassificationListResponse(BaseModel):
    items: list[ClassificationItemResponse]


class ClassificationBatchCreateResponse(BaseModel):
    batch_id: UUID
    status: str
    total_requests: int
    estimated_cost: int
    request_ids: list[UUID]


class ClassificationBatchResponse(BaseModel):
    batch_id: UUID
    status: str
    total_requests: int
    completed_requests: int
    failed_requests: int
    estimated_cost: int
    final_cost: int
    request_ids: list[UUID]
    created_at: datetime
    completed_at: datetime | None = None


def new_request_id() -> UUID:
    return uuid4()
