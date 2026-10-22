# Nuvira Deployment Preparation

No production deployment was performed while preparing this repository.

## Prerequisites

1. Clone to `/root/apps/nuvira/`.
2. Create or confirm the Nginx Proxy Manager network: `docker network inspect hermes-network` (create only if deployment owners confirm it is absent).
3. Create a fresh `.env` from `.env.example`; never reuse another application's secrets.
4. Confirm DNS and TLS for `nuvira.agentcraft.info` and `api.nuvira.agentcraft.info`.
5. Record the reviewed commit and image digests.

## Build and start

```bash
cd /root/apps/nuvira
docker compose config
docker compose build --build-arg NEXT_PUBLIC_API_URL=https://api.nuvira.agentcraft.info frontend backend worker
docker compose up -d
docker compose exec -T backend alembic upgrade head
```

The Compose file publishes no host ports. Configure Nginx Proxy Manager on the shared network:

| Domain | Forward host | Forward port |
|---|---|---:|
| `nuvira.agentcraft.info` | `frontend` | 3000 |
| `api.nuvira.agentcraft.info` | `backend` | 8000 |

## Smoke tests

- `GET https://api.nuvira.agentcraft.info/health`
- `GET https://api.nuvira.agentcraft.info/health/db`
- registration/login/refresh and `/auth/me`
- enrolled and unenrolled subject access
- chapters, concepts, attempts, and preferences
- real OpenRouter chat with and without material context
- upload, Celery processing, embedding persistence, and status polling
- German, English, Arabic RTL, desktop, and mobile browser journeys

## Rollback

Return to the recorded commit/image digests and recreate frontend, backend, and worker without `down -v`. Database rollback requires a reviewed migration downgrade or restoration into separately prepared volumes. Never remove Nuvira named volumes until backup integrity and rollback approval are confirmed.
