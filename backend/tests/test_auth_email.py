"""
Fix 1 — case-insensitive email handling.

Regression test: registering 'Sweet@x.com' then logging in with 'sweet@x.com'
must succeed, the stored email must be normalized to lowercase, and a second
registration that differs only by case must be rejected as a duplicate.
"""
from app.models.user import User
from tests.conftest import TestingSessionLocal


def test_register_mixed_case_then_login_lowercase(client):
    r = client.post("/auth/register", json={
        "email": "Sweet@x.com", "password": "S3cure!pass123", "full_name": "Sweet Tester",
    })
    assert r.status_code == 201, r.text
    assert "access_token" in r.json()

    r2 = client.post("/auth/login", json={
        "email": "sweet@x.com", "password": "S3cure!pass123",
    })
    assert r2.status_code == 200, r2.text
    body = r2.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert "refresh_token" not in body
    assert client.cookies.get("nuvira_refresh")


def test_stored_email_is_normalized_to_lowercase(client):
    client.post("/auth/register", json={
        "email": "  Sweet@X.COM ", "password": "S3cure!pass123",
    })
    db = TestingSessionLocal()
    try:
        rows = db.query(User).all()
        assert len(rows) == 1
        assert rows[0].email == "sweet@x.com"
    finally:
        db.close()


def test_duplicate_registration_case_variant_rejected(client):
    client.post("/auth/register", json={
        "email": "sweet@x.com", "password": "S3cure!pass123",
    })
    r = client.post("/auth/register", json={
        "email": "SWEET@x.com", "password": "Another!pass456",
    })
    assert r.status_code == 409


def test_login_with_wrong_password_still_fails(client):
    client.post("/auth/register", json={
        "email": "sweet@x.com", "password": "S3cure!pass123",
    })
    r = client.post("/auth/login", json={
        "email": "SWEET@x.com", "password": "wrong-password",
    })
    assert r.status_code == 401
