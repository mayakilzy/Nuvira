# Deployment and Rollback

No deployment was performed. Owner approval is required before any production action.

## Local preview

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
$env:DATABASE_URL="sqlite:///./dev.db"
$env:JWT_SECRET="local-only-secret"
python -m uvicorn app.main:app --reload --port 8995

cd ..\frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8995"
npm run dev
```

## Isolated Docker validation before rollout

1. Copy `.env.example` to a staging-only `.env` and use fresh secrets.
2. Use a unique Compose project name, network, ports and empty volumes.
3. Set `DOCKER_NS`, an immutable `TAG`, and `PUBLIC_API_URL` for the isolated API.
4. Build application-specific images only: `fahem-backend` and `fahem-frontend`.
5. Run `docker compose --profile full up -d --build` and verify DB, Redis, worker, backend and frontend health.
6. Run migrations against the staging database and execute login, chat and upload smoke tests.

## Production prerequisites

- Read-only compare deployed SHA/working tree and Compose overrides against this branch.
- Back up PostgreSQL, uploads and `.env`; test restore in isolation.
- Confirm all existing rows are compatible. This change currently requires no migration.
- Build frontend with `NEXT_PUBLIC_API_URL=https://api.suzanna.agentcraft.info`.
- Use a new immutable FAHEM image tag; never reuse `aymansaeed/saas-base-frontend:1.0.0`.
- Confirm the Celery worker is healthy before enabling uploads.

## Rollout

1. Obtain owner approval.
2. Tag the pre-rollout commit and record current image digests.
3. Pull the reviewed integration commit.
4. Build/pull immutable FAHEM images.
5. Run non-destructive migrations if later added.
6. Recreate only application services; do not remove volumes.
7. Smoke-test login, `/auth/me`, subjects, chapters, chat and material status.

## Rollback

1. Point Compose back to the recorded image tags/commit.
2. Recreate frontend/backend/worker without `down -v`.
3. If a future migration is involved, follow its reviewed downgrade plan only after confirming backup integrity.
4. Re-run authentication and educational API smoke tests.
