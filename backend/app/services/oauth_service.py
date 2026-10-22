"""Google OAuth authorization-code flow with server-side state and PKCE."""
from __future__ import annotations

import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.security import OAuthExchange, OAuthState

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


class InvalidOAuthState(Exception):
    pass


class OAuthProviderError(Exception):
    pass


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _b64_sha256(value: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(value.encode()).digest()).rstrip(b"=").decode()


def safe_return_path(value: str | None) -> str:
    if not value or len(value) > 255:
        return "/dashboard"
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or not value.startswith("/") or value.startswith("//"):
        return "/dashboard"
    return value


def begin(db: Session, return_path: str | None = None) -> str:
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    db.add(OAuthState(
        id=str(uuid.uuid4()), state_hash=_hash(state), code_verifier=verifier,
        return_path=safe_return_path(return_path),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))
    db.commit()
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": _b64_sha256(verifier),
        "code_challenge_method": "S256",
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def consume_state(db: Session, state: str) -> OAuthState:
    row = db.query(OAuthState).filter(OAuthState.state_hash == _hash(state)).with_for_update().first()
    if not row or row.used_at is not None or _aware(row.expires_at) <= datetime.now(timezone.utc):
        raise InvalidOAuthState()
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return row


async def exchange_code(code: str, code_verifier: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(TOKEN_URL, data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            })
            token_response.raise_for_status()
            access = token_response.json()["access_token"]
            info_response = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access}"})
            info_response.raise_for_status()
        data = info_response.json()
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise OAuthProviderError() from exc
    return {
        "sub": data.get("sub"), "email": data.get("email"),
        "email_verified": data.get("email_verified") is True,
        "name": data.get("name"), "picture": data.get("picture"),
    }


def create_exchange(db: Session, user_id: int, return_path: str) -> str:
    raw = secrets.token_urlsafe(40)
    db.add(OAuthExchange(
        id=str(uuid.uuid4()), code_hash=_hash(raw), user_id=user_id,
        return_path=safe_return_path(return_path),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    ))
    db.commit()
    return raw


def consume_exchange(db: Session, raw: str) -> OAuthExchange:
    row = db.query(OAuthExchange).filter(OAuthExchange.code_hash == _hash(raw)).with_for_update().first()
    if not row or row.used_at is not None or _aware(row.expires_at) <= datetime.now(timezone.utc):
        raise InvalidOAuthState()
    row.used_at = datetime.now(timezone.utc)
    db.commit()
    return row
