# Phase 3 Billing Domain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the transactional billing foundation: credit balance operations, idempotent hold/capture/refund transactions, promo code activation, loyalty tier schema, and billing API endpoints.

**Architecture:** Extend the Phase 2 persistence/auth foundation without coupling billing to ML inference execution. Domain enums and calculation helpers stay framework-free; application use cases orchestrate repositories; infrastructure repositories perform SQLAlchemy persistence and row-locking; API routes expose balance, transaction history, mock top-up, promo activation, and loyalty tier reads. Phase 3 prepares the reserve/capture/refund contract for Phase 4 async classification but does not create classification request persistence.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, Alembic, PostgreSQL-compatible schema, SQLite/aiosqlite integration tests, pytest, pytest-asyncio.

---

## Scope Check

Included:

- Billing domain enums and pricing/discount helpers.
- ORM models and migration for:
  - `billing_transactions`
  - `promo_codes`
  - `promo_code_activations`
  - `loyalty_tiers`
  - `loyalty_tier_history`
  - `users.loyalty_tier_id`
- Billing repository with balance row locking where supported.
- Idempotent credit operations:
  - `top_up`
  - `reserve_credits`
  - `capture_reserved_credits`
  - `refund_reserved_credits`
  - `activate_promo_code`
- Initial `initial_grant` transaction during registration.
- Billing API:
  - `GET /api/v1/billing/balance`
  - `GET /api/v1/billing/transactions`
  - `POST /api/v1/billing/top-up`
  - `POST /api/v1/billing/promo-codes/activate`
  - `GET /api/v1/billing/loyalty-tier`

Excluded:

- Real payment gateway.
- Classification request persistence and worker integration. Phase 4 will call `reserve/capture/refund`.
- Batch partial success billing. Phase 5 will call the same primitives per item.
- Monthly loyalty recalculation job. Phase 7 scheduler/admin work can use the schema and helper methods.

Use commit ID `PHASE3` for commits unless the user provides a different ID before execution.

## File Structure

Create or modify these files:

- `app/domain/billing/entities.py` - billing enums and domain dataclasses.
- `app/domain/billing/services.py` - discount calculation helper.
- `app/infrastructure/db/models.py` - add billing, promo, loyalty models and `UserModel.loyalty_tier_id`.
- `alembic/versions/20260509_0002_create_billing_domain.py` - Phase 3 migration.
- `app/infrastructure/db/repositories/billing_repository.py` - billing persistence and atomic balance operations.
- `app/application/auth/use_cases.py` - create `initial_grant` transaction on registration.
- `app/application/billing/use_cases.py` - billing API use cases.
- `app/schemas/billing.py` - billing request/response schemas.
- `app/api/v1/billing.py` - billing endpoints.
- `app/api/v1/router.py` - include billing router.
- `tests/unit/test_billing_domain.py` - enum/helper tests.
- `tests/unit/test_billing_models.py` - ORM default tests.
- `tests/unit/test_billing_migration.py` - migration content tests.
- `tests/integration/test_billing_repository.py` - repository behavior tests with SQLite.
- `tests/unit/test_auth_initial_grant.py` - registration creates initial grant transaction.
- `tests/unit/test_billing_api.py` - API tests with dependency overrides.

---

### Task 1: Billing Domain Types and Pricing Helpers

**Files:**
- Create: `app/domain/billing/entities.py`
- Create: `app/domain/billing/services.py`
- Test: `tests/unit/test_billing_domain.py`

- [ ] **Step 1: Write failing billing domain tests**

Create `tests/unit/test_billing_domain.py`:

```python
import pytest

from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.domain.billing.services import calculate_discounted_cost


def test_transaction_type_values_match_technical_task() -> None:
    assert BillingTransactionType.INITIAL_GRANT.value == "initial_grant"
    assert BillingTransactionType.TOP_UP.value == "top_up"
    assert BillingTransactionType.PROMO_GRANT.value == "promo_grant"
    assert BillingTransactionType.INFERENCE_HOLD.value == "inference_hold"
    assert BillingTransactionType.INFERENCE_CAPTURE.value == "inference_capture"
    assert BillingTransactionType.INFERENCE_REFUND.value == "inference_refund"
    assert BillingTransactionType.ADMIN_ADJUSTMENT.value == "admin_adjustment"
    assert BillingTransactionType.CACHE_HIT_CHARGE.value == "cache_hit_charge"


def test_transaction_status_values_match_technical_task() -> None:
    assert BillingTransactionStatus.PENDING.value == "pending"
    assert BillingTransactionStatus.COMPLETED.value == "completed"
    assert BillingTransactionStatus.FAILED.value == "failed"
    assert BillingTransactionStatus.REFUNDED.value == "refunded"


def test_discounted_cost_uses_ceiling() -> None:
    assert calculate_discounted_cost(base_cost=7, discount_percent=10) == 7
    assert calculate_discounted_cost(base_cost=15, discount_percent=10) == 14
    assert calculate_discounted_cost(base_cost=5, discount_percent=0) == 5


def test_discounted_cost_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=0, discount_percent=0)
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=5, discount_percent=-1)
    with pytest.raises(ValueError):
        calculate_discounted_cost(base_cost=5, discount_percent=101)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/unit/test_billing_domain.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.domain.billing.entities'
```

- [ ] **Step 3: Add billing domain entities**

Create `app/domain/billing/entities.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class BillingTransactionType(StrEnum):
    INITIAL_GRANT = "initial_grant"
    TOP_UP = "top_up"
    PROMO_GRANT = "promo_grant"
    INFERENCE_HOLD = "inference_hold"
    INFERENCE_CAPTURE = "inference_capture"
    INFERENCE_REFUND = "inference_refund"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    CACHE_HIT_CHARGE = "cache_hit_charge"


class BillingTransactionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass(frozen=True)
class BalanceSnapshot:
    user_id: UUID
    current_balance: int
    reserved_balance: int


@dataclass(frozen=True)
class BillingTransaction:
    id: UUID
    user_id: UUID
    amount: int
    transaction_type: BillingTransactionType
    status: BillingTransactionStatus
    idempotency_key: str
    description: str | None
    created_at: datetime
```

- [ ] **Step 4: Add billing service helper**

Create `app/domain/billing/services.py`:

```python
from math import ceil


def calculate_discounted_cost(*, base_cost: int, discount_percent: int) -> int:
    if base_cost <= 0:
        raise ValueError("base_cost must be positive")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("discount_percent must be between 0 and 100")
    return ceil(base_cost * (1 - discount_percent / 100))
```

- [ ] **Step 5: Run billing domain tests**

Run:

```bash
uv run pytest tests/unit/test_billing_domain.py -v
```

Expected:

```text
4 passed
```

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add app/domain/billing/entities.py app/domain/billing/services.py tests/unit/test_billing_domain.py
git commit -m "feat PHASE3: добавить billing domain"
```

---

### Task 2: Billing ORM Models

**Files:**
- Modify: `app/infrastructure/db/models.py`
- Test: `tests/unit/test_billing_models.py`

- [ ] **Step 1: Write failing billing model tests**

Create `tests/unit/test_billing_models.py`:

```python
from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.infrastructure.db.models import (
    BillingTransactionModel,
    LoyaltyTierModel,
    PromoCodeActivationModel,
    PromoCodeModel,
    UserModel,
)


def test_billing_transaction_defaults() -> None:
    transaction = BillingTransactionModel(
        user_id="00000000-0000-0000-0000-000000000001",
        amount=100,
        transaction_type=BillingTransactionType.TOP_UP.value,
        idempotency_key="top-up:1",
    )

    assert transaction.status == BillingTransactionStatus.COMPLETED.value
    assert transaction.amount == 100


def test_promo_code_defaults() -> None:
    promo_code = PromoCodeModel(code="WELCOME100", credits_amount=100)

    assert promo_code.used_count == 0
    assert promo_code.is_active is True


def test_promo_activation_links_user_and_code() -> None:
    activation = PromoCodeActivationModel(
        promo_code_id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
        credits_granted=100,
    )

    assert activation.credits_granted == 100


def test_loyalty_tier_defaults() -> None:
    tier = LoyaltyTierModel(
        code="bronze",
        name="Bronze",
        min_monthly_predictions=0,
        discount_percent=0,
    )

    assert tier.is_active is True


def test_user_has_loyalty_tier_field() -> None:
    user = UserModel(email="user@example.com", hashed_password="hashed")

    assert hasattr(user, "loyalty_tier_id")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/unit/test_billing_models.py -v
```

Expected:

```text
ImportError
```

because billing ORM models are not defined yet.

- [ ] **Step 3: Extend ORM models**

Modify `app/infrastructure/db/models.py` to this complete version:

```python
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
    classification_request_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
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


class LoyaltyTierModel(Base):
    __tablename__ = "loyalty_tiers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_monthly_predictions: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

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


class LoyaltyTierHistoryModel(Base):
    __tablename__ = "loyalty_tier_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    old_tier_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("loyalty_tiers.id"))
    new_tier_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("loyalty_tiers.id"), nullable=False)
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
```

- [ ] **Step 4: Run model tests**

Run:

```bash
uv run pytest tests/unit/test_billing_models.py -v
```

Expected:

```text
5 passed
```

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add app/infrastructure/db/models.py tests/unit/test_billing_models.py
git commit -m "feat PHASE3: добавить billing ORM модели"
```

---

### Task 3: Billing Migration

**Files:**
- Create: `alembic/versions/20260509_0002_create_billing_domain.py`
- Test: `tests/unit/test_billing_migration.py`

- [ ] **Step 1: Write migration content test**

Create `tests/unit/test_billing_migration.py`:

```python
from pathlib import Path


def test_billing_migration_contains_required_tables() -> None:
    migration = Path("alembic/versions/20260509_0002_create_billing_domain.py")

    content = migration.read_text()

    assert 'create_table("billing_transactions"' in content
    assert 'create_table("promo_codes"' in content
    assert 'create_table("promo_code_activations"' in content
    assert 'create_table("loyalty_tiers"' in content
    assert 'create_table("loyalty_tier_history"' in content
    assert "add_column(\"users\"" in content
    assert "idempotency_key" in content
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/unit/test_billing_migration.py -v
```

Expected:

```text
FileNotFoundError
```

- [ ] **Step 3: Add billing migration**

Create `alembic/versions/20260509_0002_create_billing_domain.py`:

```python
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260509_0002"
down_revision: str | None = "20260509_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table("loyalty_tiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("min_monthly_predictions", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.add_column("users", sa.Column("loyalty_tier_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_loyalty_tier_id_loyalty_tiers",
        "users",
        "loyalty_tiers",
        ["loyalty_tier_id"],
        ["id"],
    )

    op.create_table("billing_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("transaction_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("classification_request_id", sa.Uuid(), nullable=True),
        sa.Column("related_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["billing_transactions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index(
        op.f("ix_billing_transactions_user_id"),
        "billing_transactions",
        ["user_id"],
        unique=False,
    )

    op.create_table("promo_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("credits_amount", sa.Integer(), nullable=False),
        sa.Column("max_activations", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table("promo_code_activations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("promo_code_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credits_granted", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["promo_code_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("promo_code_id", "user_id", name="uq_promo_code_activations_code_user"),
    )

    op.create_table("loyalty_tier_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("old_tier_id", sa.Uuid(), nullable=True),
        sa.Column("new_tier_id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("predictions_count", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["new_tier_id"], ["loyalty_tiers.id"]),
        sa.ForeignKeyConstraint(["old_tier_id"], ["loyalty_tiers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("loyalty_tier_history")
    op.drop_table("promo_code_activations")
    op.drop_table("promo_codes")
    op.drop_index(op.f("ix_billing_transactions_user_id"), table_name="billing_transactions")
    op.drop_table("billing_transactions")
    op.drop_constraint("fk_users_loyalty_tier_id_loyalty_tiers", "users", type_="foreignkey")
    op.drop_column("users", "loyalty_tier_id")
    op.drop_table("loyalty_tiers")
```

- [ ] **Step 4: Run migration test**

Run:

```bash
uv run pytest tests/unit/test_billing_migration.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Verify offline migration SQL**

Run:

```bash
uv run alembic upgrade head --sql | rg "CREATE TABLE billing_transactions|CREATE TABLE promo_codes|CREATE TABLE loyalty_tiers|ALTER TABLE users"
```

Expected:

```text
CREATE TABLE loyalty_tiers
ALTER TABLE users ADD COLUMN loyalty_tier_id UUID
CREATE TABLE billing_transactions
CREATE TABLE promo_codes
```

- [ ] **Step 6: Commit Task 3**

Run:

```bash
git add alembic/versions/20260509_0002_create_billing_domain.py tests/unit/test_billing_migration.py
git commit -m "feat PHASE3: добавить billing migration"
```

---

### Task 4: Billing Repository Operations

**Files:**
- Create: `app/infrastructure/db/repositories/billing_repository.py`
- Test: `tests/integration/test_billing_repository.py`

- [ ] **Step 1: Write repository tests**

Create `tests/integration/test_billing_repository.py`:

```python
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.base import Base
from app.infrastructure.db.models import PromoCodeModel
from app.infrastructure.db.repositories.billing_repository import (
    BillingRepository,
    InsufficientCreditsError,
    PromoCodeAlreadyActivatedError,
    PromoCodeInvalidError,
)
from app.infrastructure.db.repositories.user_repository import UserRepository


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


async def create_user(session_factory):
    async with session_factory() as session:
        user_repository = UserRepository(session)
        user = await user_repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()
        return user.id


async def test_top_up_increases_balance_and_is_idempotent(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        first = await repository.top_up(
            user_id=user_id,
            amount=50,
            idempotency_key="top-up:1",
            description="Mock top-up",
        )
        second = await repository.top_up(
            user_id=user_id,
            amount=50,
            idempotency_key="top-up:1",
            description="Mock top-up retry",
        )
        balance = await repository.get_balance(user_id)
        await session.commit()

        assert first.id == second.id
        assert balance.current_balance == 150
        assert balance.reserved_balance == 0


async def test_reserve_capture_and_refund_are_idempotent(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        hold = await repository.reserve_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:hold",
            description="Reserve inference",
        )
        duplicate_hold = await repository.reserve_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:hold",
            description="Reserve inference retry",
        )
        balance_after_hold = await repository.get_balance(user_id)

        capture = await repository.capture_reserved_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:capture",
            related_transaction_id=hold.id,
            description="Capture inference",
        )
        duplicate_capture = await repository.capture_reserved_credits(
            user_id=user_id,
            amount=20,
            idempotency_key="classification:req-1:capture",
            related_transaction_id=hold.id,
            description="Capture inference retry",
        )
        balance_after_capture = await repository.get_balance(user_id)

        assert hold.id == duplicate_hold.id
        assert capture.id == duplicate_capture.id
        assert balance_after_hold.current_balance == 80
        assert balance_after_hold.reserved_balance == 20
        assert balance_after_capture.current_balance == 80
        assert balance_after_capture.reserved_balance == 0


async def test_reserve_rejects_insufficient_balance(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)

        with pytest.raises(InsufficientCreditsError):
            await repository.reserve_credits(
                user_id=user_id,
                amount=101,
                idempotency_key="classification:req-2:hold",
                description="Reserve too much",
            )


async def test_refund_restores_reserved_balance(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        repository = BillingRepository(session)
        hold = await repository.reserve_credits(
            user_id=user_id,
            amount=15,
            idempotency_key="classification:req-3:hold",
            description="Reserve inference",
        )
        await repository.refund_reserved_credits(
            user_id=user_id,
            amount=15,
            idempotency_key="classification:req-3:refund",
            related_transaction_id=hold.id,
            description="Refund failed inference",
        )
        balance = await repository.get_balance(user_id)

        assert balance.current_balance == 100
        assert balance.reserved_balance == 0


async def test_activate_promo_code_grants_credits_once(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        session.add(PromoCodeModel(code="WELCOME100", credits_amount=100, max_activations=2))
        await session.commit()

    async with session_factory() as session:
        repository = BillingRepository(session)
        transaction = await repository.activate_promo_code(user_id=user_id, code="WELCOME100")
        balance = await repository.get_balance(user_id)

        assert transaction.transaction_type == BillingTransactionType.PROMO_GRANT.value
        assert balance.current_balance == 200

        with pytest.raises(PromoCodeAlreadyActivatedError):
            await repository.activate_promo_code(user_id=user_id, code="WELCOME100")


async def test_activate_promo_code_rejects_expired_code(session_factory) -> None:
    user_id = await create_user(session_factory)

    async with session_factory() as session:
        session.add(
            PromoCodeModel(
                code="OLD",
                credits_amount=100,
                valid_until=datetime.now(UTC) - timedelta(days=1),
            )
        )
        await session.commit()

    async with session_factory() as session:
        repository = BillingRepository(session)

        with pytest.raises(PromoCodeInvalidError):
            await repository.activate_promo_code(user_id=user_id, code="OLD")
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/integration/test_billing_repository.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.infrastructure.db.repositories.billing_repository'
```

- [ ] **Step 3: Add billing repository**

Create `app/infrastructure/db/repositories/billing_repository.py`:

```python
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.entities import BillingTransactionStatus, BillingTransactionType
from app.infrastructure.db.models import (
    BillingTransactionModel,
    LoyaltyTierModel,
    PromoCodeActivationModel,
    PromoCodeModel,
    UserBalanceModel,
    UserModel,
)


class InsufficientCreditsError(Exception):
    pass


class BalanceNotFoundError(Exception):
    pass


class PromoCodeInvalidError(Exception):
    pass


class PromoCodeAlreadyActivatedError(Exception):
    pass


class BillingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_balance(self, user_id: UUID) -> UserBalanceModel:
        balance = await self._get_balance_for_update(user_id)
        return balance

    async def list_transactions(self, user_id: UUID, limit: int = 50) -> list[BillingTransactionModel]:
        result = await self.session.execute(
            select(BillingTransactionModel)
            .where(BillingTransactionModel.user_id == user_id)
            .order_by(BillingTransactionModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_loyalty_tier(self, user_id: UUID) -> LoyaltyTierModel | None:
        result = await self.session.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or user.loyalty_tier_id is None:
            return None
        tier_result = await self.session.execute(
            select(LoyaltyTierModel).where(LoyaltyTierModel.id == user.loyalty_tier_id)
        )
        return tier_result.scalar_one_or_none()

    async def create_initial_grant(self, *, user_id: UUID, amount: int) -> BillingTransactionModel:
        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.INITIAL_GRANT,
            idempotency_key=f"user:{user_id}:initial_grant",
            description="Initial registration credits",
        )

    async def top_up(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.TOP_UP,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def reserve_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.current_balance < amount:
            raise InsufficientCreditsError("Insufficient credits")
        balance.current_balance -= amount
        balance.reserved_balance += amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=BillingTransactionType.INFERENCE_HOLD,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def capture_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.reserved_balance < amount:
            raise InsufficientCreditsError("Insufficient reserved credits")
        balance.reserved_balance -= amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=-amount,
            transaction_type=BillingTransactionType.INFERENCE_CAPTURE,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
        )

    async def refund_reserved_credits(
        self,
        *,
        user_id: UUID,
        amount: int,
        idempotency_key: str,
        related_transaction_id: UUID,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        if balance.reserved_balance < amount:
            raise InsufficientCreditsError("Insufficient reserved credits")
        balance.reserved_balance -= amount
        balance.current_balance += amount
        balance.updated_at = datetime.now(UTC)

        return await self._create_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=BillingTransactionType.INFERENCE_REFUND,
            idempotency_key=idempotency_key,
            description=description,
            related_transaction_id=related_transaction_id,
        )

    async def activate_promo_code(self, *, user_id: UUID, code: str) -> BillingTransactionModel:
        normalized_code = code.strip().upper()
        promo_code = await self._get_promo_code_for_update(normalized_code)
        if promo_code is None or not promo_code.is_active:
            raise PromoCodeInvalidError("Promo code is not active")
        if promo_code.valid_until is not None and promo_code.valid_until < datetime.now(UTC):
            raise PromoCodeInvalidError("Promo code has expired")
        if promo_code.max_activations is not None and promo_code.used_count >= promo_code.max_activations:
            raise PromoCodeInvalidError("Promo code activation limit reached")

        existing_activation = await self._get_promo_activation(
            promo_code_id=promo_code.id,
            user_id=user_id,
        )
        if existing_activation is not None:
            raise PromoCodeAlreadyActivatedError("Promo code already activated by user")

        promo_code.used_count += 1
        activation = PromoCodeActivationModel(
            promo_code_id=promo_code.id,
            user_id=user_id,
            credits_granted=promo_code.credits_amount,
        )
        self.session.add(activation)

        return await self._add_positive_balance_transaction(
            user_id=user_id,
            amount=promo_code.credits_amount,
            transaction_type=BillingTransactionType.PROMO_GRANT,
            idempotency_key=f"promo:{promo_code.id}:user:{user_id}",
            description=f"Promo code {promo_code.code}",
        )

    async def _add_positive_balance_transaction(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: BillingTransactionType,
        idempotency_key: str,
        description: str,
    ) -> BillingTransactionModel:
        existing = await self._get_transaction_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing
        if amount <= 0:
            raise ValueError("amount must be positive")

        balance = await self._get_balance_for_update(user_id)
        balance.current_balance += amount
        balance.updated_at = datetime.now(UTC)
        return await self._create_transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            idempotency_key=idempotency_key,
            description=description,
        )

    async def _get_balance_for_update(self, user_id: UUID) -> UserBalanceModel:
        statement = select(UserBalanceModel).where(UserBalanceModel.user_id == user_id)
        if self.session.bind is not None and self.session.bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        balance = result.scalar_one_or_none()
        if balance is None:
            raise BalanceNotFoundError("User balance was not found")
        return balance

    async def _get_promo_code_for_update(self, code: str) -> PromoCodeModel | None:
        statement = select(PromoCodeModel).where(PromoCodeModel.code == code)
        if self.session.bind is not None and self.session.bind.dialect.name != "sqlite":
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def _get_promo_activation(
        self,
        *,
        promo_code_id: UUID,
        user_id: UUID,
    ) -> PromoCodeActivationModel | None:
        result = await self.session.execute(
            select(PromoCodeActivationModel).where(
                PromoCodeActivationModel.promo_code_id == promo_code_id,
                PromoCodeActivationModel.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_transaction_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> BillingTransactionModel | None:
        result = await self.session.execute(
            select(BillingTransactionModel).where(
                BillingTransactionModel.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def _create_transaction(
        self,
        *,
        user_id: UUID,
        amount: int,
        transaction_type: BillingTransactionType,
        idempotency_key: str,
        description: str | None,
        related_transaction_id: UUID | None = None,
    ) -> BillingTransactionModel:
        transaction = BillingTransactionModel(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type.value,
            status=BillingTransactionStatus.COMPLETED.value,
            related_transaction_id=related_transaction_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        self.session.add(transaction)
        await self.session.flush()
        return transaction
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
uv run pytest tests/integration/test_billing_repository.py -v
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add app/infrastructure/db/repositories/billing_repository.py tests/integration/test_billing_repository.py
git commit -m "feat PHASE3: добавить billing repository"
```

---

### Task 5: Registration Initial Grant Transaction

**Files:**
- Modify: `app/application/auth/use_cases.py`
- Modify: `app/api/deps.py`
- Test: `tests/unit/test_auth_initial_grant.py`

- [ ] **Step 1: Write initial grant test**

Create `tests/unit/test_auth_initial_grant.py`:

```python
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
            current_balance=initial_credits,
            reserved_balance=0,
        )
        self.users_by_email[email] = user
        return user


class FakeBillingRepository:
    def __init__(self) -> None:
        self.created_initial_grants: list[tuple[object, int]] = []

    async def create_initial_grant(self, *, user_id, amount: int):
        self.created_initial_grants.append((user_id, amount))
        transaction = type("Transaction", (), {})()
        transaction.transaction_type = BillingTransactionType.INITIAL_GRANT.value
        transaction.amount = amount
        return transaction


async def test_register_creates_initial_grant_transaction() -> None:
    user_repository = FakeUserRepository()
    billing_repository = FakeBillingRepository()
    service = AuthService(
        repository=user_repository,
        billing_repository=billing_repository,
        initial_credits=100,
    )

    result = await service.register(email="user@example.com", password="strong-password")

    assert billing_repository.created_initial_grants == [(result.user.id, 100)]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/unit/test_auth_initial_grant.py -v
```

Expected:

```text
TypeError
```

because `AuthService` does not accept `billing_repository` yet.

- [ ] **Step 3: Update AuthService**

Modify `app/application/auth/use_cases.py` to this complete version:

```python
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
    def __init__(self, repository, initial_credits: int, billing_repository=None) -> None:
        self.repository = repository
        self.initial_credits = initial_credits
        self.billing_repository = billing_repository

    async def register(self, *, email: str, password: str) -> AuthResult:
        existing_user = await self.repository.get_by_email(email)
        if existing_user is not None:
            raise EmailAlreadyRegisteredError("Email is already registered")

        user = await self.repository.create_user_with_balance(
            email=email,
            hashed_password=get_password_hash(password),
            initial_credits=self.initial_credits,
        )
        if self.billing_repository is not None:
            await self.billing_repository.create_initial_grant(
                user_id=user.id,
                amount=self.initial_credits,
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
```

- [ ] **Step 4: Update auth dependency to inject billing repository**

Modify `app/api/deps.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.use_cases import AuthService, InactiveUserError, UserNotFoundError
from app.core.config import settings
from app.core.security import InvalidTokenError, decode_access_token
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.db.session import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(session: DbSessionDep) -> AuthService:
    return AuthService(
        repository=UserRepository(session),
        billing_repository=BillingRepository(session),
        initial_credits=settings.initial_credits,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    auth_service: AuthServiceDep,
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        return await auth_service.get_active_user(UUID(payload.sub))
    except (InvalidTokenError, ValueError, UserNotFoundError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
        ) from exc


CurrentUserDep = Annotated[object, Depends(get_current_user)]
```

- [ ] **Step 5: Run auth tests**

Run:

```bash
uv run pytest tests/unit/test_auth_initial_grant.py tests/unit/test_auth_use_cases.py tests/unit/test_auth_api.py -v
```

Expected:

```text
10 passed
```

- [ ] **Step 6: Commit Task 5**

Run:

```bash
git add app/application/auth/use_cases.py app/api/deps.py tests/unit/test_auth_initial_grant.py
git commit -m "feat PHASE3: фиксировать initial grant при регистрации"
```

---

### Task 6: Billing Use Cases and API

**Files:**
- Create: `app/application/billing/use_cases.py`
- Create: `app/schemas/billing.py`
- Create: `app/api/v1/billing.py`
- Modify: `app/api/v1/router.py`
- Test: `tests/unit/test_billing_api.py`

- [ ] **Step 1: Write billing API tests**

Create `tests/unit/test_billing_api.py`:

```python
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.billing import get_billing_service
from app.domain.billing.entities import BillingTransactionType
from app.infrastructure.db.models import UserBalanceModel, UserModel
from app.main import app


class FakeBillingService:
    def __init__(self) -> None:
        self.user_id = uuid4()

    async def get_balance(self, user_id):
        return {"current_balance": 100, "reserved_balance": 10}

    async def list_transactions(self, user_id):
        return [
            {
                "id": uuid4(),
                "amount": 100,
                "transaction_type": BillingTransactionType.INITIAL_GRANT.value,
                "status": "completed",
                "description": "Initial registration credits",
                "created_at": "2026-05-09T00:00:00Z",
            }
        ]

    async def top_up(self, user_id, amount: int, idempotency_key: str | None):
        return {
            "id": uuid4(),
            "amount": amount,
            "transaction_type": BillingTransactionType.TOP_UP.value,
            "status": "completed",
            "description": "Mock top-up",
            "created_at": "2026-05-09T00:00:00Z",
        }

    async def activate_promo_code(self, user_id, code: str):
        return {
            "id": uuid4(),
            "amount": 50,
            "transaction_type": BillingTransactionType.PROMO_GRANT.value,
            "status": "completed",
            "description": f"Promo code {code}",
            "created_at": "2026-05-09T00:00:00Z",
        }

    async def get_loyalty_tier(self, user_id):
        return {
            "code": "bronze",
            "name": "Bronze",
            "discount_percent": 0,
            "min_monthly_predictions": 0,
        }


@pytest.fixture
def client() -> TestClient:
    user = UserModel(id=uuid4(), email="user@example.com", hashed_password="hashed")
    user.balance = UserBalanceModel(user_id=user.id, current_balance=100, reserved_balance=0)
    service = FakeBillingService()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_billing_service] = lambda: service
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_get_balance(client: TestClient) -> None:
    response = client.get("/api/v1/billing/balance")

    assert response.status_code == 200
    assert response.json() == {"current_balance": 100, "reserved_balance": 10}


def test_list_transactions(client: TestClient) -> None:
    response = client.get("/api/v1/billing/transactions")

    assert response.status_code == 200
    assert response.json()["items"][0]["transaction_type"] == "initial_grant"


def test_top_up(client: TestClient) -> None:
    response = client.post("/api/v1/billing/top-up", json={"amount": 25})

    assert response.status_code == 200
    assert response.json()["amount"] == 25
    assert response.json()["transaction_type"] == "top_up"


def test_activate_promo_code(client: TestClient) -> None:
    response = client.post("/api/v1/billing/promo-codes/activate", json={"code": "WELCOME50"})

    assert response.status_code == 200
    assert response.json()["transaction_type"] == "promo_grant"


def test_get_loyalty_tier(client: TestClient) -> None:
    response = client.get("/api/v1/billing/loyalty-tier")

    assert response.status_code == 200
    assert response.json()["code"] == "bronze"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_billing_api.py -v
```

Expected:

```text
ModuleNotFoundError
```

because billing API does not exist yet.

- [ ] **Step 3: Add billing use cases**

Create `app/application/billing/use_cases.py`:

```python
from uuid import UUID, uuid4

from app.infrastructure.db.repositories.billing_repository import BillingRepository


class BillingService:
    def __init__(self, repository: BillingRepository) -> None:
        self.repository = repository

    async def get_balance(self, user_id: UUID) -> dict:
        balance = await self.repository.get_balance(user_id)
        return {
            "current_balance": balance.current_balance,
            "reserved_balance": balance.reserved_balance,
        }

    async def list_transactions(self, user_id: UUID) -> list[dict]:
        transactions = await self.repository.list_transactions(user_id)
        return [self._transaction_to_dict(transaction) for transaction in transactions]

    async def top_up(self, user_id: UUID, amount: int, idempotency_key: str | None) -> dict:
        transaction = await self.repository.top_up(
            user_id=user_id,
            amount=amount,
            idempotency_key=idempotency_key or f"top-up:{user_id}:{uuid4()}",
            description="Mock top-up",
        )
        return self._transaction_to_dict(transaction)

    async def activate_promo_code(self, user_id: UUID, code: str) -> dict:
        transaction = await self.repository.activate_promo_code(user_id=user_id, code=code)
        return self._transaction_to_dict(transaction)

    async def get_loyalty_tier(self, user_id: UUID) -> dict:
        tier = await self.repository.get_loyalty_tier(user_id)
        if tier is None:
            return {
                "code": "bronze",
                "name": "Bronze",
                "discount_percent": 0,
                "min_monthly_predictions": 0,
            }
        return {
            "code": tier.code,
            "name": tier.name,
            "discount_percent": tier.discount_percent,
            "min_monthly_predictions": tier.min_monthly_predictions,
        }

    def _transaction_to_dict(self, transaction) -> dict:
        return {
            "id": transaction.id,
            "amount": transaction.amount,
            "transaction_type": transaction.transaction_type,
            "status": transaction.status,
            "description": transaction.description,
            "created_at": transaction.created_at,
        }
```

- [ ] **Step 4: Add billing schemas**

Create `app/schemas/billing.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class BalanceResponse(BaseModel):
    current_balance: int
    reserved_balance: int


class BillingTransactionResponse(BaseModel):
    id: UUID
    amount: int
    transaction_type: str
    status: str
    description: str | None
    created_at: datetime


class BillingTransactionListResponse(BaseModel):
    items: list[BillingTransactionResponse]


class TopUpRequest(BaseModel):
    amount: int = Field(gt=0, le=100_000)
    idempotency_key: str | None = Field(default=None, max_length=255)


class PromoCodeActivateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=100)


class LoyaltyTierResponse(BaseModel):
    code: str
    name: str
    discount_percent: int
    min_monthly_predictions: int
```

- [ ] **Step 5: Add billing API routes**

Create `app/api/v1/billing.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUserDep, DbSessionDep
from app.application.billing.use_cases import BillingService
from app.infrastructure.db.repositories.billing_repository import (
    BillingRepository,
    InsufficientCreditsError,
    PromoCodeAlreadyActivatedError,
    PromoCodeInvalidError,
)
from app.schemas.billing import (
    BalanceResponse,
    BillingTransactionListResponse,
    BillingTransactionResponse,
    LoyaltyTierResponse,
    PromoCodeActivateRequest,
    TopUpRequest,
)

router = APIRouter()


def get_billing_service(session: DbSessionDep) -> BillingService:
    return BillingService(repository=BillingRepository(session))


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]


@router.get("/balance", summary="Get current balance")
async def get_balance(
    current_user: CurrentUserDep,
    billing_service: BillingServiceDep,
) -> BalanceResponse:
    return BalanceResponse(**await billing_service.get_balance(current_user.id))


@router.get("/transactions", summary="List billing transactions")
async def list_transactions(
    current_user: CurrentUserDep,
    billing_service: BillingServiceDep,
) -> BillingTransactionListResponse:
    items = await billing_service.list_transactions(current_user.id)
    return BillingTransactionListResponse(
        items=[BillingTransactionResponse(**item) for item in items]
    )


@router.post("/top-up", summary="Mock top-up balance")
async def top_up(
    payload: TopUpRequest,
    current_user: CurrentUserDep,
    billing_service: BillingServiceDep,
    session: DbSessionDep,
) -> BillingTransactionResponse:
    try:
        transaction = await billing_service.top_up(
            current_user.id,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
        )
        await session.commit()
        return BillingTransactionResponse(**transaction)
    except InsufficientCreditsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/promo-codes/activate", summary="Activate promo code")
async def activate_promo_code(
    payload: PromoCodeActivateRequest,
    current_user: CurrentUserDep,
    billing_service: BillingServiceDep,
    session: DbSessionDep,
) -> BillingTransactionResponse:
    try:
        transaction = await billing_service.activate_promo_code(current_user.id, payload.code)
        await session.commit()
        return BillingTransactionResponse(**transaction)
    except PromoCodeAlreadyActivatedError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PromoCodeInvalidError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/loyalty-tier", summary="Get current loyalty tier")
async def get_loyalty_tier(
    current_user: CurrentUserDep,
    billing_service: BillingServiceDep,
) -> LoyaltyTierResponse:
    return LoyaltyTierResponse(**await billing_service.get_loyalty_tier(current_user.id))
```

- [ ] **Step 6: Include billing router**

Modify `app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import auth, billing, classifications, models

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(
    classifications.router,
    prefix="/classifications",
    tags=["classifications"],
)
```

- [ ] **Step 7: Run billing API tests**

Run:

```bash
uv run pytest tests/unit/test_billing_api.py -v
```

Expected:

```text
5 passed
```

- [ ] **Step 8: Commit Task 6**

Run:

```bash
git add app/application/billing/use_cases.py app/schemas/billing.py app/api/v1/billing.py app/api/v1/router.py tests/unit/test_billing_api.py
git commit -m "feat PHASE3: добавить billing API"
```

---

### Task 7: Final Phase 3 Verification

**Files:**
- Modify only if verification reveals a concrete failure.

- [ ] **Step 1: Run full tests**

Run:

```bash
uv run pytest
```

Expected:

```text
passed
```

with all Phase 1, Phase 2 and Phase 3 tests passing.

- [ ] **Step 2: Run lint**

Run:

```bash
uv run ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Verify billing routes are registered**

Run:

```bash
uv run python -c "from app.main import app; paths={route.path for route in app.routes}; print('/api/v1/billing/balance' in paths); print('/api/v1/billing/top-up' in paths); print('/api/v1/billing/promo-codes/activate' in paths); print('/api/v1/billing/loyalty-tier' in paths)"
```

Expected:

```text
True
True
True
True
```

- [ ] **Step 4: Verify OpenAPI has billing routes**

Run:

```bash
uv run python -c "from app.main import app; schema=app.openapi(); print('/api/v1/billing/balance' in schema['paths']); print('/api/v1/billing/transactions' in schema['paths']); print('/api/v1/billing/top-up' in schema['paths']); print('/api/v1/billing/promo-codes/activate' in schema['paths']); print('/api/v1/billing/loyalty-tier' in schema['paths'])"
```

Expected:

```text
True
True
True
True
True
```

- [ ] **Step 5: Verify Alembic SQL render includes Phase 3 tables**

Run:

```bash
uv run alembic upgrade head --sql | rg "CREATE TABLE billing_transactions|CREATE TABLE promo_codes|CREATE TABLE promo_code_activations|CREATE TABLE loyalty_tiers|CREATE TABLE loyalty_tier_history"
```

Expected:

```text
CREATE TABLE loyalty_tiers
CREATE TABLE billing_transactions
CREATE TABLE promo_codes
CREATE TABLE promo_code_activations
CREATE TABLE loyalty_tier_history
```

- [ ] **Step 6: Inspect git status**

Run:

```bash
git status --short
```

Expected:

```text
```

No output except intentionally ignored local generated files.

- [ ] **Step 7: Commit final fixes only if verification required changes**

If Step 1-5 required corrections, run:

```bash
git add app tests alembic docs/superpowers/plans/2026-05-09-phase-3-billing-domain.md
git commit -m "fix PHASE3: исправить замечания финальной проверки"
```

If no corrections were required, do not create an empty commit.

---

## Self-Review

Spec coverage:

- Balance service with row locks: Task 4 uses `with_for_update()` for non-SQLite dialects.
- Hold/capture/refund transactions: Task 4.
- Idempotency keys: Task 4 checks existing transaction before mutation.
- Promo code activation: Task 4 and Task 6.
- Loyalty tier schema: Task 2 and Task 3.
- Billing endpoints from TЗ: Task 6.
- Initial grant transaction: Task 5.

Deferred scope:

- Real payment gateway is explicitly out of MVP.
- Classification request persistence and worker calls to reserve/capture/refund are Phase 4.
- Batch partial failure billing is Phase 5.
- Periodic monthly loyalty recalculation is scheduler/admin work for later phases; Phase 3 creates schema and read API.

Placeholder scan:

- The plan contains concrete files, code blocks and commands.
- The plan avoids open-ended markers, deferred-code notes and symbolic file placeholders.

Type consistency:

- `BillingTransactionType`, `BillingTransactionStatus`, `BillingRepository`, `BillingService`, `BillingTransactionModel`, `PromoCodeModel`, `PromoCodeActivationModel`, `LoyaltyTierModel`, `LoyaltyTierHistoryModel`, `BalanceResponse`, `BillingTransactionResponse`, `TopUpRequest`, `PromoCodeActivateRequest`, and `LoyaltyTierResponse` are defined before use.
- Transaction type strings match `docs/TECHNICAL_TASK.MD`.
- Idempotency examples follow `classification:{request_id}:hold/capture/refund`, `promo:{promo_code.id}:user:{user_id}`, and `top-up:{user_id}:{uuid}` patterns.

