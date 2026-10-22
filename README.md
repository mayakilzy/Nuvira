# Nuvira

Nuvira is a multilingual learning companion that turns an authenticated student's enrolled subjects, chapters, concepts, and uploaded materials into a calm, personal study experience. It explains course concepts, plays stored mechanisms, grounds AI answers in authorized materials when available, and schedules review from persisted learning attempts without fabricating progress.

- Repository: `https://github.com/mayakilzy/Nuvira.git`
- Frontend: `https://nuvira.agentcraft.info`
- API: `https://api.nuvira.agentcraft.info`
- Planned server directory: `/root/apps/nuvira/`

## Core journeys

- Sign in and view a garden driven by persisted learning attempts.
- Browse authorized subjects, chapters, concepts, and mechanism steps.
- Ask the Nuvira companion a course-scoped question through OpenRouter.
- Upload PDF/PPT material, assign it to a chapter, and observe real Celery status.
- Switch the interface among German, English, and Arabic with RTL support.

## Architecture

```text
Browser
  ├─ https://nuvira.agentcraft.info ───────▶ frontend:3000
  └─ https://api.nuvira.agentcraft.info ───▶ backend:8000
                         Nginx Proxy Manager / shared proxy network
                                             │
                 ┌───────────────────────────┴───────────────────────────┐
                 │                    Nuvira stack                       │
                 │ frontend + backend ── project-internal network       │
                 │                    ├─ PostgreSQL + pgvector           │
                 │                    └─ Redis ── Celery worker          │
                 └───────────────────────────────────────────────────────┘
```

No application or database port is published on the host. Nginx Proxy Manager reaches only `frontend:3000` and `backend:8000` through the explicitly configured external proxy network. PostgreSQL and Redis remain on the Nuvira-only internal network.

## Technology

- Frontend: Next.js 16 App Router, React 19, TypeScript, Tailwind CSS
- Backend: FastAPI, SQLAlchemy, Pydantic
- Data: PostgreSQL 16 and pgvector; SQLite for isolated tests
- Processing: Redis, Celery, pypdf, python-pptx
- AI: OpenRouter for chat and a separate embeddings provider
- Platform: JWT/Google authentication, billing, credits, admin, email, audit logs

## Local development

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
$env:DATABASE_URL="sqlite:///./dev.db"
$env:JWT_SECRET="local-only-secret"
$env:FRONTEND_URL="http://localhost:3000"
python -m uvicorn app.main:app --reload --port 8995

cd ..\frontend
npm install
$env:NEXT_PUBLIC_API_URL="http://127.0.0.1:8995"
npm run dev
```

## Production preparation

1. Create the external proxy network once during deployment: `docker network create hermes-network`.
2. Clone the repository to `/root/apps/nuvira/`.
3. Copy `.env.example` to `.env`, replace every placeholder, and keep `PROXY_NETWORK` aligned with Nginx Proxy Manager.
4. Build with the production API URL: `docker compose build --build-arg NEXT_PUBLIC_API_URL=https://api.nuvira.agentcraft.info frontend`.
5. Start the isolated stack: `docker compose up -d`.
6. Configure Nginx Proxy Manager to route the frontend domain to `frontend:3000` and API domain to `backend:8000` on the shared network.

Do not reuse or attach existing deployment volumes. If legacy data is intentionally migrated, follow [`docs/SUZANNA_TO_NUVIRA_MIGRATION.md`](docs/SUZANNA_TO_NUVIRA_MIGRATION.md) and obtain an independently verified backup first.

## Verification

```powershell
cd backend
$env:DATABASE_URL="sqlite://"
python -m pytest -q

cd ..\frontend
npm run build
.\node_modules\.bin\tsc.cmd --noEmit
```

Docker runtime validation requires Docker and a pre-created proxy network. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## API surface

| Area | Endpoints |
|---|---|
| Auth | `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me` |
| Learning | `/agent/subjects`, `/agent/chapters`, `/agent/concepts`, `/agent/attempt`, `/agent/review-queue`, `/agent/history` |
| Companion | `/agent/session/start`, `/agent/chat`, `/agent/fun-fact` |
| Materials | `/agent/materials`, `/agent/materials/upload` |
| Preferences | `/agent/preferences` |
| Platform | `/billing/*`, `/credits/*`, `/user/*`, `/admin/*` |

## Known release blockers

- Real OpenRouter and embedding calls require staging-only credentials.
- Redis/Celery document processing has not completed an isolated Docker rehearsal.
- A persistent quiz bank and real quiz-generation API do not yet exist.
- Production environment, backup/restore, proxy routing, and OAuth flows require staging verification.

See [`docs/integration/05_FINAL_HANDOFF.md`](docs/integration/05_FINAL_HANDOFF.md) for the current engineering handoff.
