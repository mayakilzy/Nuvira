"""Real HTTP/PostgreSQL session gates for the isolated staging stack."""

import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import jwt
import pytest

from app.config import settings
from app.core.tokens import create_reset_token
from app.database import SessionLocal
from app.models.user import User


API_URL = os.getenv("STAGING_API_URL")
FRONTEND_URL = os.getenv("STAGING_FRONTEND_URL", "http://127.0.0.1:3300")
pytestmark = pytest.mark.skipif(not API_URL, reason="STAGING_API_URL is not configured")


def _assert_isolated_runtime() -> None:
    if urlparse(API_URL).hostname not in {"127.0.0.1", "localhost", "backend"}:
        pytest.fail("STAGING_API_URL must target localhost or the isolated backend service")


def _register(client: httpx.Client, email: str) -> tuple[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "SyntheticPass1234", "full_name": "Synthetic Student"},
    )
    assert response.status_code == 201, response.text
    refresh = client.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert refresh
    return response.json()["access_token"], refresh


def test_refresh_reuse_revokes_family_and_invalid_origin_is_rejected():
    _assert_isolated_runtime()
    unique = str(time.time_ns())
    with httpx.Client(base_url=API_URL, timeout=20) as client:
        _, original_refresh = _register(client, f"rotation-{unique}@example.com")
        rotated = client.post("/auth/refresh", headers={"Origin": FRONTEND_URL})
        assert rotated.status_code == 200, rotated.text
        replacement_refresh = client.cookies.get(settings.REFRESH_COOKIE_NAME)
        assert replacement_refresh and replacement_refresh != original_refresh

        with httpx.Client(base_url=API_URL, timeout=20) as replay:
            replay.cookies.set(settings.REFRESH_COOKIE_NAME, original_refresh, path="/auth")
            assert replay.post("/auth/refresh", headers={"Origin": FRONTEND_URL}).status_code == 401
        assert client.post("/auth/refresh", headers={"Origin": FRONTEND_URL}).status_code == 401

    with httpx.Client(base_url=API_URL, timeout=20) as origin_client:
        _register(origin_client, f"origin-{unique}@example.com")
        assert origin_client.post("/auth/refresh", headers={"Origin": "https://evil.example"}).status_code == 403


def test_logout_password_reset_and_expired_access_token_revoke_access():
    _assert_isolated_runtime()
    unique = str(time.time_ns())
    email = f"revocation-{unique}@example.com"
    with httpx.Client(base_url=API_URL, timeout=20) as client:
        access, _ = _register(client, email)
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {access}"}).status_code == 200
        assert client.post("/auth/logout", headers={"Origin": FRONTEND_URL}).status_code == 200
        assert client.post("/auth/refresh", headers={"Origin": FRONTEND_URL}).status_code == 401

        _, _ = _register(client, f"reset-{unique}@example.com")
        db = SessionLocal()
        try:
            reset_user = db.query(User).filter(User.email == f"reset-{unique}@example.com").one()
            reset_token = create_reset_token(str(reset_user.id))
        finally:
            db.close()
        reset = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "new_password": "ReplacementPass5678"},
        )
        assert reset.status_code == 200, reset.text
        assert client.post("/auth/refresh", headers={"Origin": FRONTEND_URL}).status_code == 401

        now = datetime.now(timezone.utc)
        expired = jwt.encode(
            {
                "sub": "1", "type": "access", "iat": now - timedelta(minutes=2),
                "exp": now - timedelta(minutes=1), "jti": "expired-staging-token",
            },
            settings.JWT_SECRET,
            algorithm="HS256",
        )
        assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
