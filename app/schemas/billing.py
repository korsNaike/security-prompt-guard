from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    current_balance: int
    reserved_balance: int


class BillingTransactionResponse(BaseModel):
    id: UUID
    amount: int
    transaction_type: str
    status: str
    description: str | None
    created_at: datetime


class BillingTransactionListResponse(BaseModel):
    items: list[BillingTransactionResponse]


class TopUpRequest(BaseModel):
    amount: int = Field(gt=0, le=100_000)
    idempotency_key: str | None = Field(default=None, max_length=255)


class PromoCodeActivateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)


class LoyaltyTierResponse(BaseModel):
    code: str
    name: str
    discount_percent: int
    min_monthly_predictions: int
