from uuid import uuid4

from app.application.auth.use_cases import AuthService
from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.models import UserBalanceModel, UserModel


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, UserModel] = {}

    async def get_by_email(self, email: str) -> UserModel | None:
        return self.users_by_email.get(email)

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
            current_balance=0,
            reserved_balance=0,
        )
        self.users_by_email[email] = user
        return user


class FakeBillingRepository:
    def __init__(self, user_repository: FakeUserRepository) -> None:
        self.user_repository = user_repository
        self.created_initial_grants: list[tuple[object, int]] = []

    async def create_initial_grant(self, *, user_id, amount: int):
        self.created_initial_grants.append((user_id, amount))
        for user in self.user_repository.users_by_email.values():
            if user.id == user_id:
                user.balance.current_balance += amount
        transaction = type("Transaction", (), {})()
        transaction.transaction_type = BillingTransactionType.INITIAL_GRANT.value
        transaction.amount = amount
        return transaction


async def test_register_creates_initial_grant_transaction() -> None:
    user_repository = FakeUserRepository()
    billing_repository = FakeBillingRepository(user_repository)
    service = AuthService(
        repository=user_repository,
        billing_repository=billing_repository,
        initial_credits=100,
    )

    result = await service.register(email="user@example.com", password="strong-password")

    assert billing_repository.created_initial_grants == [(result.user.id, 100)]
    assert result.user.balance.current_balance == 100
