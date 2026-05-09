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
