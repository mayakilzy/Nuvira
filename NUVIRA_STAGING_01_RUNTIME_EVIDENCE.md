# NUVIRA STAGING-01 Runtime Evidence

## Evidence chain

| Item | Value |
|---|---|
| Workflow | `.github/workflows/staging-verification.yml` |
| Final run | `https://github.com/mayakilzy/Nuvira/actions/runs/39874587953` |
| Tested SHA | `b4734bf59db45dcaab85ca993fe10b0bda4ec90d` |
| Job | `isolated-staging` |
| Artifact | `nuvira-staging-01-evidence-39874587953` |
| Artifact ID | `12468385525` |
| Artifact SHA-256 | `5891fb74d25e7e12e9c57fa68819c930287ef2c8d85756b2529d2dda4068c25f` |
| Expiry | `2026-11-05T23:56:44Z` |

The GitHub artifact digest matched the locally downloaded archive SHA-256. The uploaded archive excludes the ephemeral `.env.staging`, database dump, upload archive, browser cookies, credentials, and secret values.

## Host and component versions

`environment.txt` records Docker 28.0.4, Compose 2.38.2, host Node.js 22.23.3, npm 10.9.9, and host Python 3.12.3. `runtime-versions.txt` records the exact container components:

```text
postgres (PostgreSQL) 16.15 (Debian 16.15-1.pgdg12+2)
server=PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2), x86_64, 64-bit
pgvector=0.8.7
Redis server v=7.4.11 malloc=jemalloc-5.3.0 bits=64
python=3.12.15
celery=5.4.0
pgvector-python=0.3.6
node=v20.20.2
next=16.3.8
```

The frontend image build log separately records Next.js 16.3.8. Playwright came from the locked frontend dependency tree (`@playwright/test` 1.64.1).

## Resolved runtime topology

```text
services: db, redis, backend, frontend, worker
network:  nuvira-foundation-staging_internal
volumes:  nuvira-foundation-staging_postgres_data
          nuvira-foundation-staging_redis_data
          nuvira-foundation-staging_uploads_data
```

Runtime container evidence:

| Service | State/health | Published host port |
|---|---|---|
| `db` | running / healthy | none (`5432/tcp` internal only) |
| `redis` | running / healthy | none (`6379/tcp` internal only) |
| `backend` | running / healthy | `127.0.0.1:8800 -> 8000` |
| `worker` | running / healthy | none |
| `frontend` | running / healthy | `127.0.0.1:3300 -> 3000` |

Every container carried `com.nuvira.environment=staging` and `com.nuvira.mission=staging-01`. Runtime inspection rejected production volume names, the production proxy network, missing limits, non-loopback application bindings, and any DB/Redis host publication.

## Migration and PostgreSQL evidence

```text
0001_lowercase_emails -> 0002_security_controls (head)
0000_authoritative_schema -> 0001_lowercase_emails
<base> -> 0000_authoritative_schema

alembic current: 0002_security_controls (head)
alembic check:   No new upgrade operations detected.
extension:       vector
```

`tests/integration/test_postgres_foundation.py` reported `5 passed in 4.77s`. It created a fresh disposable database, ran Alembic to head, repeated the upgrade, checked drift, required the expected revision, queried native vector rows, exercised concurrent webhook delivery, and performed compatible/incompatible synthetic legacy adoption.

The production-era synthetic fixture retained the user, subject, chapter, and concept after adoption. The user's mixed-case email was normalized. An unexpected column caused classification to reject stamping. This is not evidence about the unknown live production schema.

## Security and worker evidence

Preserved pytest outputs:

```text
PostgreSQL: 5 passed
Backend:    36 passed, 9 skipped (the same 9 ran in dedicated live suites)
Celery:     1 passed
HTTP auth:  2 passed
Documents:  1 passed
```

The backend suite's three warnings were deprecation/cache warnings, not failures. The cache warning was caused by the non-root production-shaped container refusing to create `.pytest_cache` in `/app`; it did not change test execution.

The Celery proof inspected registered tasks, submitted `app.workers.tasks.ping`, and retrieved `pong` through Redis result DB 2. After Redis was deliberately stopped and restarted, the worker recovered and answered:

```text
-> foundation-worker@<ephemeral-container>: OK
   pong
1 node online.
```

The document proof used generated, non-sensitive PDF and PPTX files. Both produced chunks through the real worker. A controlled transient embedding failure caused exactly two attempts before success. Student B could not list Student A's documents; all resulting embeddings retained Student A ownership.

## Browser evidence

Command:

```bash
cd frontend
npm ci
npx playwright install --with-deps chromium
npm run test:e2e
```

Actual result:

```text
Running 6 tests using 2 workers
6 passed
```

Projects were desktop Chromium and Pixel 7. In each project:

- Registration, session restoration, direct settings access, refresh rotation, logout invalidation, refresh-cookie flags, staging-only API calls, and absence of URL credentials passed.
- Invalid login remained on `/login` with no URL credentials.
- The zero-subject dashboard settings-tab assertion was marked `test.fail(...)` and failed as expected. Playwright therefore counted the expected outcome as accepted. `error-context.md` for both projects is preserved in the artifact; the report does not claim the product defect is fixed.

The successful run produced no failure screenshot for normal flows because configuration captures screenshots only on unexpected failures. The HTML report and expected-failure contexts are the available browser evidence.

## Backup and restore evidence

Disposable database backup:

```text
9923b5671489c8c0c888d49d7b1eebe2b5cf5730f4cff133b5c3e58532a39899  database.dump
```

Disposable upload backup:

```text
8e1ee18ab3b46dc164eeef8d05cc2cd48aebeace569bc6ba5e8858382e66b8c0  uploads.tar.gz
```

The private backup files were not uploaded. The database was restored into `nuvira_staging_restore_test`, and uploads were restored into `nuvira-foundation-staging_uploads_restore_data` with `--network none` for extraction.

| Validation | Restored result |
|---|---|
| users | 10 |
| uploaded documents | 2 |
| embeddings | 2 |
| Alembic revision | `0002_security_controls` |
| upload files | 2 |
| original stack after rehearsal | `{"database":"ok"}` |

## Cleanup evidence

The workflow ended with scoped `docker compose ... down --remove-orphans`. It did not use `down -v`, `docker system prune`, a production Compose file, or a shared host. The GitHub runner was disposable.

