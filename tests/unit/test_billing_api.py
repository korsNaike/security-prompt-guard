from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_repository, get_current_user
from app.api.v1.billing import get_billing_service
from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.main import app
from tests.unit.fakes import FakeAuditLogRepository


class FakeBillingService:
    async def get_balance(self, user_id):
        return {"current_balance": 100, "reserved_balance": 10}

    async def list_transactions(self, user_id):
        return [
            {
                "id": uuid4(),
                "amount": 100,
                "transaction_type": BillingTransactionType.INITIAL_GRANT.value,
                "status": "completed",
                "description": "Initial registration credits",
                "created_at": "2026-05-09T00:00:00Z",
            }
        ]

    async def top_up(self, user_id, amount: int, idempotency_key: str | None):
        return {
            "id": uuid4(),
            "amount": amount,
            "transaction_type": BillingTransactionType.TOP_UP.value,
            "status": "completed",
            "description": "Mock top-up",
            "created_at": "2026-05-09T00:00:00Z",
        }

    async def activate_promo_code(self, user_id, code: str):
        return {
            "id": uuid4(),
            "amount": 50,
            "transaction_type": BillingTransactionType.PROMO_GRANT.value,
            "status": "completed",
            "description": f"Promo code {code}",
            "created_at": "2026-05-09T00:00:00Z",
        }

    async def get_loyalty_tier(self, user_id):
        return {
            "code": "bronze",
            "name": "Bronze",
            "discount_percent": 0,
            "min_monthly_predictions": 0,
        }


@pytest.fixture
def client() -> TestClient:
    user = UserModel(id=uuid4(), email="user@example.com", hashed_password="hashed")
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    service = FakeBillingService()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_billing_service] = lambda: service
    app.dependency_overrides[get_audit_log_repository] = lambda: FakeAuditLogRepository()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_get_balance(client: TestClient) -> None:
    response = client.get("/api/v1/billing/balance")

    assert response.status_code == 200
    assert response.json() == {"current_balance": 100, "reserved_balance": 10}


def test_list_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/billing/transactions")

    assert response.status_code == 200
    assert response.json()["items"][0]["transaction_type"] == "initial_grant"


def test_top_up(client: TestClient) -> None:
    response = client.post("/api/v1/billing/top-up", json={"amount": 25})

    assert response.status_code == 200
    assert response.json()["amount"] == 25
    assert response.json()["transaction_type"] == "top_up"


def test_activate_promo_code(client: TestClient) -> None:
    response = client.post("/api/v1/billing/promo-codes/activate", json={"code": "WELCOME50"})

    assert response.status_code == 200
    assert response.json()["transaction_type"] == "promo_grant"


def test_get_loyalty_tier(client: TestClient) -> None:
    response = client.get("/api/v1/billing/loyalty-tier")

    assert response.status_code == 200
    assert response.json()["code"] == "bronze"
