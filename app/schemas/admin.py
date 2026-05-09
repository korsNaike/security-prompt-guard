from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


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
