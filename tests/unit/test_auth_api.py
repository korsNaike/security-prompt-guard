from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service, get_current_user
from app.application.auth.use_cases import AuthResult
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.main import app


class FakeAuthService:
    def __init__(self) -> None:
        self.user = UserModel(
            id=uuid4(),
            email="user@example.com",
            hashed_password="hashed",
        )
        self.user.balance = UserBalanceModel(
            user_id=self.user.id,
            current_balance=100,
            reserved_balance=0,
        )

    async def register(self, *, email: str, password: str) -> AuthResult:
        self.user.email = email
        return AuthResult(user=self.user, access_token="registered-token")

    async def login(self, *, email: str, password: str) -> AuthResult:
        self.user.email = email
        return AuthResult(user=self.user, access_token="login-token")


@pytest.fixture
def client() -> TestClient:
    service = FakeAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: service.user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_register_endpoint_returns_token_and_user(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "strong-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "registered-token"
    assert payload["token_type"] == "bearer"
    assert payload["user"]["email"] == "new@example.com"
    assert payload["user"]["balance"]["current_balance"] == 100


def test_login_endpoint_returns_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"] == "login-token"
    assert payload["user"]["email"] == "user@example.com"


def test_me_endpoint_returns_current_user(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "user@example.com"
    assert payload["balance"]["current_balance"] == 100
