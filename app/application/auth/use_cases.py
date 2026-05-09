from dataclasses import dataclass
from uuid import UUID

from app.core.security import create_access_token, get_password_hash, verify_password
from app.infrastructure.db.models import UserModel


class EmailAlreadyRegisteredError(Exception):
    pass


class AuthenticationError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InactiveUserError(Exception):
    pass


@dataclass(frozen=True)
class AuthResult:
    user: UserModel
    access_token: str
    token_type: str = "bearer"


class AuthService:
    def __init__(self, repository, initial_credits: int) -> None:
        self.repository = repository
        self.initial_credits = initial_credits

    async def register(self, *, email: str, password: str) -> AuthResult:
        existing_user = await self.repository.get_by_email(email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError("Email is already registered")

        user = await self.repository.create_user_with_balance(
            email=email,
            hashed_password=get_password_hash(password),
            initial_credits=self.initial_credits,
        )
        return AuthResult(user=user, access_token=create_access_token(str(user.id)))

    async def login(self, *, email: str, password: str) -> AuthResult:
        user = await self.repository.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise InactiveUserError("User is inactive")
        return AuthResult(user=user, access_token=create_access_token(str(user.id)))

    async def get_active_user(self, user_id: UUID) -> UserModel:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User was not found")
        if not user.is_active:
            raise InactiveUserError("User is inactive")
        return user
