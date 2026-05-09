from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AdminUserResponse(BaseModel):
    id: UUID
    email: str
    role: str
    is_active: bool
    current_balance: int
    reserved_balance: int
    created_at: datetime


class AdminUserListResponse(BaseModel):
    items: list[AdminUserResponse]


class AdminPromoCodeCreateRequest(BaseModel):
    code: str = Field(min_length=3, max_length=100)
    credits_amount: int = Field(gt=0)
    max_activations: int | None = Field(default=None, gt=0)


class AdminPromoCodeResponse(BaseModel):
    id: UUID
    code: str
    credits_amount: int
    max_activations: int | None
    used_count: int
    is_active: bool
    created_at: datetime


class AdminClassificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    model_code: str
    mode: str
    status: str
    estimated_cost: int
    final_cost: int | None
    label: str | None
    created_at: datetime
    completed_at: datetime | None = None


class AdminClassificationListResponse(BaseModel):
    items: list[AdminClassificationResponse]


class AdminBalanceAdjustmentRequest(BaseModel):
    amount_delta: int
    description: str = Field(min_length=1, max_length=500)

    @field_validator("amount_delta")
    @classmethod
    def validate_amount_delta(cls, value: int) -> int:
        if value == 0:
            raise ValueError("amount_delta must be non-zero")
        return value


class AdminBalanceAdjustmentResponse(BaseModel):
    user_id: UUID
    current_balance: int
    reserved_balance: int
    transaction_id: UUID
    amount: int
    transaction_type: str
