from pathlib import Path
import os
import subprocess
import sys

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import settings
from app.services.schema_service import EXPECTED_ALEMBIC_REVISION, require_expected_revision
from scripts.adopt_legacy_schema import BASELINE_REVISION, assess


def _config(database_url: str, monkeypatch) -> Config:
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    backend = Path(__file__).parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    return config


def _url(tmp_path, name: str) -> str:
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def test_fresh_database_upgrades_to_head_without_schema_drift(tmp_path, monkeypatch):
    url = _url(tmp_path, "fresh.db")
    config = _config(url, monkeypatch)
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "users", "subject_packages", "chapters", "concepts", "embeddings",
        "refresh_sessions", "oauth_states", "oauth_exchanges", "credit_packs",
        "payment_events", "account_deletion_requests", "alembic_version",
    }.issubset(tables)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == EXPECTED_ALEMBIC_REVISION
    require_expected_revision(engine)


def test_populated_legacy_schema_can_be_adopted_without_data_loss(tmp_path, monkeypatch):
    url = _url(tmp_path, "legacy.db")
    config = _config(url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO users (id,email,password_hash,role,is_active,is_verified,created_at,updated_at) "
            "VALUES (1,'Student@Example.com','hash','user',1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
        ))
        connection.execute(text(
            "INSERT INTO subject_packages (id,name,language,review_status,created_at) "
            "VALUES (1,'Synthetic Math','en','self_reviewed',CURRENT_TIMESTAMP)"
        ))
        connection.execute(text(
            "INSERT INTO chapters (id,subject_package_id,chapter_number,title,created_at) "
            "VALUES (1,1,1,'Synthetic Chapter',CURRENT_TIMESTAMP)"
        ))
        connection.execute(text(
            "INSERT INTO concepts (id,subject_package_id,name,difficulty,created_at) "
            "VALUES (1,1,'Synthetic Concept',1,CURRENT_TIMESTAMP)"
        ))
        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(text("DROP TABLE alembic_version"))

    result = assess(engine)
    assert result.safe_to_stamp and result.stamp_target == BASELINE_REVISION
    command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT email FROM users WHERE id=1")).scalar_one() == "student@example.com"
        assert connection.execute(text("SELECT title FROM chapters WHERE id=1")).scalar_one() == "Synthetic Chapter"
        assert connection.execute(text("SELECT name FROM concepts WHERE id=1")).scalar_one() == "Synthetic Concept"


def test_adoption_rejects_unexpected_schema(tmp_path, monkeypatch):
    url = _url(tmp_path, "unexpected.db")
    config = _config(url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE users ADD COLUMN unreviewed_data TEXT"))
        connection.execute(text("DROP TABLE alembic_version"))
    result = assess(engine)
    assert result.state == "incompatible"
    assert not result.safe_to_stamp
    assert any("unreviewed_data" in error for error in result.errors)


def test_email_collision_interrupts_then_recovers_without_partial_upgrade(tmp_path, monkeypatch):
    url = _url(tmp_path, "collision.db")
    config = _config(url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    engine = create_engine(url)
    with engine.begin() as connection:
        for user_id, email in ((1, "Student@Example.com"), (2, "student@example.com")):
            connection.execute(text(
                "INSERT INTO users (id,email,password_hash,role,is_active,is_verified,created_at,updated_at) "
                "VALUES (:id,:email,'hash','user',1,1,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            ), {"id": user_id, "email": email})
    with pytest.raises(RuntimeError, match="case-insensitive duplicate"):
        command.upgrade(config, "head")
    with engine.begin() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == BASELINE_REVISION
        connection.execute(text("UPDATE users SET email='student-2@example.com' WHERE id=2"))
    command.upgrade(config, "head")
    require_expected_revision(engine)


def test_schema_guard_rejects_missing_or_old_revision(tmp_path, monkeypatch):
    fresh_url = _url(tmp_path, "unmanaged.db")
    unmanaged = create_engine(fresh_url)
    with unmanaged.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
    with pytest.raises(RuntimeError, match="not managed"):
        require_expected_revision(unmanaged)

    old_url = _url(tmp_path, "old.db")
    config = _config(old_url, monkeypatch)
    command.upgrade(config, BASELINE_REVISION)
    with pytest.raises(RuntimeError, match="revision mismatch"):
        require_expected_revision(create_engine(old_url))


def test_adoption_cli_runs_read_only_from_the_documented_path(tmp_path):
    env = os.environ.copy()
    env["DATABASE_URL"] = _url(tmp_path, "cli-fresh.db")
    result = subprocess.run(
        [sys.executable, "scripts/adopt_legacy_schema.py"],
        cwd=Path(__file__).parents[1], env=env, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert "state=fresh" in result.stdout
