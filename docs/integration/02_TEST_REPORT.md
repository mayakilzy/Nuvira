# Nuvira Integration Test Report

Date: 2026-10-22  
Branch: `main`

## Automated checks

| Check | Command | Result |
|---|---|---|
| Backend tests | `$env:DATABASE_URL='sqlite://'; python -m pytest -q` | **PASS** — 11 tests in 5.66s |
| Nuvira identity and production CORS | `$env:DATABASE_URL='sqlite://'; python -m pytest -q tests/test_cors_branding.py` | **PASS** — 2 tests in 0.12s |
| Frontend production build | `$env:NEXT_PUBLIC_API_URL='https://api.nuvira.agentcraft.info'; npm run build` | **PASS** — compiled, TypeScript completed, 14 static routes generated |
| Independent TypeScript validation | `.\node_modules\.bin\tsc.cmd --noEmit` | **PASS** — no diagnostics |
| Compose static parse/isolation assertions | PyYAML load and assertions | **PASS** — `name=nuvira`, five services, exact images, zero published ports, isolated DB network |
| Backup/deployment script syntax | Git for Windows Bash `-n` | **PASS** |
| Docker runtime | `docker compose config/build/up` | **BLOCKED** — Docker CLI is not installed on the review host |

Pytest continues to emit a non-failing deprecation warning because `asyncio_default_fixture_loop_scope` is unset.

## Preserved functional evidence

The earlier isolated browser run remains relevant because the rebrand changed identity, paths, metadata, and deployment configuration without altering educational API behavior or database models:

| Journey | Result |
|---|---|
| Email/password login and `/dashboard` redirect | PASS |
| Authorized subject, chapter, concept, garden, and mechanism loading | PASS |
| Cross-student and cross-subject isolation | PASS automated |
| Mobile layout and Arabic RTL | PASS |
| Real OpenRouter response | BLOCKED — credentials not supplied |
| Celery/Redis document completion | BLOCKED — isolated Docker runtime unavailable |
| Automated browser E2E suite | NOT RUN — no Playwright/Cypress suite exists |

Existing screenshots are historical functional evidence and may contain the pre-rebrand companion label. They must not be treated as proof of the final Nuvira wordmark until new staging screenshots are captured.

## Source safety

- No database table, model, migration, or authentication token key was renamed.
- No existing deployment was contacted.
- No host ports are declared in Compose.
- Only frontend/backend join the external proxy network; DB, Redis, and worker remain internal.
