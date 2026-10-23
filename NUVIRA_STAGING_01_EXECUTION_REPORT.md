# NUVIRA STAGING-01 Execution Report

## Decision

**Mission status: SUCCESS — isolated infrastructure verification completed.**

The infrastructure and security gates required by STAGING-01 passed on an ephemeral GitHub-hosted Ubuntu runner. The known zero-subject dashboard/settings defect was reproduced on desktop and mobile as an explicit expected failure; it remains a student-product blocker and was not disguised as a pass. No production host, container, database, upload volume, proxy, DNS record, secret, or student record was accessed.

This result supports an **isolated staging deployment only**. It does not authorize production deployment or a merge to `main`.

## Source identity

| Item | Value |
|---|---|
| Repository | `https://github.com/mayakilzy/Nuvira.git` |
| Branch | `test/nuvira-staging-01` |
| Required baseline | `433849fad60f596dd502a53bab653de967c4fe50` (`foundation/nuvira-foundation-01`) |
| SECURITY-01 ancestor | `9cba55bfa8b6ae450fc307ed6c054b3926699a6d` |
| Runtime-tested SHA | `b4734bf59db45dcaab85ca993fe10b0bda4ec90d` |
| Final documentation SHA | recorded in the final handoff after the reports-only commit |
| Unchanged local and remote `main` | `db9fc4823ce65f08f9f770b8a32ac860de024587` |

Both required ancestors were verified with `git merge-base --is-ancestor`. Work started from the FOUNDATION-01 commit, not from `main`.

## Environment actually used

The development machine had no Docker, Podman, PostgreSQL client, or Redis runtime and had insufficient free system-drive space for a safe local stack. The real runtime therefore used an isolated, disposable GitHub Actions `ubuntu-24.04` virtual machine. This was not the shared production server.

- Runner kernel: Linux Azure x86_64, Ubuntu 24.04 runner image.
- Capacity at start: 15 GiB RAM, 3 GiB swap, 86 GiB free root filesystem.
- Docker Engine: 28.0.4.
- Docker Compose: 2.38.2.
- Host Node.js: 22.23.3; npm 10.9.9.
- Host Python: 3.12.3.
- Container/runtime component versions: preserved in `runtime-versions.txt` in the final evidence artifact and summarized in the runtime-evidence report.
- Compose project: `nuvira-foundation-staging`.
- Network: `nuvira-foundation-staging_internal` only.
- Named volumes: separately prefixed PostgreSQL, Redis, and upload volumes.
- Host bindings: frontend `127.0.0.1:3300`, backend `127.0.0.1:8800`; PostgreSQL and Redis had no published ports.
- External providers: Google OAuth, payments, AI/OpenRouter, email, and first-admin bootstrapping disabled. Uploads were enabled only for synthetic files, using the deterministic local test embedding provider.

## Execution history and discovered defects

The branch contains reproducible test infrastructure plus small defects discovered by real execution:

1. Added staging-only Compose, isolation validation, real PostgreSQL/pgvector, HTTP authentication, Redis/Celery, document-processing, Playwright, and backup/restore gates.
2. Repaired the legacy-schema inspector for PostgreSQL by reading the primary-key constraint through SQLAlchemy's portable inspector API.
3. Corrected test-container dependency and environment scoping.
4. Corrected validator-safe synthetic email addresses.
5. Replaced an invalid Celery wildcard destination with broadcast recovery checks.
6. Fixed accessible label associations on login, registration, settings, and every shared `Field` consumer after Playwright exposed that visual text was not an actual accessible label.
7. Added exact runtime-version capture to the sanitized evidence artifact.

No onboarding feature or visual redesign was implemented. The zero-subject dashboard navigation defect remains deferred as required.

## Commands and headline results

The authoritative CI command sequence is in `.github/workflows/staging-verification.yml`. Important commands and actual outcomes:

| Command/gate | Result | Actual output |
|---|---|---|
| `python3 scripts/staging/verify_isolation.py --env-file .env.staging` | PASS | Preflight exited 0 before startup. |
| `docker compose ... config --quiet` | PASS | Five services, one isolated network, three isolated volumes. |
| `docker compose ... build` | PASS | Backend and Next.js production images built; Next.js 16.3.8 production build passed. |
| `docker compose ... up -d --wait --wait-timeout 300` | PASS | All five services running and healthy. |
| `alembic history/current/check` | PASS | Head `0002_security_controls`; no new upgrade operations. |
| `pytest -q tests/integration/test_postgres_foundation.py` | PASS | 5 passed in 4.77s on PostgreSQL/pgvector. |
| `pytest -q --ignore=tests/test_staging_isolation.py` | PASS | 36 passed, 9 conditional integration tests skipped in this invocation; all nine were run separately below. |
| Redis/Celery integration suite | PASS | 1 passed; registered ping task and persisted result. |
| HTTP authentication suite | PASS | 2 passed against the live backend/PostgreSQL. |
| HTTP document suite | PASS | 1 passed in 33.05s against PDF, PPTX, worker, pgvector, and two synthetic students. |
| Broker stop/start recovery | PASS | Redis returned `PONG`; worker returned `pong` after restart. |
| `npm run test:e2e` | PASS with expected product failures | Six Playwright cases accepted: four normal passes plus two correctly observed expected failures for zero-subject dashboard settings navigation. |
| Database/upload backup and separate restore | PASS | Checksums recorded; restored counts and Alembic revision matched; original stack health remained `ok`. |
| Local `npx tsc --noEmit` | PASS | No TypeScript diagnostics. |
| Local `npx playwright test --list` | PASS | Six cases discovered across desktop Chromium and Pixel 7. |

## Evidence

- Final workflow run: `https://github.com/mayakilzy/Nuvira/actions/runs/39874587953`
- Final evidence artifact: `nuvira-staging-01-evidence-39874587953` (artifact ID `12468385525`)
- Artifact SHA-256: `5891fb74d25e7e12e9c57fa68819c930287ef2c8d85756b2529d2dda4068c25f`
- Artifact retention expires: `2026-11-05T23:56:44Z`
- Artifact includes environment, versions, resolved resources, container state, migration output, pytest output, broker recovery, Playwright HTML report/error contexts, and backup/restore checksums.

The artifact contains no `.env`, generated passwords, JWT secrets, database dump, upload archive, production credential, or real user data. Backups were used only inside the disposable runner; only their checksums and validation results were uploaded.

## Final scope statement

- Production unchanged: **confirmed**.
- Shared production server used: **no**.
- `main` changed or merged: **no**.
- Production deployment performed: **no**.
- Live OpenRouter, OAuth, email, or payment provider used: **no**.
- Real student content used: **no**.

