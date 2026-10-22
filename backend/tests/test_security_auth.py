from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import jwt

from app.config import settings
from app.core.security import _create_token, create_access_token, decode_token
from app.core.tokens import create_reset_token
from app.models.security import OAuthExchange, OAuthState, RefreshSession
from app.models.user import User
from app.services import oauth_service
from tests.conftest import TestingSessionLocal, engine


def test_jwt_rejects_tamper_wrong_algorithm_expiry_and_wrong_purpose():
    token = create_access_token("42")
    assert decode_token(token)["sub"] == "42"
    head, body, sig = token.split(".")
    assert decode_token(f"{head}.{body}.{sig[:-1]}x") is None
    wrong_alg = jwt.encode(
        {"sub": "42", "type": "access", "iat": 1, "exp": 9999999999, "jti": "x"},
        "different-secret-that-is-long-enough-for-hs384-testing-1234567890", algorithm="HS384",
    )
    assert decode_token(wrong_alg) is None
    expired = _create_token("42", timedelta(seconds=-1), "access")
    assert decode_token(expired) is None
    assert decode_token(_create_token("42", timedelta(minutes=1), "reset_password"))["type"] != "access"


def _oauth_tables():
    OAuthExchange.__table__.drop(engine, checkfirst=True)
    OAuthState.__table__.drop(engine, checkfirst=True)
    OAuthState.__table__.create(engine)
    OAuthExchange.__table__.create(engine)


def test_oauth_state_pkce_single_use_and_no_bearer_in_redirect(client, monkeypatch):
    _oauth_tables()
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    start = client.get("/auth/google?return_path=%2Fsettings", follow_redirects=False)
    assert start.status_code in (302, 307)
    query = parse_qs(urlparse(start.headers["location"]).query)
    assert query["state"][0]
    assert query["code_challenge_method"] == ["S256"]

    async def verified_profile(code, verifier):
        assert code == "provider-code"
        assert verifier
        return {"sub": "google-1", "email": "oauth@example.com", "email_verified": True,
                "name": "OAuth User", "picture": None}

    monkeypatch.setattr(oauth_service, "exchange_code", verified_profile)
    state = query["state"][0]
    callback = client.get(
        f"/auth/google/callback?code=provider-code&state={state}", follow_redirects=False
    )
    assert callback.status_code == 303
    location = callback.headers["location"]
    assert "oauth_code=" in location
    assert "access_token" not in location and "refresh_token" not in location
    assert client.get(
        f"/auth/google/callback?code=provider-code&state={state}", follow_redirects=False
    ).status_code == 400

    exchange_code = parse_qs(urlparse(location).query)["oauth_code"][0]
    exchanged = client.post("/auth/oauth/exchange", json={"code": exchange_code})
    assert exchanged.status_code == 200
    assert exchanged.json()["return_path"] == "/settings"
    assert "refresh_token" not in exchanged.json()
    assert client.post("/auth/oauth/exchange", json={"code": exchange_code}).status_code == 400


def test_refresh_rotation_reuse_detection_and_logout(client):
    registered = client.post("/auth/register", json={
        "email": "session@example.com", "password": "StrongPass1234",
    })
    assert registered.status_code == 201
    first = client.cookies.get(settings.REFRESH_COOKIE_NAME)
    refreshed = client.post("/auth/refresh")
    assert refreshed.status_code == 200
    second = client.cookies.get(settings.REFRESH_COOKIE_NAME)
    assert first != second

    client.cookies.set(settings.REFRESH_COOKIE_NAME, first, path="/auth")
    assert client.post("/auth/refresh").status_code == 401
    client.cookies.set(settings.REFRESH_COOKIE_NAME, second, path="/auth")
    assert client.post("/auth/refresh").status_code == 401

    client.post("/auth/login", json={"email": "session@example.com", "password": "StrongPass1234"})
    assert client.post("/auth/logout").status_code == 200
    assert client.post("/auth/refresh").status_code == 401


def test_password_reset_revokes_all_refresh_sessions(client):
    registered = client.post("/auth/register", json={
        "email": "reset@example.com", "password": "StrongPass1234",
    })
    assert registered.status_code == 201
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == "reset@example.com").one()
        token = create_reset_token(str(user.id))
    finally:
        db.close()
    reset = client.post("/auth/reset-password", json={
        "token": token, "new_password": "NewStrongPass5678",
    })
    assert reset.status_code == 200
    assert client.post("/auth/refresh").status_code == 401


def test_oauth_does_not_silently_link_existing_password_account(client, monkeypatch):
    _oauth_tables()
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    client.post("/auth/register", json={
        "email": "owned@example.com", "password": "StrongPass1234",
    })
    start = client.get("/auth/google", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    async def verified_profile(code, verifier):
        return {"sub": "attacker-google", "email": "owned@example.com", "email_verified": True,
                "name": "Attacker", "picture": None}

    monkeypatch.setattr(oauth_service, "exchange_code", verified_profile)
    response = client.get(f"/auth/google/callback?code=x&state={state}", follow_redirects=False)
    assert response.status_code == 409


def test_oauth_rejects_missing_invalid_expired_state_and_unsafe_return(client, monkeypatch):
    _oauth_tables()
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")
    assert client.get("/auth/google/callback?code=x", follow_redirects=False).status_code == 422
    assert client.get(
        "/auth/google/callback?code=x&state=invalid", follow_redirects=False
    ).status_code == 400

    start = client.get("/auth/google?return_path=https://evil.example/steal", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    db = TestingSessionLocal()
    try:
        row = db.query(OAuthState).one()
        assert row.return_path == "/dashboard"
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        db.close()
    assert client.get(
        f"/auth/google/callback?code=x&state={state}", follow_redirects=False
    ).status_code == 400


def test_oauth_rejects_provider_failure_and_unverified_identity_without_session(client, monkeypatch):
    _oauth_tables()
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_ENABLED", True)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-client")

    start = client.get("/auth/google", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    async def rejected_provider(code, verifier):
        raise oauth_service.OAuthProviderError()

    monkeypatch.setattr(oauth_service, "exchange_code", rejected_provider)
    response = client.get(
        f"/auth/google/callback?code=rejected&state={state}", follow_redirects=False
    )
    assert response.status_code == 400
    assert settings.REFRESH_COOKIE_NAME not in response.cookies

    _oauth_tables()
    start = client.get("/auth/google", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    async def unverified_profile(code, verifier):
        return {"sub": "google-unverified", "email": "unverified@example.com",
                "email_verified": False}

    monkeypatch.setattr(oauth_service, "exchange_code", unverified_profile)
    response = client.get(
        f"/auth/google/callback?code=x&state={state}", follow_redirects=False
    )
    assert response.status_code == 400
    assert settings.REFRESH_COOKIE_NAME not in response.cookies
    db = TestingSessionLocal()
    try:
        assert db.query(User).filter(User.email == "unverified@example.com").first() is None
    finally:
        db.close()
