# Nuvira Architecture

```text
Internet
  │
  ▼
Nginx Proxy Manager (external proxy network)
  ├─ nuvira.agentcraft.info ───────▶ frontend:3000
  └─ api.nuvira.agentcraft.info ───▶ backend:8000
                                      │
                         Nuvira internal bridge
                         ├─ PostgreSQL + pgvector
                         ├─ Redis
                         └─ Celery worker + uploads volume
```

## Isolation

- `name: nuvira` fixes the Compose project identity.
- `nuvira_internal` carries application-only traffic.
- `${PROXY_NETWORK:-hermes-network}` is external and is attached only to frontend/backend.
- No service has a `ports:` mapping. `expose` documents container ports without publishing them.
- Named volumes are `nuvira_postgres_data`, `nuvira_redis_data`, and `nuvira_uploads`.
- Images are `localdev/nuvira-frontend:1.0.0` and `localdev/nuvira-backend:1.0.0`; the worker uses the backend image.

## Application layers

- **Frontend** — Next.js standalone application. `NEXT_PUBLIC_API_URL` is supplied as a Docker build argument because browser-facing values are compiled into the production bundle.
- **Backend** — FastAPI with JWT/Google authentication, educational authorization, billing, credits, admin, and health endpoints.
- **Database** — PostgreSQL/pgvector. Existing table and migration names remain unchanged by the rebrand.
- **Worker** — independent Celery service using private Redis and the shared Nuvira uploads volume.
- **AI** — OpenRouter chat plus a separately configured embedding provider.
