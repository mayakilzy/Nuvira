# NUVIRA SECURITY-01 Deployment Handoff

## Deployment decision

Do not deploy this branch to production. It is suitable for code review and for constructing an isolated security staging environment only after the authoritative database baseline is repaired/adopted. Production, Nginx Proxy Manager, DNS, volumes, databases, secrets, and containers were not accessed or changed during SECURITY-01.

## Required configuration contract

Create the deployment `.env` outside Git from `.env.example`. Never reuse the example values.

Required core values:

- `ENV=production`, `DEBUG=false`
- `FRONTEND_URL=https://nuvira.agentcraft.info`
- `PUBLIC_API_URL=https://api.nuvira.agentcraft.info` at frontend image build time
- a unique `JWT_SECRET` of at least 64 characters
- unique PostgreSQL credentials and correct internal `DATABASE_URL`
- Redis/Celery internal URLs
- `TRUSTED_PROXY_IPS` containing only the real Docker proxy peers that terminate requests

Feature flags default to false: `GOOGLE_OAUTH_ENABLED`, `PAYMENTS_ENABLED`, `AI_ENABLED`, `EMAIL_ENABLED`, `FIRST_ADMIN_ENABLED`, and `UPLOADS_ENABLED`. Enable a feature only after its credentials and staging evidence exist. Production validation rejects enabled-but-unconfigured integrations.

For OAuth, register the exact callback `https://api.nuvira.agentcraft.info/auth/google/callback`. For cookies/CORS, the browser origin must exactly match `FRONTEND_URL` or an intentionally listed `EXTRA_CORS_ORIGINS` value.

## Migration gate

1. Take and verify a PostgreSQL backup plus upload-volume backup.
2. Inventory the live schema and current Alembic version read-only.
3. Complete FOUNDATION-01 to create or adopt an authoritative baseline for all pre-existing tables.
4. In an isolated clone of the schema, stamp only the verified adopted baseline; never guess a revision.
5. Run `python -m alembic upgrade head` and confirm revision `0002_security_controls`.
6. Verify new tables, unique constraints, indexes, and upload columns.
7. Exercise rollback on a disposable copy. Do not downgrade a live database merely as a test.

The current repository cannot initialize an empty database: revision `0001_lowercase_emails` assumes `users` already exists. Until this is corrected, deployment is blocked.

## Session compatibility

- Existing stateless refresh JWTs are not accepted by the new opaque refresh-session store. Plan a controlled sign-in reset at rollout.
- Rotate `JWT_SECRET` only with an explicit invalidation window; rotation logs out all access-token users.
- Legacy frontend local-storage refresh material is deleted on app startup and is not migrated.
- Ensure HTTPS before production cookie testing; the refresh cookie is `Secure` in production.

## Staging procedure

1. Build immutable frontend/backend images from the reviewed branch SHA; inject `NEXT_PUBLIC_API_URL` during the frontend build.
2. Use a new project-isolated PostgreSQL database, Redis instance/databases, upload volume, and Docker network. Do not mount Suzanna/SaaSForge/Nuvira production volumes.
3. Start with every optional feature flag false.
4. Apply the repaired migration chain to a disposable database.
5. Run health checks and the full test suite.
6. Verify registration/login/refresh/logout/reset in a real browser through the reverse proxy, including Origin/CORS, cookie flags, and no URL tokens.
7. With synthetic students, verify same-subject cross-user RAG isolation and document ownership on PostgreSQL/pgvector.
8. Start Redis and the Celery worker; test forged, oversized, malformed, compressed, interrupted, and retried documents in an isolated parser environment.
9. If payments are enabled, use provider sandbox products populated as server-owned rows; test signatures, failed/cancelled events, replay, and concurrent duplicate delivery.
10. Enable Google, email, AI, payments, uploads, and admin bootstrap one at a time only after each gate passes. Disable first-admin bootstrap after the controlled account is created.

## Backup and restore prerequisites

- PostgreSQL logical backup with restore rehearsal and recorded checksum.
- Upload-volume snapshot/tar with permissions and checksum.
- Encrypted, access-controlled backup of deployment configuration/secrets outside the repository.
- Record image digests, branch SHA, Alembic revision, feature flags, and proxy-network membership.
- Confirm restore into an isolated project before any production change.

## Rollback plan

Rollback requires the pre-deployment database/upload backups and previous image digests. Stop traffic-changing actions, disable optional integrations, restore the previous images, and restore database/uploads together if the migration has been applied. Do not rely on application-code rollback alone after session/security schema writes. New opaque sessions are incompatible with the old refresh-JWT model; expect forced reauthentication in either direction.

## Production risks

- Fresh migration baseline failure is a hard blocker.
- No Docker/PostgreSQL/Redis/Celery/browser/provider sandbox run was possible here.
- A malware scanner and stronger parser process isolation are not present.
- Real concurrent webhook behavior needs PostgreSQL stress testing.
- Production secret inventory and feature credentials were intentionally not inspected.
