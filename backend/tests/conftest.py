"""
Shared test fixtures.

Uses an in-memory SQLite database (only tables that don't need pgvector),
so unit tests never touch Postgres. External calls (email/Resend) are mocked.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-which-is-longer-than-sixty-four-characters-000001")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models.user import User
from app.models.security import RefreshSession
from app.services import email_service
from app.core import ratelimit

# One shared in-memory DB for the whole test session (StaticPool keeps the
# connection alive). Only the users table is created here — auth tests don't
# need pgvector tables.
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    """FastAPI test client with a clean users table per test."""
    User.__table__.drop(engine, checkfirst=True)
    User.__table__.create(engine)
    RefreshSession.__table__.drop(engine, checkfirst=True)
    RefreshSession.__table__.create(engine)
    ratelimit._hits.clear()
    ratelimit._auth_hits.clear()
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_external_email(monkeypatch):
    """Never call Resend from tests; record what would have been sent."""
    sent = []

    async def fake_send(to, token_or_url=None, *args, **kwargs):
        sent.append(to)
        return True

    monkeypatch.setattr(email_service, "send_verification_email",
                        lambda to, token: fake_send(to, token))
    monkeypatch.setattr(email_service, "send_reset_email",
                        lambda to, token: fake_send(to, token))
    return sent
