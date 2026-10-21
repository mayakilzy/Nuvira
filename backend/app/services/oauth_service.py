"""Minimal Google OAuth (Authorization Code flow) using httpx — no heavy SDK."""
from __future__ import annotations

from urllib.parse import urlencode

import httpx

from app.config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def build_consent_url(state: str = "") -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    """Exchange the auth code for tokens, then fetch the user's profile.
    Returns {sub, email, name, picture}.
    """
    async with httpx.AsyncClient(timeout=20) as c:
        tok = await c.post(TOKEN_URL, data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        tok.raise_for_status()
        access = tok.json()["access_token"]
        info = await c.get(USERINFO_URL, headers={"Authorization": f"Bearer {access}"})
        info.raise_for_status()
    data = info.json()
    return {
        "sub": data.get("id"),
        "email": data.get("email"),
        "name": data.get("name"),
        "picture": data.get("picture"),
    }
