"""Validate and adopt a legacy Nuvira database into Alembic history.

Read-only by default. A stamp is permitted only after exact structural parity
and an explicit backup acknowledgement. This tool never creates, alters, or
drops application data.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings
from app.database import Base
import app.models  # noqa: F401

BASELINE_REVISION = "0000_authoritative_schema"
SECURITY_REVISION = "0002_security_controls"
HEAD_REVISION = "0003_curriculum_library"
SECURITY_TABLES = {
    "refresh_sessions", "oauth_states", "oauth_exchanges", "credit_packs",
    "payment_events", "account_deletion_requests",
}
SECURITY_UPLOAD_COLUMNS = {"error_code", "file_size", "processing_attempts"}
SYSTEM_TABLES = {"alembic_version", "sqlite_sequence"}
CURRICULUM_TABLES = {
    "educational_systems", "curricula", "curriculum_versions", "learning_resources",
    "curriculum_units", "lessons", "user_lesson_progress",
}
CURRICULUM_COLUMNS = {
    "subject_packages": {"curriculum_version_id", "code", "description", "order_index", "publication_status"},
    "chapters": {"learning_resource_id", "unit_id"},
    "concepts": {"chapter_id", "lesson_id", "order_index"},
    "user_subject_access": {"is_active"},
}


@dataclass
class Assessment:
    state: str
    stamp_target: str | None = None
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def safe_to_stamp(self) -> bool:
        return self.state == "legacy-compatible" and not self.errors and self.stamp_target is not None


def _type_family(value) -> str:
    name = value.__class__.__name__.lower()
    aliases = {
        "varchar": "string", "string": "string", "text": "text",
        "integer": "integer", "bigint": "integer", "boolean": "boolean",
        "datetime": "datetime", "timestamp": "datetime", "json": "json",
        "jsonb": "json", "float": "float", "double_precision": "float",
        "vector": "vector",
    }
    return aliases.get(name, name)


def _signature(
    column: dict, *, primary_key: bool | None = None,
) -> tuple[str, bool, bool, int | None]:
    type_name = _type_family(column["type"])
    length = getattr(column["type"], "length", None)
    if primary_key is None:
        primary_key = bool(column.get("primary_key"))
    return type_name, bool(column["nullable"]), primary_key, length


def _expected_tables(profile: str) -> set[str]:
    tables = set(Base.metadata.tables)
    if profile in {"baseline", "security"}:
        tables -= CURRICULUM_TABLES
    if profile == "baseline":
        tables -= SECURITY_TABLES
    return tables


def _expected_columns(
    table_name: str, profile: str, dialect_name: str,
) -> dict[str, tuple[str, bool, bool, int | None]]:
    columns = {
        column.name: (
            _type_family(column.type), bool(column.nullable),
            bool(column.primary_key), getattr(column.type, "length", None),
        )
        for column in Base.metadata.tables[table_name].columns
    }
    if profile == "baseline" and table_name == "uploaded_documents":
        for name in SECURITY_UPLOAD_COLUMNS:
            columns.pop(name, None)
    if profile in {"baseline", "security"}:
        for name in CURRICULUM_COLUMNS.get(table_name, set()):
            columns.pop(name, None)
    if dialect_name == "sqlite" and table_name == "embeddings":
        signature = columns["embedding"]
        columns["embedding"] = ("json", *signature[1:])
    return columns


def _expected_foreign_keys(table_name: str, profile: str) -> set[tuple[tuple[str, ...], str, tuple[str, ...], str | None]]:
    table = Base.metadata.tables[table_name]
    allowed_columns = set(_expected_columns(table_name, profile, "postgresql"))
    return {
        (
            tuple(element.parent.name for element in constraint.elements),
            constraint.referred_table.name,
            tuple(element.column.name for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.foreign_key_constraints
        if all(element.parent.name in allowed_columns for element in constraint.elements)
    }


def _actual_foreign_keys(inspector, table_name: str) -> set[tuple[tuple[str, ...], str, tuple[str, ...], str | None]]:
    return {
        (
            tuple(item["constrained_columns"]), item["referred_table"],
            tuple(item["referred_columns"]), (item.get("options") or {}).get("ondelete"),
        )
        for item in inspector.get_foreign_keys(table_name)
    }


def _required_indexes(table_name: str, profile: str) -> dict[str, tuple[tuple[str, ...], bool]]:
    allowed_columns = set(_expected_columns(table_name, profile, "postgresql"))
    result = {
        index.name: (tuple(column.name for column in index.columns), bool(index.unique))
        for index in Base.metadata.tables[table_name].indexes
        if all(column.name in allowed_columns for column in index.columns)
    }
    if profile == "baseline" and table_name == "embeddings":
        result.pop("ix_embeddings_subject_owner_chapter_document", None)
    return result


def _actual_indexes(inspector, table_name: str) -> dict[str, tuple[tuple[str, ...], bool]]:
    return {
        item["name"]: (tuple(item["column_names"]), bool(item["unique"]))
        for item in inspector.get_indexes(table_name)
        if item.get("name")
    }


def _expected_unique_constraints(table_name: str, profile: str) -> set[tuple[str, ...]]:
    allowed_columns = set(_expected_columns(table_name, profile, "postgresql"))
    result = {
        tuple(column.name for column in constraint.columns)
        for constraint in Base.metadata.tables[table_name].constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
        and all(column.name in allowed_columns for column in constraint.columns)
    }
    if profile in {"baseline", "security"} and table_name == "user_subject_access":
        result.discard(("user_id", "subject_package_id"))
    return result


def _actual_unique_constraints(inspector, table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints(table_name)
    }


def _compare_profile(engine: Engine, profile: str) -> list[str]:
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names()) - SYSTEM_TABLES
    expected_tables = _expected_tables(profile)
    errors: list[str] = []
    if missing := sorted(expected_tables - actual_tables):
        errors.append("missing tables: " + ", ".join(missing))
    if unexpected := sorted(actual_tables - expected_tables):
        errors.append("unexpected tables: " + ", ".join(unexpected))
    for table_name in sorted(expected_tables & actual_tables):
        primary_key_columns = set(
            (inspector.get_pk_constraint(table_name) or {}).get("constrained_columns") or []
        )
        actual_columns = {
            column["name"]: _signature(
                column, primary_key=column["name"] in primary_key_columns,
            )
            for column in inspector.get_columns(table_name)
        }
        expected_columns = _expected_columns(table_name, profile, engine.dialect.name)
        if set(actual_columns) != set(expected_columns):
            errors.append(
                f"{table_name}: column set differs; missing={sorted(set(expected_columns)-set(actual_columns))}, "
                f"unexpected={sorted(set(actual_columns)-set(expected_columns))}"
            )
            continue
        for column_name, expected in expected_columns.items():
            actual = actual_columns[column_name]
            if actual != expected:
                errors.append(f"{table_name}.{column_name}: expected {expected}, found {actual}")
        expected_fks = _expected_foreign_keys(table_name, profile)
        actual_fks = _actual_foreign_keys(inspector, table_name)
        if actual_fks != expected_fks:
            errors.append(f"{table_name}: foreign keys differ")
        expected_indexes = _required_indexes(table_name, profile)
        actual_indexes = _actual_indexes(inspector, table_name)
        for name, signature in expected_indexes.items():
            if actual_indexes.get(name) != signature:
                errors.append(f"{table_name}: required index {name} differs or is missing")
        if _actual_unique_constraints(inspector, table_name) != _expected_unique_constraints(table_name, profile):
            errors.append(f"{table_name}: unique constraints differ")
    if engine.dialect.name == "postgresql":
        with engine.connect() as connection:
            vector_enabled = bool(connection.execute(text(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )).scalar())
        if not vector_enabled:
            errors.append("PostgreSQL extension 'vector' is not installed")
    return errors


def _emails_are_normalized(engine: Engine) -> bool:
    with engine.connect() as connection:
        duplicate = connection.execute(text(
            "SELECT 1 FROM users GROUP BY LOWER(TRIM(email)) HAVING COUNT(*) > 1 LIMIT 1"
        )).first()
        noncanonical = connection.execute(text(
            "SELECT 1 FROM users WHERE email <> LOWER(TRIM(email)) LIMIT 1"
        )).first()
    return duplicate is None and noncanonical is None


def assess(engine: Engine) -> Assessment:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    app_tables = tables - SYSTEM_TABLES
    if not app_tables:
        return Assessment("fresh", notes=["Run alembic upgrade head; do not stamp a fresh database."])
    if "alembic_version" in tables:
        with engine.connect() as connection:
            revisions = [row[0] for row in connection.execute(text("SELECT version_num FROM alembic_version"))]
        return Assessment("versioned", notes=["Current revision(s): " + ", ".join(revisions or ["none"])])

    baseline_errors = _compare_profile(engine, "baseline")
    if not baseline_errors:
        return Assessment(
            "legacy-compatible", stamp_target=BASELINE_REVISION,
            notes=["Schema matches the historical pre-SECURITY-01 baseline."],
        )
    security_errors = _compare_profile(engine, "security")
    if not security_errors and _emails_are_normalized(engine):
        return Assessment(
            "legacy-compatible", stamp_target=SECURITY_REVISION,
            notes=["Schema matches SECURITY-01 head and emails are canonical."],
        )
    if not security_errors:
        security_errors.append("users.email contains duplicates or non-canonical casing")
    head_errors = _compare_profile(engine, "head")
    if not head_errors and _emails_are_normalized(engine):
        return Assessment(
            "legacy-compatible", stamp_target=HEAD_REVISION,
            notes=["Schema matches CURRICULUM-01 head and emails are canonical."],
        )
    return Assessment(
        "incompatible", errors=[
            "baseline profile: " + "; ".join(baseline_errors),
            "security profile: " + "; ".join(security_errors),
            "head profile: " + "; ".join(head_errors),
        ],
    )


def _alembic_config() -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply-stamp", action="store_true", help="Stamp only after parity succeeds")
    parser.add_argument(
        "--acknowledge-backup", action="store_true",
        help="Confirm a verified database and uploads backup exists",
    )
    args = parser.parse_args()
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
    result = assess(engine)
    print(f"state={result.state}")
    for note in result.notes:
        print(f"note={note}")
    for error in result.errors:
        print(f"error={error}")
    if not args.apply_stamp:
        if result.safe_to_stamp:
            print(f"safe_stamp_target={result.stamp_target}")
        return 0 if result.state != "incompatible" else 2
    if not args.acknowledge_backup:
        print("error=--acknowledge-backup is required before stamping", file=sys.stderr)
        return 3
    if not result.safe_to_stamp:
        print("error=schema is not eligible for stamping", file=sys.stderr)
        return 4
    command.stamp(_alembic_config(), result.stamp_target)
    print(f"stamped={result.stamp_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
