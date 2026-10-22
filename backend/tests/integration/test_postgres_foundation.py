"""PostgreSQL/pgvector gates. Set FOUNDATION_POSTGRES_URL to run them."""

import os
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.commerce import CreditPack
from app.models.credits import CreditLedger
from app.models.embedding import Embedding
from app.models.subject import SubjectPackage
from app.models.user import User
from app.services import vector_service
from app.services.payments.base import WebhookEvent, fulfill

URL = os.getenv("FOUNDATION_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="FOUNDATION_POSTGRES_URL is not configured")


def _assert_isolated_test_database() -> None:
    parsed = urlparse(URL)
    if parsed.hostname not in {"127.0.0.1", "localhost", "db"}:
        pytest.fail("FOUNDATION_POSTGRES_URL must target localhost or the isolated db service")
    if not (parsed.path or "").lstrip("/").startswith("nuvira_foundation_test"):
        pytest.fail("database name must start with nuvira_foundation_test")


@pytest.fixture(scope="module")
def postgres_engine(monkeypatch):
    _assert_isolated_test_database()
    monkeypatch.setattr(settings, "DATABASE_URL", URL)
    engine = create_engine(URL, pool_pre_ping=True)
    if set(inspect(engine).get_table_names()) - {"alembic_version"}:
        pytest.fail("FOUNDATION_POSTGRES_URL must point to an empty disposable database")
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


def test_postgres_migration_pgvector_and_constraints(postgres_engine):
    inspector = inspect(postgres_engine)
    assert {"users", "embeddings", "refresh_sessions", "payment_events"}.issubset(inspector.get_table_names())
    with postgres_engine.connect() as connection:
        assert connection.execute(text("SELECT extname FROM pg_extension WHERE extname='vector'")).scalar_one() == "vector"
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0002_security_controls"


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
