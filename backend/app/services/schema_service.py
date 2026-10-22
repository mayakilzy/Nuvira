"""Fail-closed database revision checks for managed environments."""

from sqlalchemy import Engine, inspect, text

EXPECTED_ALEMBIC_REVISION = "0002_security_controls"


def require_expected_revision(engine: Engine) -> None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        raise RuntimeError("Database is not managed by Alembic")
    with engine.connect() as connection:
        revisions = {row[0] for row in connection.execute(text("SELECT version_num FROM alembic_version"))}
    if revisions != {EXPECTED_ALEMBIC_REVISION}:
        found = ", ".join(sorted(revisions)) or "none"
        raise RuntimeError(
            f"Database revision mismatch: expected {EXPECTED_ALEMBIC_REVISION}, found {found}"
        )
