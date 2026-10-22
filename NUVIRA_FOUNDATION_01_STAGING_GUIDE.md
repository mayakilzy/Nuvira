# NUVIRA FOUNDATION-01 Isolated Staging Guide

## Prerequisites

- Docker Engine with Compose v2
- At least 4 GB available memory and sufficient virtual memory
- Git, curl, Python 3.11+, Node.js 20+
- No production credentials, volumes, networks, URLs, or student data

This staging stack needs no DNS, TLS certificate, Nginx Proxy Manager, or production proxy network.

## Environment preparation

```bash
cp .env.staging.example .env.staging
```

Replace every `CHANGE_ME` value with staging-only random values. Keep all optional providers disabled initially. Then run:

```bash
python scripts/staging/verify_isolation.py --env-file .env.staging
docker compose --env-file .env.staging -f docker-compose.staging.yml config
```

Both must pass before building. Confirm the resolved output contains only `nuvira-foundation-staging_*` resources, `db`/`redis` service hosts, loopback frontend/backend bindings, and no external network.

## Startup

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml build
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d
docker compose --env-file .env.staging -f docker-compose.staging.yml ps
```

The backend applies `alembic upgrade head` before Uvicorn. The worker starts only after backend/database health. Expected local endpoints:

- Frontend: `http://127.0.0.1:3300`
- API: `http://127.0.0.1:8800`

## Health and isolation checks

```bash
curl -fsS http://127.0.0.1:8800/health
curl -fsS http://127.0.0.1:8800/health/db
curl -fsS http://127.0.0.1:3300/
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  psql -U nuvira_staging -d nuvira_staging -c "SELECT version_num FROM alembic_version"
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T worker \
  celery -A app.workers.celery_app inspect ping -d 'foundation-worker@*' --timeout=10
```

Inspect `docker compose ps` and confirm database/Redis have no published host ports. Confirm no container has the production project labels, network, or volumes.

## Backend and PostgreSQL integration

Run unit tests inside backend:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T backend pytest -q
```

Create a disposable test database in the isolated PostgreSQL container:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  createdb -U nuvira_staging nuvira_foundation_test_run
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T \
  -e FOUNDATION_POSTGRES_URL=postgresql+psycopg2://nuvira_staging:STAGING_PASSWORD@db:5432/nuvira_foundation_test_run \
  backend pytest -q tests/integration/test_postgres_foundation.py
```

Use the actual staging-only password without recording it in shell history where possible. The test refuses remote hosts and database names not beginning `nuvira_foundation_test`.

Run Redis/Celery integration:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T \
  -e FOUNDATION_CELERY_BROKER_URL=redis://redis:6379/1 \
  -e FOUNDATION_CELERY_RESULT_BACKEND=redis://redis:6379/2 \
  backend pytest -q tests/integration/test_redis_celery_foundation.py
```

## Security integration workflow

Use only synthetic users and documents.

1. Register two students and grant both the same synthetic subject in the isolated DB.
2. Enable uploads only after configuring a mocked/local embedding path or isolated test credential.
3. Upload a benign synthetic PDF for Student A.
4. Wait for Celery completion and verify ready status.
5. Query as Students A and B; A sees private chunks, B receives none, and authorized platform material remains visible.
6. Interrupt a processing task and verify retry count, safe error code, and absence of partial embeddings.
7. Run concurrent duplicate payment events with mocked provider signatures and confirm one ledger grant.
8. Run register/login/refresh/logout/reset/OAuth-state tests through the HTTP interface and verify Origin rejection.

Do not enable live payments, personal OAuth accounts, email, or production AI credentials.

## Browser E2E

From `frontend`:

```bash
npm install
npx playwright install chromium
FOUNDATION_FRONTEND_URL=http://127.0.0.1:3300 \
FOUNDATION_API_URL=http://127.0.0.1:8800 \
npm run test:e2e
```

The test verifies registration, session restoration, settings with zero subjects, refresh rotation, logout revocation, absence of URL tokens, and absence of requests to the production domain. Missing onboarding/catalog remains an expected product gap, not an infrastructure pass.

For isolated HTTPS cookie/proxy testing, use a local reverse proxy and hosts-file-only names; do not change public DNS or Nginx Proxy Manager.

## Shutdown and cleanup

Preserve staging data by default:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml down
```

Destructive cleanup requires explicit acknowledgement that only disposable staging resources are targeted:

```bash
# Review first:
docker volume ls --filter name=nuvira-foundation-staging
docker network ls --filter name=nuvira-foundation-staging

# Only after confirming the exact project:
docker compose --env-file .env.staging -f docker-compose.staging.yml down --volumes --remove-orphans
```

Never run `down --volumes` against `docker-compose.yml` or the production project.

## Troubleshooting

- Backend exits with revision mismatch: inspect migrations; do not enable `create_all()` or stamp blindly.
- Vector extension permission denied: grant extension creation in this isolated DB or pre-create it as staging DBA.
- Worker unhealthy: compare the worker hostname with `foundation-worker@$HOSTNAME`, then inspect Redis and task registration.
- Frontend calls production: rebuild frontend with the staging `PUBLIC_API_URL`; runtime environment alone cannot replace a compiled `NEXT_PUBLIC_*` value.
- Playwright browser exits before tests: increase host paging/virtual memory or run on a CI runner with supported Chromium resources.

