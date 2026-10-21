# Architecture

```
Browser ──▶ Reverse proxy ──▶ Frontend (Next.js, :3000)
                          └──▶ Backend  (FastAPI, :8000) ──▶ PostgreSQL
                                                          ├─▶ Redis ──▶ Celery worker
                                                          └─▶ OpenRouter (AI)
```

- **Frontend** — Next.js 15 (standalone). Talks to the backend over HTTP with a
  JWT stored client-side; auto-refreshes expired tokens.
- **Backend** — FastAPI. Stable modules (auth, billing, credits, admin, user)
  never change between products; `routers/agent.py` and `workers/tasks.py` are
  the per-product files.
- **Database** — PostgreSQL, private (never exposed to the host/internet).
- **Redis + Celery** — background jobs.
- **Payments** — one provider-agnostic interface; Lemon Squeezy / Paddle / Stripe
  selected by `PAYMENT_PROVIDER`.
- **Credits** — append-only ledger; balance is the sum of entries.

## What changes per project
`routers/agent.py`, `workers/tasks.py`, `frontend workspace`, `core/seed.py`
(plans), `OPENROUTER_MODEL`, and `CREDIT_COSTS`. Everything else is fixed.
