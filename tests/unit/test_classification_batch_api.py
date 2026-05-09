from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.classifications import get_classification_service
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.main import app


class FakeClassificationService:
    def __init__(self) -> None:
        self.batch_id = uuid4()
        self.request_ids = [uuid4(), uuid4()]

    async def create_batch(self, *, user_id, model_code: str, mode: str, items: list[str]):
        batch = type(
            "Batch",
            (),
            {
                "id": self.batch_id,
                "status": "pending",
                "total_requests": len(items),
                "estimated_cost": len(items) * 7,
            },
        )()
        requests = [type("Request", (), {"id": request_id})() for request_id in self.request_ids]
        return {"batch": batch, "requests": requests}

    async def get_batch(self, *, user_id, batch_id):
        requests = [type("Request", (), {"id": request_id})() for request_id in self.request_ids]
        return type(
            "Batch",
            (),
            {
                "id": batch_id,
                "status": "partial_success",
                "total_requests": 2,
                "completed_requests": 1,
                "failed_requests": 1,
                "estimated_cost": 14,
                "final_cost": 7,
                "requests": requests,
                "created_at": datetime.now(UTC),
                "completed_at": datetime.now(UTC),
            },
        )()


@pytest.fixture
def client() -> TestClient:
    user = UserModel(id=uuid4(), email="user@example.com", hashed_password="hashed")
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    service = FakeClassificationService()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_classification_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_batch_accepts_items_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classifications/batch",
        json={
            "model_code": "prompt_guard",
            "mode": "standard",
            "items": ["one", "two"],
        },
    )

    assert response.status_code == 200
    assert response.json()["total_requests"] == 2
    assert len(response.json()["request_ids"]) == 2


def test_create_batch_rejects_legacy_texts_field(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classifications/batch",
        json={
            "model_code": "prompt_guard",
            "mode": "standard",
            "texts": ["one", "two"],
        },
    )

    assert response.status_code == 422


def test_get_batch_returns_aggregate_progress(client: TestClient) -> None:
    response = client.get(f"/api/v1/classifications/batch/{uuid4()}")

    assert response.status_code == 200
    assert response.json()["status"] == "partial_success"
    assert response.json()["completed_requests"] == 1
    assert response.json()["failed_requests"] == 1
