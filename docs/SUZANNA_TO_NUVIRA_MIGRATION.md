# Legacy Suzanna-to-Nuvira Data Migration Runbook

This runbook prepares a separate, owner-authorized migration. It was not executed, and no existing deployment was accessed or modified.

## Goal and boundaries

Move reviewed data into empty Nuvira storage while keeping the legacy deployment untouched and independently recoverable. Preserve:

- user accounts, password hashes, roles, OAuth associations, subscriptions, and credit ledger;
- subject packages and `UserSubjectAccess` entitlements;
- preferences, avatar state, study logs, attempts, and review progress;
- uploaded-document metadata, embeddings, and the corresponding uploaded files.

Do not copy the legacy `.env`, Redis state, running containers, Compose network, or named volumes into Nuvira. Create fresh Nuvira secrets and rebuild Redis/Celery state.

## Phase 1 — read-only discovery

1. Obtain explicit change-window approval and identify the exact source directory, Compose project, commit, schema revision, database container, and uploads location.
2. Record source row counts for users, subject access, study logs, documents, embeddings, subscriptions, and credits.
3. Confirm Nuvira is at a schema-compatible commit. If revisions differ, rehearse the migration on a disposable copy first.
4. Confirm sufficient encrypted storage for two database copies, uploads, and checksums.

## Phase 2 — source backup

Run from the approved legacy project directory during a maintenance window. Replace placeholders only after discovery:

```bash
mkdir -p /root/migration/nuvira-source
docker compose exec -T db pg_dump --no-owner --no-acl \
  -U <source_db_user> <source_db_name> \
  > /root/migration/nuvira-source/database.sql
docker compose cp backend:/app/uploads /root/migration/nuvira-source/uploads
sha256sum /root/migration/nuvira-source/database.sql \
  > /root/migration/nuvira-source/SHA256SUMS
find /root/migration/nuvira-source/uploads -type f -print0 \
  | sort -z | xargs -0 sha256sum >> /root/migration/nuvira-source/SHA256SUMS
```

Take the platform's normal full backup as a separate rollback artifact. Do not stop, delete, or repoint the source stack.

## Phase 3 — restore into isolated Nuvira

1. Create a fresh Nuvira `.env` and proxy network configuration.
2. Start only the empty Nuvira database and Redis: `docker compose up -d db redis`.
3. Verify checksums, then restore with errors treated as fatal:

```bash
cd /root/migration/nuvira-source
sha256sum -c SHA256SUMS
cd /root/apps/nuvira
docker compose exec -T db psql -v ON_ERROR_STOP=1 \
  -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  < /root/migration/nuvira-source/database.sql
docker compose up -d backend worker frontend
docker compose cp /root/migration/nuvira-source/uploads/. backend:/app/uploads/
docker compose exec -T backend alembic upgrade head
```

If legacy document paths contain an old absolute prefix, prepare and review a data-only path rewrite before applying it. Never change table or migration names merely for branding.

## Phase 4 — verification before cutover

- Compare all recorded row counts and foreign-key relationships.
- Test sampled legacy and admin logins without resetting password hashes.
- Verify subject entitlements and denial for a different student/subject.
- Verify garden progress, review queue, preferences, and avatar state.
- Open sampled uploaded files and confirm material metadata/embeddings belong to the correct user and subject.
- Reprocess one non-sensitive staging document through Redis/Celery.
- Run the complete automated and browser suites against Nuvira.

## Cutover and rollback

Cutover requires separate authorization after verification. Keep the source deployment unchanged and DNS untouched until approval. If Nuvira verification fails, stop Nuvira services, retain logs and migration artifacts, and return to the empty pre-migration Nuvira volumes or recreate them only with explicit destructive-action approval. The legacy deployment remains the rollback source of truth throughout the window.
