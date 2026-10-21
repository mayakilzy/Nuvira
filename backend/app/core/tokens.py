"""Short-lived, purpose-scoped tokens for email verification and password reset.
Reuses the JWT secret but with a distinct `type`, so an access token can never be
replayed as a verify/reset token and vice-versa.
"""
from datetime import timedelta

from app.core.security import _create_token, decode_token


def create_verify_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(hours=24), "verify_email")


def create_reset_token(user_id: str) -> str:
    return _create_token(user_id, timedelta(hours=1), "reset_password")


def read_token(token: str, expected_type: str) -> str | None:
    payload = decode_token(token)
    if not payload or payload.get("type") != expected_type:
        return None
    return payload.get("sub")
