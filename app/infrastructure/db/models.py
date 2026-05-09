import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.billing.entities import BillingTransactionStatus
from app.domain.users.entities import UserRole
from app.infrastructure.db.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserRole.USER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    loyalty_tier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("loyalty_tiers.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    balance: Mapped["UserBalanceModel"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )
    loyalty_tier: Mapped["LoyaltyTierModel | None"] = relationship(lazy="selectin")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.role is None:
            self.role = UserRole.USER.value
        if self.is_active is None:
            self.is_active = True
        if self.created_at is None:
            self.created_at = utc_now()
        if self.updated_at is None:
            self.updated_at = utc_now()


class LoyaltyTierModel(Base):
    __tablename__ = "loyalty_tiers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_monthly_predictions: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.is_active is None:
            self.is_active = True
        if self.created_at is None:
            self.created_at = utc_now()
        if self.updated_at is None:
            self.updated_at = utc_now()


class UserBalanceModel(Base):
    __tablename__ = "user_balances"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_balances_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )

    user: Mapped[UserModel] = relationship(back_populates="balance", lazy="selectin")

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.current_balance is None:
            self.current_balance = 0
        if self.reserved_balance is None:
            self.reserved_balance = 0
        if self.updated_at is None:
            self.updated_at = utc_now()


class BillingTransactionModel(Base):
    __tablename__ = "billing_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=BillingTransactionStatus.COMPLETED.value,
    )
    classification_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("billing_transactions.id"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.status is None:
            self.status = BillingTransactionStatus.COMPLETED.value
        if self.created_at is None:
            self.created_at = utc_now()


class PromoCodeModel(Base):
    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    credits_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    max_activations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.used_count is None:
            self.used_count = 0
        if self.is_active is None:
            self.is_active = True
        if self.created_at is None:
            self.created_at = utc_now()


class PromoCodeActivationModel(Base):
    __tablename__ = "promo_code_activations"
    __table_args__ = (
        UniqueConstraint("promo_code_id", "user_id", name="uq_promo_code_activations_code_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    credits_granted: Mapped[int] = mapped_column(Integer, nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.activated_at is None:
            self.activated_at = utc_now()


class LoyaltyTierHistoryModel(Base):
    __tablename__ = "loyalty_tier_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    old_tier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("loyalty_tiers.id"),
    )
    new_tier_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("loyalty_tiers.id"),
        nullable=False,
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predictions_count: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if self.id is None:
            self.id = uuid.uuid4()
        if self.changed_at is None:
            self.changed_at = utc_now()
