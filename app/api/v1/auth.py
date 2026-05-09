from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuditLogRepositoryDep, AuthServiceDep, CurrentUserDep, DbSessionDep
from app.application.auth.use_cases import (
    AuthenticationError,
    EmailAlreadyRegisteredError,
    InactiveUserError,
)
from app.core.security import create_access_token
from app.infrastructure.db.models import UserModel
from app.schemas.auth import (
    AuthResponse,
    BalanceResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

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
    audit_log_repository: AuditLogRepositoryDep,
    session: DbSessionDep,
) -> AuthResponse:
    try:
        result = await auth_service.register(email=str(payload.email), password=payload.password)
        await audit_log_repository.record(
            actor_user_id=result.user.id,
            action="auth.register",
            entity_type="user",
            entity_id=result.user.id,
            metadata={"email": result.user.email},
        )
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
async def login(
    payload: LoginRequest,
    auth_service: AuthServiceDep,
    audit_log_repository: AuditLogRepositoryDep,
    session: DbSessionDep,
) -> AuthResponse:
    try:
        result = await auth_service.login(email=str(payload.email), password=payload.password)
        await audit_log_repository.record(
            actor_user_id=result.user.id,
            action="auth.login",
            entity_type="user",
            entity_id=result.user.id,
            metadata={"email": result.user.email},
        )
        await session.commit()
        return to_auth_response(result)
    except (AuthenticationError, InactiveUserError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc


@router.get("/me", summary="Get current user profile")
async def me(current_user: CurrentUserDep) -> UserResponse:
    return to_user_response(current_user)


@router.post("/refresh", summary="Refresh access token")
async def refresh(
    current_user: CurrentUserDep,
    audit_log_repository: AuditLogRepositoryDep,
    session: DbSessionDep,
) -> AuthResponse:
    await audit_log_repository.record(
        actor_user_id=current_user.id,
        action="auth.refresh",
        entity_type="user",
        entity_id=current_user.id,
        metadata={"email": current_user.email},
    )
    await session.commit()
    return AuthResponse(
        access_token=create_access_token(str(current_user.id)),
        token_type="bearer",
        user=to_user_response(current_user),
    )
