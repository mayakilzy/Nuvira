# Nuvira Final Engineering Handoff

## Outcome

The integrated educational application is branded as **Nuvira** across visible UI, Next.js metadata, backend identity, package metadata, documentation, environment examples, backup tooling, Compose identity, network/volume names, and Docker images.

Educational functionality, authentication contracts, database models, table names, and migrations remain unchanged. The Nuvira API retains server-side subject authorization and uploader-scoped materials.

## Deployment preparation

- Compose project: `nuvira`
- Services: frontend, backend, worker, Redis, PostgreSQL
- Images: `localdev/nuvira-frontend:1.0.0`, `localdev/nuvira-backend:1.0.0`
- Internal ports: frontend 3000, backend 8000
- Host port mappings: none
- Proxy integration: explicit external network shared only by frontend/backend
- Production frontend origin is covered by a FastAPI CORS regression test
- `NEXT_PUBLIC_API_URL` is injected during the frontend Docker build

## Verification

- Backend tests: **PASS — 11/11**
- Nuvira identity/CORS tests: **PASS — 2/2**
- Frontend production build: **PASS**
- TypeScript: **PASS**
- Compose static isolation review: **PASS**
- Shell syntax for deployment/backup scripts: **PASS**
- Docker runtime: **BLOCKED** on the review host

## Data migration

`docs/SUZANNA_TO_NUVIRA_MIGRATION.md` defines a separate, checksum-verified procedure for accounts, entitlements, progress, document metadata/embeddings, and uploaded files. It intentionally does not copy the legacy `.env`, Redis state, networks, or volumes. The procedure was not executed.

## Remaining blockers

- GitHub authentication must be valid before pushing.
- Docker build/runtime, shared proxy networking, migrations, and backup/restore require isolated staging.
- Real OpenRouter/embedding and Redis/Celery flows remain unverified.
- Real quiz generation is not implemented.
- New final-brand screenshots and automated browser E2E are still needed.
- OAuth query-string tokens remain a security follow-up.

## Readiness

The source is ready for GitHub publication and isolated staging after final commit review. It is not ready for production deployment.
