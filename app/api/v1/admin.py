from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import AuditLogRepositoryDep, CurrentUserDep, DbSessionDep
from app.domain.users.entities import UserRole
from app.infrastructure.db.repositories.billing_repository import (
    BalanceNotFoundError,
    BillingRepository,
    InsufficientCreditsError,
)
from app.infrastructure.db.repositories.classification_repository import ClassificationRepository
from app.infrastructure.db.repositories.user_repository import UserRepository
from app.infrastructure.ml.loader import model_registry
from app.infrastructure.tasks.maintenance_tasks import recalculate_loyalty_tiers_once
from app.schemas.admin import (
    AdminBalanceAdjustmentRequest,
    AdminBalanceAdjustmentResponse,
    AdminClassificationListResponse,
    AdminClassificationResponse,
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


@router.get("/classifications", summary="Admin classification list")
async def list_classifications(
    current_user: CurrentUserDep,
    session: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> AdminClassificationListResponse:
    require_admin(current_user)
    requests = await ClassificationRepository(session).list_all(limit=limit)
    return AdminClassificationListResponse(
        items=[
            AdminClassificationResponse(
                id=request.id,
                user_id=request.user_id,
                model_code=request.model_code,
                mode=request.mode,
                status=request.status,
                estimated_cost=request.estimated_cost,
                final_cost=request.final_cost,
                label=request.result.label if request.result is not None else None,
                created_at=request.created_at,
                completed_at=request.completed_at,
            )
            for request in requests
        ]
    )


@router.patch("/users/{user_id}/balance", summary="Admin adjust user balance")
async def adjust_user_balance(
    user_id: UUID,
    payload: AdminBalanceAdjustmentRequest,
    current_user: CurrentUserDep,
    audit_log_repository: AuditLogRepositoryDep,
    session: DbSessionDep,
) -> AdminBalanceAdjustmentResponse:
    require_admin(current_user)
    billing_repository = BillingRepository(session)
    try:
        transaction = await billing_repository.adjust_balance(
            user_id=user_id,
            amount_delta=payload.amount_delta,
            idempotency_key=f"admin:{current_user.id}:balance:{user_id}:{uuid4()}",
            description=payload.description,
        )
        await audit_log_repository.record(
            actor_user_id=current_user.id,
            action="admin.balance_adjust",
            entity_type="user_balance",
            entity_id=user_id,
            metadata={
                "amount_delta": payload.amount_delta,
                "description": payload.description,
                "transaction_id": str(transaction.id),
            },
        )
        balance = await billing_repository.get_balance(user_id)
        await session.commit()
        return AdminBalanceAdjustmentResponse(
            user_id=user_id,
            current_balance=balance.current_balance,
            reserved_balance=balance.reserved_balance,
            transaction_id=transaction.id,
            amount=transaction.amount,
            transaction_type=transaction.transaction_type,
        )
    except InsufficientCreditsError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except BalanceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/loyalty-tiers/recalculate", summary="Admin recalculate loyalty tiers")
async def recalculate_loyalty_tiers(
    current_user: CurrentUserDep,
    audit_log_repository: AuditLogRepositoryDep,
    session: DbSessionDep,
) -> dict:
    require_admin(current_user)
    result = await recalculate_loyalty_tiers_once()
    await audit_log_repository.record(
        actor_user_id=current_user.id,
        action="admin.loyalty_recalculate",
        entity_type="loyalty_tier",
        metadata=result,
    )
    await session.commit()
    return result


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
            valid_until=payload.valid_until,
        )
        await session.commit()
        return AdminPromoCodeResponse(
            id=promo_code.id,
            code=promo_code.code,
            credits_amount=promo_code.credits_amount,
            max_activations=promo_code.max_activations,
            valid_until=promo_code.valid_until,
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
