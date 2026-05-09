from uuid import uuid4

import pytest

from app.application.auth.use_cases import (
    AuthenticationError,
    AuthService,
    EmailAlreadyRegisteredError,
    InactiveUserError,
    UserNotFoundError,
)
from app.infrastructure.db.models import UserBalanceModel, UserModel


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, UserModel] = {}
        self.users_by_id: dict[object, UserModel] = {}

    async def get_by_email(self, email: str) -> UserModel | None:
        return self.users_by_email.get(email)

    async def get_by_id(self, user_id) -> UserModel | None:
        return self.users_by_id.get(user_id)

    async def create_user_with_balance(
        self,
        *,
        email: str,
        hashed_password: str,
        initial_credits: int,
    ) -> UserModel:
        user = UserModel(id=uuid4(), email=email, hashed_password=hashed_password)
        user.balance = UserBalanceModel(
            user_id=user.id,
            current_balance=initial_credits,
            reserved_balance=0,
        )
        self.users_by_email[email] = user
        self.users_by_id[user.id] = user
        return user


async def test_register_creates_user_with_initial_balance() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)

    result = await service.register(email="user@example.com", password="strong-password")

    assert result.user.email == "user@example.com"
    assert result.user.balance.current_balance == 100
    assert result.access_token


async def test_register_rejects_duplicate_email() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)
    await service.register(email="user@example.com", password="strong-password")

    with pytest.raises(EmailAlreadyRegisteredError):
        await service.register(email="user@example.com", password="strong-password")


async def test_login_returns_token_for_valid_credentials() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)
    await service.register(email="user@example.com", password="strong-password")

    result = await service.login(email="user@example.com", password="strong-password")

    assert result.token_type == "bearer"
    assert result.access_token


async def test_login_rejects_wrong_password() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)
    await service.register(email="user@example.com", password="strong-password")

    with pytest.raises(AuthenticationError):
        await service.login(email="user@example.com", password="wrong-password")


async def test_get_active_user_rejects_missing_user() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)

    with pytest.raises(UserNotFoundError):
        await service.get_active_user(uuid4())


async def test_get_active_user_rejects_inactive_user() -> None:
    repository = FakeUserRepository()
    service = AuthService(repository=repository, initial_credits=100)
    result = await service.register(email="user@example.com", password="strong-password")
    result.user.is_active = False

    with pytest.raises(InactiveUserError):
        await service.get_active_user(result.user.id)
