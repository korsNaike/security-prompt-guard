from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.infrastructure.db.models import (
    BillingTransactionModel,
    LoyaltyTierModel,
    PromoCodeActivationModel,
    PromoCodeModel,
    UserModel,
)


def test_billing_transaction_defaults() -> None:
    transaction = BillingTransactionModel(
        user_id="00000000-0000-0000-0000-000000000001",
        amount=100,
        transaction_type=BillingTransactionType.TOP_UP.value,
        idempotency_key="top-up:1",
    )

    assert transaction.status == BillingTransactionStatus.COMPLETED.value
    assert transaction.amount == 100


def test_promo_code_defaults() -> None:
    promo_code = PromoCodeModel(code="WELCOME100", credits_amount=100)

    assert promo_code.used_count == 0
    assert promo_code.is_active is True


def test_promo_activation_links_user_and_code() -> None:
    activation = PromoCodeActivationModel(
        promo_code_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
        credits_granted=100,
    )

    assert activation.credits_granted == 100


def test_loyalty_tier_defaults() -> None:
    tier = LoyaltyTierModel(
        code="bronze",
        name="Bronze",
        min_monthly_predictions=0,
        discount_percent=0,
    )

    assert tier.is_active is True


def test_user_has_loyalty_tier_field() -> None:
    user = UserModel(email="user@example.com", hashed_password="hashed")

    assert hasattr(user, "loyalty_tier_id")
