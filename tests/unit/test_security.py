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
