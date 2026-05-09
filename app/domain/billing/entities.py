from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class BillingTransactionType(StrEnum):
    INITIAL_GRANT = "initial_grant"
    TOP_UP = "top_up"
    PROMO_GRANT = "promo_grant"
    INFERENCE_HOLD = "inference_hold"
    INFERENCE_CAPTURE = "inference_capture"
    INFERENCE_REFUND = "inference_refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    CACHE_HIT_CHARGE = "cache_hit_charge"


class BillingTransactionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class BalanceSnapshot:
    user_id: UUID
    current_balance: int
    reserved_balance: int


@dataclass(frozen=True)
class BillingTransaction:
    id: UUID
    user_id: UUID
    amount: int
    transaction_type: BillingTransactionType
    status: BillingTransactionStatus
    idempotency_key: str
    description: str | None
    created_at: datetime
