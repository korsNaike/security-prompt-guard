from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_audit_log_repository, get_current_user
from app.domain.users.entities import UserRole
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.main import app
from tests.unit.fakes import FakeAuditLogRepository


def build_user(role: str) -> UserModel:
    user = UserModel(id=uuid4(), email=f"{role}@example.com", hashed_password="hashed", role=role)
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    return user


@pytest.fixture
def client():
    app.dependency_overrides[get_audit_log_repository] = lambda: FakeAuditLogRepository()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_admin_models_requires_admin_role(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: build_user(UserRole.USER.value)

    response = client.get("/api/v1/admin/models")

    assert response.status_code == 403


def test_admin_models_returns_catalog_for_admin(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: build_user(UserRole.ADMIN.value)

    response = client.get("/api/v1/admin/models")

    assert response.status_code == 200
    assert {item["model_code"] for item in response.json()["items"]} == {"prompt_guard"}


def test_admin_router_exposes_required_contract_endpoints(client: TestClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: build_user(UserRole.USER.value)

    assert client.get("/api/v1/admin/classifications").status_code == 403
    assert client.patch(
        f"/api/v1/admin/users/{uuid4()}/balance",
        json={"amount_delta": 10, "description": "manual correction"},
    ).status_code == 403
    assert client.post("/api/v1/admin/loyalty-tiers/recalculate").status_code == 403
