# Nuvira Deployment and Rollback

No deployment was performed. Production actions require owner approval and a successful isolated staging rehearsal.

## Target identity

- Repository: `https://github.com/mayakilzy/Nuvira.git`
- Directory: `/root/apps/nuvira/`
- Frontend: `https://nuvira.agentcraft.info`
- API: `https://api.nuvira.agentcraft.info`
- Images: `localdev/nuvira-frontend:1.0.0`, `localdev/nuvira-backend:1.0.0`
- Compose project: `nuvira`

## Network model

The Compose stack publishes no host ports. Nginx Proxy Manager must share the external `${PROXY_NETWORK:-hermes-network}` network with frontend/backend. PostgreSQL, Redis, and worker remain on `nuvira_internal`; only frontend/backend join the proxy network.

## Staging validation before rollout

1. Create a staging-only `.env` with fresh secrets and production-shaped domains.
2. Create/confirm the shared proxy network without touching existing project networks.
3. Run `docker compose config` and build immutable Nuvira images.
4. Confirm the frontend bundle was built with `NEXT_PUBLIC_API_URL=https://api.nuvira.agentcraft.info`.
5. Run migrations against an empty Nuvira database.
6. Exercise login, refresh, subject isolation, real chat, uploads, Celery processing, embeddings, and RTL/responsive browser flows.
7. Run a backup and restore into a second empty Nuvira stack.

## Existing-data migration

Do not assume legacy database or upload volumes exist in Nuvira. Use `docs/SUZANNA_TO_NUVIRA_MIGRATION.md` only in a separately authorized maintenance window. The source deployment must remain untouched and available for rollback.

## Rollout and rollback

Record the approved commit and image digests, then recreate only Nuvira services. Never run `docker compose down -v`. Rollback points Compose back to the recorded images/commit; database rollback uses a reviewed migration downgrade or a verified restore into isolated volumes.
