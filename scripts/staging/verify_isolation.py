"""Static preflight for the isolated FOUNDATION-01 staging environment."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import urlparse


FORBIDDEN = (
    "nuvira.agentcraft.info", "api.nuvira.agentcraft.info", "hermes-network",
    "nuvira_postgres_data", "nuvira_redis_data", "nuvira_uploads", "/root/apps/nuvira",
)

REQUIRED_DISABLED_FLAGS = (
    "GOOGLE_OAUTH_ENABLED", "PAYMENTS_ENABLED", "AI_ENABLED", "EMAIL_ENABLED",
    "FIRST_ADMIN_ENABLED", "UPLOADS_ENABLED",
)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def verify(root: Path, env_path: Path) -> list[str]:
    errors: list[str] = []
    compose = (root / "docker-compose.staging.yml").read_text(encoding="utf-8")
    env_text = env_path.read_text(encoding="utf-8")
    env = read_env(env_path)
    combined = compose + "\n" + env_text
    for forbidden in FORBIDDEN:
        if forbidden.lower() in combined.lower():
            errors.append(f"forbidden production identifier found: {forbidden}")
    if env.get("COMPOSE_PROJECT_NAME") != "nuvira-foundation-staging":
        errors.append("COMPOSE_PROJECT_NAME must be nuvira-foundation-staging")
    if env.get("ENV") != "staging" or env.get("DEBUG", "").lower() != "false":
        errors.append("ENV must be staging and DEBUG must be false")
    if any("CHANGE_ME" in value for value in env.values()):
        errors.append("replace every CHANGE_ME placeholder before startup")
    for key in REQUIRED_DISABLED_FLAGS:
        if env.get(key, "").lower() != "false":
            errors.append(f"{key} must default to false before runtime verification")
    database = urlparse(env.get("DATABASE_URL", ""))
    if database.hostname != "db" or env.get("POSTGRES_DB") != "nuvira_staging":
        errors.append("DATABASE_URL must target the isolated db service and staging database")
    for key in ("REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"):
        if urlparse(env.get(key, "")).hostname != "redis":
            errors.append(f"{key} must target the isolated redis service")
    if "127.0.0.1:${STAGING_FRONTEND_PORT" not in compose or "127.0.0.1:${STAGING_BACKEND_PORT" not in compose:
        errors.append("frontend/backend ports must bind to loopback only")
    if env.get("PUBLIC_API_URL") != "http://127.0.0.1:8800":
        errors.append("PUBLIC_API_URL must target the loopback staging backend")
    if compose.count("mem_limit:") != 5 or compose.count("cpus:") != 5:
        errors.append("all five staging services must define CPU and memory limits")
    if compose.count("com.nuvira.environment: staging") != 5:
        errors.append("all five staging services must carry the staging label")
    if "localdev/nuvira-foundation-" in compose or "${STAGING_TAG:-security-01}" in compose:
        errors.append("application images must use staging-specific names and tags")
    db_block = compose.split("  db:", 1)[1].split("  redis:", 1)[0]
    redis_block = compose.split("  redis:", 1)[1].split("  backend:", 1)[0]
    if "ports:" in db_block or "ports:" in redis_block:
        errors.append("PostgreSQL and Redis must not publish host ports")
    if "external: true" in compose or "nuvira_internal" in compose:
        errors.append("staging compose must not attach to external or production networks")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.staging")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    env_path = (root / args.env_file).resolve()
    if not env_path.is_file():
        print(f"FAIL: environment file not found: {env_path}")
        return 2
    errors = verify(root, env_path)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: staging identifiers, service hosts, ports, networks and placeholders are isolated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
