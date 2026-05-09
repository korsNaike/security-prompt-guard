from app.domain.users.entities import UserRole
from app.infrastructure.db.models import UserBalanceModel, UserModel


def test_user_model_defaults() -> None:
    user = UserModel(email="user@example.com", hashed_password="hashed")

    assert user.email == "user@example.com"
    assert user.role == UserRole.USER.value
    assert user.is_active is True


def test_user_balance_model_defaults() -> None:
    balance = UserBalanceModel(user_id="00000000-0000-0000-0000-000000000001")

    assert balance.current_balance == 0
    assert balance.reserved_balance == 0
