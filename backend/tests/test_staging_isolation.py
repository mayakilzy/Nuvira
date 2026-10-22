import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "verify_isolation", ROOT / "scripts" / "staging" / "verify_isolation.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
verify = MODULE.verify


def test_staging_configuration_is_isolated_after_placeholders_are_replaced(tmp_path):
    root = ROOT
    template = (root / ".env.staging.example").read_text(encoding="utf-8")
    env = template.replace(
        "CHANGE_ME_STAGING_DATABASE_PASSWORD", "synthetic-staging-database-password"
    ).replace(
        "CHANGE_ME_WITH_A_STAGING_ONLY_RANDOM_VALUE_OF_AT_LEAST_64_CHARACTERS",
        "synthetic-staging-jwt-secret-000000000000000000000000000000000000000000000000",
    ).replace(
        "CHANGE_ME_STAGING_ADMIN_PASSWORD", "synthetic-admin-password-not-enabled"
    )
    env_path = tmp_path / ".env.staging"
    env_path.write_text(env, encoding="utf-8")
    assert verify(root, env_path) == []


def test_staging_preflight_rejects_production_identifiers_and_placeholders(tmp_path):
    root = ROOT
    env_path = tmp_path / ".env.staging"
    env_path.write_text(
        "COMPOSE_PROJECT_NAME=nuvira-foundation-staging\n"
        "ENV=staging\nDEBUG=false\n"
        "FRONTEND_URL=https://nuvira.agentcraft.info\n"
        "DATABASE_URL=postgresql://user:CHANGE_ME@db:5432/nuvira_staging\n"
        "POSTGRES_DB=nuvira_staging\n"
        "REDIS_URL=redis://redis:6379/0\n"
        "CELERY_BROKER_URL=redis://redis:6379/1\n"
        "CELERY_RESULT_BACKEND=redis://redis:6379/2\n",
        encoding="utf-8",
    )
    errors = verify(root, env_path)
    assert any("production identifier" in error for error in errors)
    assert any("CHANGE_ME" in error for error in errors)
