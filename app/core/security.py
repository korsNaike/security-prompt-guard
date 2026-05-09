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
