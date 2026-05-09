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
