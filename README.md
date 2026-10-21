# FAHEM · Suzanna

FAHEM is a multilingual learning companion that turns an authenticated student's enrolled courses, chapters and uploaded materials into a calm, personal study experience. Suzanna explains concepts in the course's teaching language, grounds answers in processed materials when available, and quietly uses learning attempts to schedule review without punitive grades or fabricated progress.

## Core journeys

- A student signs in and enters a garden that grows from persisted learning attempts.
- A student browses enrolled subjects, chapters and concepts, then plays stored mechanism steps.
- A student asks Suzanna a course-scoped question using authenticated retrieval and OpenRouter.
- A student uploads PDF/PPT material, assigns it to a chapter and observes real worker status.
- A student switches the interface among German, English and Arabic with RTL support.

## Architecture

```text
Next.js student UI
  ├─ existing JWT auth + refresh
  ├─ typed educational API client
  └─ garden / chapters / chat / materials / preferences
                    │
                    ▼
FastAPI authorization boundary
  ├─ UserSubjectAccess enforcement
  ├─ study log + spaced review
  ├─ material status + Celery dispatch
  └─ scoped retrieval + OpenRouter
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
 PostgreSQL + pgvector     Redis + Celery
```

The SaaS foundation remains intact: accounts, JWT/Google authentication, billing, credits, admin, email, audit logs, backups and provider-independent payments.

## Technology

- Frontend: Next.js App Router, React, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Pydantic
- Data: PostgreSQL 16, pgvector; SQLite fallback for local tests
- Processing: Redis, Celery, pypdf, python-pptx
- AI: OpenRouter for chat and a separate embeddings provider
- Infrastructure: isolated Docker Compose stack, Nginx-compatible routing, backup/restore scripts

## Local development

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

## Verification

```powershell
cd backend
$env:DATABASE_URL="sqlite://"
python -m pytest -q

cd ..\frontend
npm run build
```

## API surface

| Area | Endpoints |
|---|---|
| Auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` |
| Learning | `/agent/subjects`, `/agent/chapters`, `/agent/concepts`, `/agent/attempt`, `/agent/review-queue`, `/agent/history` |
| Companion | `/agent/session/start`, `/agent/chat`, `/agent/fun-fact` |
| Materials | `/agent/materials`, `/agent/materials/upload` |
| Preferences | `/agent/preferences` |
| SaaS services | `/billing/*`, `/credits/*`, `/user/*`, `/admin/*` |

## Business model

The existing billing and credit ledger can support course access, subscriptions and metered AI usage. `UserSubjectAccess` is the server-side entitlement boundary for purchased, gifted or trial subjects.

## Roadmap

- Add an additive chapter-to-concept association and migration.
- Add a persistent authorized quiz bank and attempt sessions.
- Replace OAuth query tokens with a one-time exchange code.
- Verify AI retrieval and document processing in isolated staging.
- Reconcile archive, remote and deployed SHAs before an owner-approved rollout.

See [`docs/integration/05_FINAL_HANDOFF.md`](docs/integration/05_FINAL_HANDOFF.md) for the implementation handoff and acceptance status.
