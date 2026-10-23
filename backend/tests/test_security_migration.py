from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import settings


def test_security_migration_applies_to_existing_schema(tmp_path, monkeypatch):
    database = tmp_path / "upgrade.db"
    url = f"sqlite:///{database.as_posix()}"
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255))"))
        connection.execute(text("CREATE TABLE subject_packages (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE chapters (id INTEGER PRIMARY KEY)"))
        connection.execute(text(
            "CREATE TABLE uploaded_documents (id INTEGER PRIMARY KEY, "
            "uploaded_by_user_id INTEGER, subject_package_id INTEGER, chapter_id INTEGER)"
        ))
        connection.execute(text(
            "CREATE TABLE embeddings (id INTEGER PRIMARY KEY, subject_package_id INTEGER, "
            "user_id INTEGER, chapter_id INTEGER, document_id INTEGER)"
        ))
    monkeypatch.setattr(settings, "DATABASE_URL", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    command.stamp(config, "0001_lowercase_emails")
    # This synthetic schema intentionally contains only the SECURITY-01 tables,
    # so exercise the security revision directly rather than later feature migrations.
    command.upgrade(config, "0002_security_controls")
    tables = set(inspect(engine).get_table_names())
    assert {"refresh_sessions", "oauth_states", "oauth_exchanges", "credit_packs",
            "payment_events", "account_deletion_requests"}.issubset(tables)
    columns = {column["name"] for column in inspect(engine).get_columns("uploaded_documents")}
    assert {"error_code", "file_size", "processing_attempts"}.issubset(columns)
