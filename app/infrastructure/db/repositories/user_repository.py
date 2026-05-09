from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import UserBalanceModel, UserModel


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel)
            .options(selectinload(UserModel.balance))
            .where(UserModel.email == email)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> UserModel | None:
        result = await self.session.execute(
            select(UserModel)
            .options(selectinload(UserModel.balance))
            .where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_users(self, limit: int = 100) -> list[UserModel]:
        result = await self.session.execute(
            select(UserModel)
            .options(selectinload(UserModel.balance))
            .order_by(UserModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_user_with_balance(
        self,
        *,
        email: str,
        hashed_password: str,
        initial_credits: int,
    ) -> UserModel:
        user = UserModel(email=email, hashed_password=hashed_password)
        user.balance = UserBalanceModel(current_balance=0, reserved_balance=0)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user, attribute_names=["balance"])
        return user
