# Phase 2 Persistence and Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Phase 2 persistence and authentication foundation: SQLAlchemy models, Alembic migration, user registration, login, JWT-protected `/me`, and initial balance creation.

**Architecture:** Keep the existing clean layering. API routes use application services and dependencies; application services orchestrate repositories and security helpers; domain objects stay framework-free; infrastructure owns SQLAlchemy models, sessions and repositories. Phase 2 creates only user/auth/balance persistence, leaving transactional inference billing, promo codes and loyalty recalculation for Phase 3.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, Alembic, SQLite/aiosqlite for repository tests, pwdlib Argon2 password hashing, PyJWT, pytest, pytest-asyncio, httpx/TestClient.

---

## Scope Check

Included:

- SQLAlchemy declarative base and ORM models for `users` and `user_balances`.
- Alembic configuration and first migration.
- Password hashing with Argon2 through `pwdlib`.
- JWT access token creation and validation with `PyJWT`.
- Auth API:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
- User balance initialization with `settings.initial_credits`.
- Repository tests using async SQLite.
- API tests using dependency overrides.

Excluded:

- Refresh tokens. The technical task marks refresh tokens as optional.
- Admin user management.
- Balance top-up, transactions, promo codes and loyalty recalculation. Those belong to Phase 3.
- Persistent classification requests. That belongs to Phase 4.

Use commit ID `PHASE2` for commits unless the user provides a different ID before execution.

## File Structure

Create or modify these files:

- `pyproject.toml` - add `pwdlib[argon2]`, `pyjwt`, `aiosqlite`.
- `app/core/config.py` - add JWT algorithm and access-token TTL settings.
- `app/core/security.py` - password hashing, password verification, JWT creation/decoding.
- `app/domain/users/entities.py` - domain enums and immutable user/balance DTOs.
- `app/infrastructure/db/base.py` - SQLAlchemy declarative base.
- `app/infrastructure/db/models.py` - `UserModel` and `UserBalanceModel`.
- `app/infrastructure/db/session.py` - keep engine/session, importable dependency.
- `app/infrastructure/db/repositories/user_repository.py` - async user persistence.
- `app/application/auth/use_cases.py` - register, login and current-user loading.
- `app/schemas/auth.py` - auth request/response schemas.
- `app/api/deps.py` - database and current-user FastAPI dependencies.
- `app/api/v1/auth.py` - auth endpoints.
- `app/api/v1/router.py` - include auth router.
- `alembic.ini` - Alembic config.
- `alembic/env.py` - migration env wired to metadata and settings.
- `alembic/versions/20260509_0001_create_users_and_balances.py` - first migration.
- `tests/unit/test_security.py` - password/JWT tests.
- `tests/integration/test_user_repository.py` - repository tests on SQLite.
- `tests/unit/test_auth_api.py` - API route tests with dependency override.

---

### Task 1: Security Dependencies and Settings

**Files:**
- Modify: `pyproject.toml`
- Modify: `app/core/config.py`
- Create: `app/core/security.py`
- Test: `tests/unit/test_security.py`

- [ ] **Step 1: Write failing security tests**

Create `tests/unit/test_security.py`:

```python
import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies() -> None:
    hashed = get_password_hash("strong-password")

    assert hashed != "strong-password"
    assert verify_password("strong-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_access_token_roundtrip() -> None:
    token = create_access_token(subject="user-id-1")

    payload = decode_access_token(token)

    assert payload.sub == "user-id-1"


def test_invalid_token_is_rejected() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-valid-token")
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
uv run pytest tests/unit/test_security.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.core.security'
```

- [ ] **Step 3: Add dependencies**

Modify `pyproject.toml` dependencies so the list includes these additional packages:

```toml
dependencies = [
    "aiosqlite>=0.20.0",
    "alembic>=1.16.0",
    "asyncpg>=0.30.0",
    "celery[redis]>=5.5.0",
    "fastapi[standard]>=0.115.0",
    "pwdlib[argon2]>=0.2.1",
    "pydantic-settings>=2.9.0",
    "pyjwt>=2.10.0",
    "pyyaml>=6.0.2",
    "redis>=5.2.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "transformers>=4.50.0",
]
```

- [ ] **Step 4: Add JWT settings**

Modify `app/core/config.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UniClassify Platform"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+asyncpg://uniclassify:uniclassify@postgres:5432/uniclassify"
    )
    redis_url: str = "redis://redis:6379/0"
    model_config_path: str = "config/models.yml"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    initial_credits: int = 100
    cache_hit_cost: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
```

- [ ] **Step 5: Create security helpers**

Create `app/core/security.py`:

```python
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


class InvalidTokenError(Exception):
    """Raised when a JWT cannot be decoded or misses required claims."""


@dataclass(frozen=True)
class TokenPayload:
    sub: str
    exp: datetime


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        subject = payload.get("sub")
        expires_at = payload.get("exp")
        if not isinstance(subject, str) or expires_at is None:
            raise InvalidTokenError("Token does not contain required claims")
        return TokenPayload(sub=subject, exp=datetime.fromtimestamp(int(expires_at), tz=UTC))
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError("Invalid access token") from exc
```

- [ ] **Step 6: Sync dependencies**

Run:

```bash
uv sync
```

Expected:

```text
Command exits with status 0 and updates `uv.lock`.
```

- [ ] **Step 7: Run security tests**

Run:

```bash
uv run pytest tests/unit/test_security.py -v
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Commit Task 1**

Run:

```bash
git add pyproject.toml uv.lock app/core/config.py app/core/security.py tests/unit/test_security.py
git commit -m "feat PHASE2: добавить security helpers для auth"
```

---

### Task 2: User Domain and SQLAlchemy Models

**Files:**
- Create: `app/domain/users/entities.py`
- Create: `app/infrastructure/db/base.py`
- Create: `app/infrastructure/db/models.py`
- Test: `tests/unit/test_user_models.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/unit/test_user_models.py`:

```python
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
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/unit/test_user_models.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.domain.users'
```

- [ ] **Step 3: Add user domain entities**

Create `app/domain/users/entities.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class UserBalance:
    user_id: UUID
    current_balance: int
    reserved_balance: int
```

- [ ] **Step 4: Add SQLAlchemy base**

Create `app/infrastructure/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 5: Add ORM models**

Create `app/infrastructure/db/models.py`:

```python
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    balance: Mapped["UserBalanceModel"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )


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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped[UserModel] = relationship(back_populates="balance", lazy="selectin")
```

- [ ] **Step 6: Run model tests**

Run:

```bash
uv run pytest tests/unit/test_user_models.py -v
```

Expected:

```text
2 passed
```

- [ ] **Step 7: Commit Task 2**

Run:

```bash
git add app/domain/users/entities.py app/infrastructure/db/base.py app/infrastructure/db/models.py tests/unit/test_user_models.py
git commit -m "feat PHASE2: добавить модели пользователей и баланса"
```

---

### Task 3: Alembic Migration Foundation

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/20260509_0001_create_users_and_balances.py`
- Test: `tests/unit/test_alembic_migration.py`

- [ ] **Step 1: Write migration file test**

Create `tests/unit/test_alembic_migration.py`:

```python
from pathlib import Path


def test_initial_migration_contains_users_and_balances() -> None:
    migration = Path("alembic/versions/20260509_0001_create_users_and_balances.py")

    content = migration.read_text()

    assert "create_table(\"users\"" in content
    assert "create_table(\"user_balances\"" in content
    assert "uq_user_balances_user_id" in content
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```bash
uv run pytest tests/unit/test_alembic_migration.py -v
```

Expected:

```text
FileNotFoundError
```

- [ ] **Step 3: Add Alembic config**

Create `alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://uniclassify:uniclassify@postgres:5432/uniclassify

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 4: Add Alembic env**

Create `alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db import models

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 5: Add first migration**

Create `alembic/versions/20260509_0001_create_users_and_balances.py`:

```python
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260509_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "user_balances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("current_balance", sa.Integer(), nullable=False),
        sa.Column("reserved_balance", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_user_balances_user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_balances")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
```

- [ ] **Step 6: Run migration file test**

Run:

```bash
uv run pytest tests/unit/test_alembic_migration.py -v
```

Expected:

```text
1 passed
```

- [ ] **Step 7: Verify Alembic can render SQL offline**

Run:

```bash
uv run alembic upgrade head --sql
```

Expected:

```text
CREATE TABLE users
CREATE TABLE user_balances
```

- [ ] **Step 8: Commit Task 3**

Run:

```bash
git add alembic.ini alembic/env.py alembic/versions/20260509_0001_create_users_and_balances.py tests/unit/test_alembic_migration.py
git commit -m "feat PHASE2: добавить миграции users и balances"
```

---

### Task 4: User Repository

**Files:**
- Create: `app/infrastructure/db/repositories/user_repository.py`
- Test: `tests/integration/test_user_repository.py`

- [ ] **Step 1: Write repository integration tests**

Create `tests/integration/test_user_repository.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.infrastructure.db.base import Base
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


async def test_create_user_with_initial_balance(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)

        user = await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()

        assert user.email == "user@example.com"
        assert user.balance.current_balance == 100
        assert user.balance.reserved_balance == 0


async def test_get_user_by_email(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)
        await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()

    async with session_factory() as session:
        repository = UserRepository(session)
        user = await repository.get_by_email("user@example.com")

        assert user is not None
        assert user.email == "user@example.com"


async def test_get_user_by_id(session_factory) -> None:
    async with session_factory() as session:
        repository = UserRepository(session)
        created = await repository.create_user_with_balance(
            email="user@example.com",
            hashed_password="hashed-password",
            initial_credits=100,
        )
        await session.commit()
        user_id = created.id

    async with session_factory() as session:
        repository = UserRepository(session)
        user = await repository.get_by_id(user_id)

        assert user is not None
        assert user.id == user_id
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/integration/test_user_repository.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.infrastructure.db.repositories'
```

- [ ] **Step 3: Add user repository**

Create `app/infrastructure/db/repositories/user_repository.py`:

```python
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

    async def create_user_with_balance(
        self,
        *,
        email: str,
        hashed_password: str,
        initial_credits: int,
    ) -> UserModel:
        user = UserModel(email=email, hashed_password=hashed_password)
        user.balance = UserBalanceModel(current_balance=initial_credits, reserved_balance=0)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user, attribute_names=["balance"])
        return user
```

- [ ] **Step 4: Run repository tests**

Run:

```bash
uv run pytest tests/integration/test_user_repository.py -v
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Commit Task 4**

Run:

```bash
git add app/infrastructure/db/repositories/user_repository.py tests/integration/test_user_repository.py
git commit -m "feat PHASE2: добавить user repository"
```

---

### Task 5: Auth Use Cases

**Files:**
- Create: `app/application/auth/use_cases.py`
- Test: `tests/unit/test_auth_use_cases.py`

- [ ] **Step 1: Write auth use case tests**

Create `tests/unit/test_auth_use_cases.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_auth_use_cases.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.application.auth'
```

- [ ] **Step 3: Add auth use cases**

Create `app/application/auth/use_cases.py`:

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
```

- [ ] **Step 4: Run auth use case tests**

Run:

```bash
uv run pytest tests/unit/test_auth_use_cases.py -v
```

Expected:

```text
6 passed
```

- [ ] **Step 5: Commit Task 5**

Run:

```bash
git add app/application/auth/use_cases.py tests/unit/test_auth_use_cases.py
git commit -m "feat PHASE2: добавить auth use cases"
```

---

### Task 6: Auth Schemas, Dependencies and API Routes

**Files:**
- Create: `app/schemas/auth.py`
- Create: `app/api/deps.py`
- Create: `app/api/v1/auth.py`
- Modify: `app/api/v1/router.py`
- Test: `tests/unit/test_auth_api.py`

- [ ] **Step 1: Write auth API tests**

Create `tests/unit/test_auth_api.py`:

```python
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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/unit/test_auth_api.py -v
```

Expected:

```text
ModuleNotFoundError: No module named 'app.api.deps'
```

- [ ] **Step 3: Add auth schemas**

Create `app/schemas/auth.py`:

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class BalanceResponse(BaseModel):
    current_balance: int
    reserved_balance: int


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    balance: BalanceResponse


class AuthResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
```

- [ ] **Step 4: Add FastAPI dependencies**

Create `app/api/deps.py`:

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.use_cases import AuthService, InactiveUserError, UserNotFoundError
from app.core.config import settings
from app.core.security import InvalidTokenError, decode_access_token
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.db.session import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(session: DbSessionDep) -> AuthService:
    return AuthService(
        repository=UserRepository(session),
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

- [ ] **Step 5: Add auth routes**

Create `app/api/v1/auth.py`:

```python
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuthServiceDep, CurrentUserDep, DbSessionDep
from app.application.auth.use_cases import (
    AuthenticationError,
    EmailAlreadyRegisteredError,
    InactiveUserError,
)
from app.infrastructure.db.models import UserModel
from app.schemas.auth import AuthResponse, BalanceResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter()


def to_user_response(user: UserModel) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        balance=BalanceResponse(
            current_balance=user.balance.current_balance,
            reserved_balance=user.balance.reserved_balance,
        ),
    )


def to_auth_response(result) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token,
        token_type=result.token_type,
        user=to_user_response(result.user),
    )


@router.post("/register", summary="Register user")
async def register(
    payload: RegisterRequest,
    auth_service: AuthServiceDep,
    session: DbSessionDep,
) -> AuthResponse:
    try:
        result = await auth_service.register(email=str(payload.email), password=payload.password)
        await session.commit()
        return to_auth_response(result)
    except EmailAlreadyRegisteredError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        ) from exc


@router.post("/login", summary="Login user")
async def login(payload: LoginRequest, auth_service: AuthServiceDep) -> AuthResponse:
    try:
        result = await auth_service.login(email=str(payload.email), password=payload.password)
        return to_auth_response(result)
    except (AuthenticationError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc


@router.get("/me", summary="Get current user profile")
async def me(current_user: CurrentUserDep) -> UserResponse:
    return to_user_response(current_user)
```

- [ ] **Step 6: Include auth router**

Modify `app/api/v1/router.py`:

```python
from fastapi import APIRouter

from app.api.v1 import auth, classifications, models

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(
    classifications.router,
    prefix="/classifications",
    tags=["classifications"],
)
```

- [ ] **Step 7: Run auth API tests**

Run:

```bash
uv run pytest tests/unit/test_auth_api.py -v
```

Expected:

```text
3 passed
```

- [ ] **Step 8: Commit Task 6**

Run:

```bash
git add app/schemas/auth.py app/api/deps.py app/api/v1/auth.py app/api/v1/router.py tests/unit/test_auth_api.py
git commit -m "feat PHASE2: добавить auth API"
```

---

### Task 7: Final Phase 2 Verification

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

with all Phase 1 and Phase 2 tests passing.

- [ ] **Step 2: Run lint**

Run:

```bash
uv run ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Verify FastAPI imports and route count**

Run:

```bash
uv run python -c "from app.main import app; print(app.title); print('/api/v1/auth/register' in {route.path for route in app.routes})"
```

Expected:

```text
UniClassify Platform
True
```

- [ ] **Step 4: Verify OpenAPI has auth routes**

Run:

```bash
uv run python -c "from app.main import app; schema = app.openapi(); print('/api/v1/auth/register' in schema['paths']); print('/api/v1/auth/login' in schema['paths']); print('/api/v1/auth/me' in schema['paths'])"
```

Expected:

```text
True
True
True
```

- [ ] **Step 5: Verify migration SQL renders**

Run:

```bash
uv run alembic upgrade head --sql
```

Expected output includes:

```text
CREATE TABLE users
CREATE TABLE user_balances
```

- [ ] **Step 6: Inspect git status**

Run:

```bash
git status --short
```

Expected:

```text
```

No output except intentionally ignored local files that were already untracked before this phase, such as `.DS_Store`.

- [ ] **Step 7: Commit final fixes only if verification required changes**

If Step 1-5 required corrections, run:

```bash
git add app tests alembic pyproject.toml uv.lock alembic.ini
git commit -m "fix PHASE2: исправить замечания финальной проверки"
```

If no corrections were required, do not create an empty commit.

---

## Self-Review

Spec coverage:

- SQLAlchemy models: Task 2.
- Alembic migrations: Task 3.
- Register/login/me endpoints: Task 6.
- Password hashing: Task 1.
- JWT access token: Task 1 and Task 5.
- User balance initialization: Task 4 and Task 5.

Deferred scope:

- Refresh token is optional in the technical task and intentionally deferred.
- Billing transactions, promo codes and loyalty tier recalculation are Phase 3.
- Classification persistence and async request lifecycle are Phase 4.

Placeholder scan:

- The plan contains concrete files, code blocks and commands.
- The plan avoids open-ended markers, deferred-code notes and symbolic file placeholders.

Type consistency:

- `UserModel`, `UserBalanceModel`, `UserRepository`, `AuthService`, `AuthResult`, `RegisterRequest`, `LoginRequest`, `AuthResponse`, `UserResponse`, `BalanceResponse`, `get_auth_service` and `get_current_user` are defined before use.
- `UserRole.USER.value` matches technical task role value `user`.
- JWT subject is consistently `str(user.id)` and decoded into `UUID(payload.sub)` in the current-user dependency.
