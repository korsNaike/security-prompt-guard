from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUserDep, DbSessionDep
from app.domain.users.entities import UserRole
from app.infrastructure.db.repositories.billing_repository import BillingRepository
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.ml.loader import model_registry
from app.schemas.admin import (
    AdminPromoCodeCreateRequest,
    AdminPromoCodeResponse,
    AdminUserListResponse,
    AdminUserResponse,
)
from app.schemas.models import ModelInfo, ModelListResponse

router = APIRouter()


def require_admin(current_user) -> None:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role is required",
        )


@router.get("/models", summary="Admin model catalog")
async def list_admin_models(current_user: CurrentUserDep) -> ModelListResponse:
    require_admin(current_user)
    return ModelListResponse(
        items=[
            ModelInfo(
                model_code=descriptor.model_code,
                product_name=descriptor.product_name,
                model_name=descriptor.model_name,
                version=descriptor.model_version,
                task_type=descriptor.task_type,
                supported_modes=descriptor.supported_modes,
                labels=descriptor.labels,
                pricing=descriptor.pricing,
            )
            for descriptor in model_registry.list_models()
        ]
    )


@router.get("/users", summary="Admin user list")
async def list_users(
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> AdminUserListResponse:
    require_admin(current_user)
    users = await UserRepository(session).list_users()
    return AdminUserListResponse(
        items=[
            AdminUserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                current_balance=user.balance.current_balance,
                reserved_balance=user.balance.reserved_balance,
                created_at=user.created_at,
            )
            for user in users
        ]
    )


@router.post("/promo-codes", summary="Admin create promo code")
async def create_promo_code(
    payload: AdminPromoCodeCreateRequest,
    current_user: CurrentUserDep,
    session: DbSessionDep,
) -> AdminPromoCodeResponse:
    require_admin(current_user)
    try:
        promo_code = await BillingRepository(session).create_promo_code(
            code=payload.code,
            credits_amount=payload.credits_amount,
            max_activations=payload.max_activations,
        )
        await session.commit()
        return AdminPromoCodeResponse(
            id=promo_code.id,
            code=promo_code.code,
            credits_amount=promo_code.credits_amount,
            max_activations=promo_code.max_activations,
            used_count=promo_code.used_count,
            is_active=promo_code.is_active,
            created_at=promo_code.created_at,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Promo code already exists",
        ) from exc
