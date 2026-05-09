import pytest

from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.domain.billing.services import calculate_discounted_cost


def test_transaction_type_values_match_technical_task() -> None:
    assert BillingTransactionType.INITIAL_GRANT.value == "initial_grant"
    assert BillingTransactionType.TOP_UP.value == "top_up"
    assert BillingTransactionType.PROMO_GRANT.value == "promo_grant"
    assert BillingTransactionType.INFERENCE_HOLD.value == "inference_hold"
    assert BillingTransactionType.INFERENCE_CAPTURE.value == "inference_capture"
    assert BillingTransactionType.INFERENCE_REFUND.value == "inference_refund"
    assert BillingTransactionType.ADMIN_ADJUSTMENT.value == "admin_adjustment"
    assert BillingTransactionType.CACHE_HIT_CHARGE.value == "cache_hit_charge"


def test_transaction_status_values_match_technical_task() -> None:
    assert BillingTransactionStatus.PENDING.value == "pending"
    assert BillingTransactionStatus.COMPLETED.value == "completed"
    assert BillingTransactionStatus.FAILED.value == "failed"
    assert BillingTransactionStatus.REFUNDED.value == "refunded"


def test_discounted_cost_uses_ceiling() -> None:
    assert calculate_discounted_cost(base_cost=7, discount_percent=10) == 7
    assert calculate_discounted_cost(base_cost=15, discount_percent=10) == 14
    assert calculate_discounted_cost(base_cost=5, discount_percent=0) == 5


def test_discounted_cost_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=0, discount_percent=0)
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=5, discount_percent=-1)
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=5, discount_percent=101)
