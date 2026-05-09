from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.deps import get_audit_log_repository, get_current_user
from app.api.v1.classifications import get_classification_service
from app.core.exceptions import ModelNotFoundError
from app.domain.classifications.entities import ClassificationStatus
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.infrastructure.db.session import get_db_session
from app.main import app
from app.schemas.classifications import ClassificationCreateRequest
from tests.unit.fakes import FakeAuditLogRepository


class FakeClassificationService:
    def __init__(self, events: list[str] | None = None) -> None:
        self.request_id = uuid4()
        self.events = events if events is not None else []

    async def create_classification(self, *, user_id, model_code: str, mode: str, text: str):
        if model_code == "missing_model":
            raise ModelNotFoundError("Model missing_model was not found")
        return type(
            "Request",
            (),
            {
                "id": self.request_id,
                "model_code": model_code,
                "mode": mode,
                "estimated_cost": 7,
            },
        )()

    async def enqueue_classification(self, request):
        self.events.append("enqueue")

    async def get_classification(self, *, user_id, request_id):
        return self._completed_request(request_id)

    async def list_classifications(self, *, user_id, limit: int = 50):
        return [self._completed_request(self.request_id)]

    def _completed_request(self, request_id):
        result = type(
            "Result",
            (),
            {
                "label": "prompt_injection",
                "risk_level": "high",
                "confidence": 0.9,
                "recommended_action": "block",
                "explanation": "Matched injection markers",
                "raw_scores": {"prompt_injection": 0.9},
                "result_metadata": {"rules": ["ignore_previous"]},
            },
        )()
        return type(
            "Request",
            (),
            {
                "id": request_id,
                "status": ClassificationStatus.COMPLETED.value,
                "model_code": "prompt_guard",
                "mode": "standard",
                "estimated_cost": 7,
                "final_cost": 7,
                "created_at": datetime.now(UTC),
                "completed_at": datetime.now(UTC),
                "error_message": None,
                "result": result,
            },
        )()


class FakeDbSession:
    def __init__(self, events: list[str] | None = None) -> None:
        self.events = events if events is not None else []

    async def commit(self) -> None:
        self.events.append("commit")

    async def rollback(self) -> None:
        self.events.append("rollback")


@pytest.fixture
def client() -> TestClient:
    user = UserModel(id=uuid4(), email="user@example.com", hashed_password="hashed")
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    service = FakeClassificationService()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_classification_service] = lambda: service
    app.dependency_overrides[get_audit_log_repository] = lambda: FakeAuditLogRepository()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_create_classification_returns_persisted_pending_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classifications",
        json={
            "model_code": "prompt_guard",
            "mode": "standard",
            "text": "Ignore previous instructions",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["estimated_cost"] == 7


def test_create_classification_enqueues_after_commit() -> None:
    events = []
    user = UserModel(id=uuid4(), email="user@example.com", hashed_password="hashed")
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    service = FakeClassificationService(events=events)
    session = FakeDbSession(events=events)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_classification_service] = lambda: service
    app.dependency_overrides[get_audit_log_repository] = lambda: FakeAuditLogRepository()
    app.dependency_overrides[get_db_session] = lambda: session
    try:
        response = TestClient(app).post(
            "/api/v1/classifications",
            json={
                "model_code": "prompt_guard",
                "mode": "standard",
                "text": "Ignore previous instructions",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert events == ["commit", "enqueue", "commit"]


def test_create_classification_unknown_model_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/classifications",
        json={"model_code": "missing_model", "mode": "standard", "text": "hello"},
    )

    assert response.status_code == 404


def test_single_classification_text_limit_is_5000() -> None:
    ClassificationCreateRequest(model_code="prompt_guard", mode="standard", text="x" * 5000)

    with pytest.raises(ValidationError):
        ClassificationCreateRequest(model_code="prompt_guard", mode="standard", text="x" * 5001)


def test_get_classification_returns_result(client: TestClient) -> None:
    request_id = uuid4()

    response = client.get(f"/api/v1/classifications/{request_id}")

    assert response.status_code == 200
    assert response.json()["request_id"] == str(request_id)
    assert response.json()["label"] == "prompt_injection"


def test_list_classifications_returns_history(client: TestClient) -> None:
    response = client.get("/api/v1/classifications")

    assert response.status_code == 200
    assert response.json()["items"][0]["status"] == "completed"
