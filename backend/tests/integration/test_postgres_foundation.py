"""PostgreSQL/pgvector gates. Set FOUNDATION_POSTGRES_URL to run them."""

import os
import subprocess
import sys
import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.commerce import CreditPack
from app.models.credits import CreditLedger
from app.models.embedding import Embedding
from app.models.subject import SubjectPackage
from app.models.user import User
from app.services import vector_service
from app.services.schema_service import require_expected_revision
from app.services.payments.base import WebhookEvent, fulfill
from app.services.payments.lemonsqueezy_provider import LemonSqueezyProvider
from scripts.adopt_legacy_schema import BASELINE_REVISION, assess

URL = os.getenv("FOUNDATION_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="FOUNDATION_POSTGRES_URL is not configured")


def _assert_isolated_test_database() -> None:
    parsed = urlparse(URL)
    if parsed.hostname not in {"127.0.0.1", "localhost", "db"}:
        pytest.fail("FOUNDATION_POSTGRES_URL must target localhost or the isolated db service")
    if not (parsed.path or "").lstrip("/").startswith("nuvira_foundation_test"):
        pytest.fail("database name must start with nuvira_foundation_test")


@pytest.fixture(scope="module")
def postgres_engine():
    _assert_isolated_test_database()
    original_url = settings.DATABASE_URL
    settings.DATABASE_URL = URL
    engine = create_engine(URL, pool_pre_ping=True)
    if set(inspect(engine).get_table_names()) - {"alembic_version"}:
        pytest.fail("FOUNDATION_POSTGRES_URL must point to an empty disposable database")
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()
    settings.DATABASE_URL = original_url


def test_postgres_migration_pgvector_and_constraints(postgres_engine):
    inspector = inspect(postgres_engine)
    assert {"users", "embeddings", "refresh_sessions", "payment_events"}.issubset(inspector.get_table_names())
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).scalar_one() == "vector"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_security_controls"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    command.upgrade(config, "head")
    command.check(config)
    require_expected_revision(postgres_engine)


def test_postgres_cross_student_vector_visibility(postgres_engine):
    Session = sessionmaker(bind=postgres_engine)
    db = Session()
    try:
        a = User(email="foundation-a@example.invalid", is_active=True)
        b = User(email="foundation-b@example.invalid", is_active=True)
        subject = SubjectPackage(name="Synthetic", language="en")
        db.add_all([a, b, subject]); db.flush()
        vector = [0.1] * 1536
        db.add_all([
            Embedding(user_id=None, subject_package_id=subject.id, content="platform", embedding=vector, meta={}),
            Embedding(user_id=a.id, subject_package_id=subject.id, content="student-a", embedding=vector, meta={}),
            Embedding(user_id=b.id, subject_package_id=subject.id, content="student-b", embedding=vector, meta={}),
        ])
        db.commit()
        visible = {row.content for row in vector_service.visible_scope_query(db, b.id, subject.id).all()}
        assert visible == {"platform", "student-b"}
    finally:
        db.rollback()
        db.close()


def test_postgres_concurrent_duplicate_payment_event_grants_once(postgres_engine):
    Session = sessionmaker(bind=postgres_engine)
    setup = Session()
    user = User(email="foundation-payments@example.invalid", is_active=True)
    setup.add(user); setup.flush()
    setup.add(CreditPack(
        slug="foundation-pack", provider="stripe", provider_price_id="price_foundation",
        credits=100, is_active=True,
    ))
    setup.commit()
    user_id = user.id
    setup.close()

    def deliver() -> None:
        db = Session()
        try:
            fulfill(db, WebhookEvent(
                type="credits_purchased", user_id=user_id, provider="stripe",
                pack_slug="foundation-pack", credits=999999,
                reference_id="evt_foundation_concurrent",
            ))
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: deliver(), range(2)))
    verify = Session()
    try:
        rows = verify.query(CreditLedger).filter(
            CreditLedger.user_id == user_id,
            CreditLedger.reference_id == "evt_foundation_concurrent",
        ).all()
        assert len(rows) == 1 and rows[0].amount == 100
    finally:
        verify.close()


def test_signed_failed_payment_fixture_grants_nothing(postgres_engine, monkeypatch):
    Session = sessionmaker(bind=postgres_engine)
    db = Session()
    user = User(email="foundation-failed-payment@example.invalid", is_active=True)
    db.add(user)
    db.commit()
    user_id = user.id
    secret = "synthetic-staging-webhook-secret"
    monkeypatch.setattr(settings, "LEMONSQUEEZY_WEBHOOK_SECRET", secret)
    payload = json.dumps({
        "meta": {
            "event_name": "order_refunded",
            "custom_data": {"user_id": str(user_id), "pack_slug": "foundation-pack"},
        },
        "data": {"id": "evt_foundation_refunded", "attributes": {}},
    }).encode()
    provider = LemonSqueezyProvider()
    with pytest.raises(ValueError, match="Invalid Lemon Squeezy signature"):
        provider.verify_and_parse(payload, {"x-signature": "invalid"})
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    event = provider.verify_and_parse(payload, {"x-signature": signature})
    assert event.type == "ignored"
    fulfill(db, event)
    assert db.query(CreditLedger).filter(CreditLedger.user_id == user_id).count() == 0
    db.close()


def _replace_database(database_name: str):
    assert database_name.startswith("nuvira_foundation_test_")
    base = make_url(URL)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    quoted = '"' + database_name.replace('"', '""') + '"'
    with admin.connect() as connection:
        connection.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=:name AND pid <> pg_backend_pid()"
        ), {"name": database_name})
        connection.execute(text(f"DROP DATABASE IF EXISTS {quoted}"))
        connection.execute(text(f"CREATE DATABASE {quoted}"))
    admin.dispose()
    return base.set(database=database_name).render_as_string(hide_password=False)


def _drop_database(database_name: str) -> None:
    assert database_name.startswith("nuvira_foundation_test_")
    base = make_url(URL)
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    quoted = '"' + database_name.replace('"', '""') + '"'
    with admin.connect() as connection:
        connection.execute(text(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=:name AND pid <> pg_backend_pid()"
        ), {"name": database_name})
        connection.execute(text(f"DROP DATABASE IF EXISTS {quoted}"))
    admin.dispose()


def test_postgres_legacy_adoption_and_incompatible_rejection(monkeypatch):
    backend_dir = Path(__file__).parents[2]
    legacy_name = "nuvira_foundation_test_legacy"
    incompatible_name = "nuvira_foundation_test_incompatible"
    legacy_url = _replace_database(legacy_name)
    incompatible_url = _replace_database(incompatible_name)
    try:
        monkeypatch.setattr(settings, "DATABASE_URL", legacy_url)
        config = Config(str(backend_dir / "alembic.ini"))
        config.set_main_option("script_location", str(backend_dir / "alembic"))
        command.upgrade(config, BASELINE_REVISION)
        engine = create_engine(legacy_url)
        with pytest.raises(RuntimeError, match="revision mismatch"):
            require_expected_revision(engine)
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id,email,password_hash,role,is_active,is_verified,created_at,updated_at) "
                "VALUES (1,'Student@Example.com','hash','user',TRUE,TRUE,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO subject_packages (id,name,language,review_status,created_at) "
                "VALUES (1,'Synthetic Chemistry','en','self_reviewed',CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO chapters (id,subject_package_id,chapter_number,title,created_at) "
                "VALUES (1,1,1,'Synthetic Chapter',CURRENT_TIMESTAMP)"
            ))
            connection.execute(text(
                "INSERT INTO concepts (id,subject_package_id,name,difficulty,created_at) "
                "VALUES (1,1,'Synthetic Concept',1,CURRENT_TIMESTAMP)"
            ))
            connection.execute(text("DROP TABLE alembic_version"))
        assessment = assess(engine)
        assert assessment.safe_to_stamp and assessment.stamp_target == BASELINE_REVISION

        environment = os.environ.copy()
        environment["DATABASE_URL"] = legacy_url
        refused = subprocess.run(
            [sys.executable, "scripts/adopt_legacy_schema.py", "--apply-stamp"],
            cwd=backend_dir, env=environment, capture_output=True, text=True, check=False,
        )
        assert refused.returncode == 3
        assert "--acknowledge-backup is required" in refused.stderr
        adopted = subprocess.run(
            [
                sys.executable, "scripts/adopt_legacy_schema.py", "--apply-stamp",
                "--acknowledge-backup",
            ],
            cwd=backend_dir, env=environment, capture_output=True, text=True, check=False,
        )
        assert adopted.returncode == 0, adopted.stdout + adopted.stderr
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        command.check(config)
        with engine.connect() as connection:
            assert connection.execute(text("SELECT email FROM users WHERE id=1")).scalar_one() == "student@example.com"
            assert connection.execute(text("SELECT title FROM chapters WHERE id=1")).scalar_one() == "Synthetic Chapter"
            assert connection.execute(text("SELECT name FROM concepts WHERE id=1")).scalar_one() == "Synthetic Concept"
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_security_controls"
        engine.dispose()

        monkeypatch.setattr(settings, "DATABASE_URL", incompatible_url)
        bad_config = Config(str(backend_dir / "alembic.ini"))
        bad_config.set_main_option("script_location", str(backend_dir / "alembic"))
        command.upgrade(bad_config, BASELINE_REVISION)
        bad_engine = create_engine(incompatible_url)
        with bad_engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN unreviewed_data TEXT"))
            connection.execute(text("DROP TABLE alembic_version"))
        rejected = assess(bad_engine)
        assert rejected.state == "incompatible"
        assert not rejected.safe_to_stamp
        assert any("unreviewed_data" in error for error in rejected.errors)
        bad_engine.dispose()
    finally:
        monkeypatch.setattr(settings, "DATABASE_URL", URL)
        _drop_database(legacy_name)
        _drop_database(incompatible_name)
