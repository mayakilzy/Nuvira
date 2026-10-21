# SaaS Template

**Production-ready full-stack SaaS starter — build once, deploy for every new product. Auth · billing · credits · admin · AI layer are done. Bring your idea, the plumbing is finished.**

🌐 **Live demo:** https://saas.agentcraft.info · https://publisher.agentcraft.info

---

## The method

```
1. This repo = the template (also what you sell as source code)
2. Build two base Docker images, push to Docker Hub with semantic version tags:
       youruser/saas-base-backend:1.0.0
       youruser/saas-base-frontend:1.0.0
3. For a new product: write a tiny Dockerfile FROM the base image,
   COPY only the files that change (agent.py · tasks.py · workspace UI)
   Builds take seconds, not minutes
4. docker compose orchestrates your images + postgres:16 + redis:7
   Multi-arch (amd64 + arm64) — runs on any server
```

---

## What you change per product

| File | Purpose |
|---|---|
| `backend/app/routers/agent.py` | The product's AI endpoint(s) |
| `backend/app/workers/tasks.py` | Background jobs |
| `frontend/src/app/workspace/` | The product UI |
| `.env` → `OPENROUTER_MODEL` | Which model to use |
| `credits_service.CREDIT_COSTS` | Cost per action |

Everything else is fixed infrastructure — never touched again.

---

## What's included

### Auth
- Email + password registration and login
- Email verification + password reset via Resend
- Google OAuth
- JWT access token + refresh token
- Role system: user · agency · admin

### Billing
- Lemon Squeezy (default) · Paddle · Stripe — switchable via one env var
- Signed webhooks with idempotent credit grants
- Per-IP rate limiting

### Credits ledger
- Full debit/credit audit log
- Per-action cost configuration
- Gating middleware — blocks actions when balance is zero

### Admin panel
- User management · manual credit grants · plan overrides · stats

### AI layer
- OpenRouter wrapper — model-agnostic, one line to swap models
- Celery worker skeleton for async AI tasks
- Streaming support

### 5-layer protection system
1. **Automatic backups** — DB + `.env` + uploads → local + S3/R2 + Drive, with rotation
2. **One-command restore** — rebuilds the full platform on any server in ~20 min
3. **Monitoring + alerts** — checks site, DB, disk, SSL every 5 min, emails on failure
4. **Internal hardening** — rate limiting · security headers · private DB/Redis · audit log
5. **Server migration** — backup on old box, restore on new one, same command

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 · TypeScript · Tailwind CSS |
| Backend | FastAPI (Python 3.11) · Celery · Redis |
| Database | PostgreSQL 16 + pgvector · Alembic migrations |
| Auth | JWT · Google OAuth · Resend (email) |
| Billing | Lemon Squeezy · Paddle · Stripe |
| AI | OpenRouter (model-agnostic gateway) |
| Infrastructure | Docker Compose · multi-arch (amd64 + arm64) |

---

## Quick start

```bash
git clone https://github.com/mayakilzy/saas-template
cd saas-template
cp .env.example .env   # fill in secrets, set DOCKER_NS

docker compose up -d --build
# frontend: http://localhost:3008
# API docs: http://localhost:8995/docs
```

## Publish base images

```bash
docker login
DOCKER_NS=youruser ./scripts/build-and-push.sh 1.0.0
```

## Deploy on a fresh server

```bash
cp .env.example .env   # set DOCKER_NS + TAG + secrets
docker compose pull
docker compose up -d
```

---

## Resource footprint

~1.1 GB RAM for the full stack. On a 4 GB server, skip `--profile full` (no Celery worker) to drop to ~760 MB. Comfortable to run 2–4 instances alongside other projects.

---

## Products built on this template

| Product | URL |
|---|---|
| AgentCraft Publisher | https://publisher.agentcraft.info |
| Idea Discovery Agent | https://ideas.agentcraft.info |
| Smart Review Intelligence | https://sri.agentcraft.info |

---

*Part of the [AgentCraft](https://agentcraft.info) ecosystem — built by Ayman Al-Saeed.*
