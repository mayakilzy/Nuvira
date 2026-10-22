# NUVIRA FOUNDATION-01 Migration Guide

## Safety boundary

These procedures are for a new isolated database or an owner-controlled restored clone. Do not point commands at production during FOUNDATION-01. Never stamp a schema merely to bypass a failure.

## Fresh installation

1. Provision PostgreSQL 16 with permission to create the `vector` extension.
2. Configure a staging-only `DATABASE_URL`.
3. Confirm the database is empty.
4. Run:

```bash
cd backend
python -m alembic history
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

Expected head: `0002_security_controls`. Verify `SELECT extname FROM pg_extension WHERE extname='vector';` and inspect all application tables, foreign keys, indexes, and the unique `(provider,event_id)` constraint.

The managed application must start only after the upgrade. It will refuse a missing or stale Alembic revision.

## Database classification and legacy adoption

Always begin read-only:

```bash
cd backend
python scripts/adopt_legacy_schema.py
```

Possible states:

- `fresh`: run `alembic upgrade head`; never stamp.
- `versioned`: inspect the reported revision, take backups, then run the normal upgrade if approved.
- `legacy-compatible` with target `0000_authoritative_schema`: historical create-all schema matches; it may be adopted after backup verification.
- `legacy-compatible` with target `0002_security_controls`: complete unversioned head matches and emails are canonical.
- `incompatible`: stop. Resolve the listed structural difference through a reviewed migration; do not stamp.

For a compatible restored clone only:

```bash
python scripts/adopt_legacy_schema.py --apply-stamp --acknowledge-backup
python -m alembic upgrade head
python -m alembic current
python -m alembic check
```

The pre-security adoption stamps `0000`, not `0001`. This ensures the existing `0001` duplicate-email check and normalization actually run. Duplicate case-insensitive emails abort before normalization and must be reviewed/merged by the owner before retry.

## Compatibility of the inserted baseline

FOUNDATION-01 adds a parent revision and changes only the published `0001.down_revision` relationship. Revision IDs `0001_lowercase_emails` and `0002_security_controls` remain unchanged.

- A database already stamped `0002` remains at head and does not run `0000` or `0001` again.
- A database stamped `0001` runs only `0002` during upgrade.
- An unversioned historical database must pass parity and be stamped at `0000`.
- A fresh database runs all three revisions.

Test this behavior again on a sanitized production-schema clone before any live approval.

## Schema parity verification

The adoption tool checks:

- Exact expected application table set
- Exact columns and string lengths
- Type families, nullability, and primary keys
- Foreign-key targets
- Required index names, columns, and uniqueness
- pgvector extension on PostgreSQL
- Canonical emails before permitting an unversioned head stamp

After upgrade, run `alembic check`. Any generated operation is unresolved drift and blocks deployment.

## Backup before adoption or upgrade

On an owner-controlled database host:

```bash
pg_dump --format=custom --no-owner --no-acl "$DATABASE_URL" > nuvira_before_foundation.dump
sha256sum nuvira_before_foundation.dump > nuvira_before_foundation.dump.sha256
```

Back up the upload volume separately with preserved paths and permissions, generate a SHA-256 checksum, and store both copies outside the application host. Do not store `.env` or credentials in Git.

Verify by restoring into a newly created isolated database:

```bash
sha256sum -c nuvira_before_foundation.dump.sha256
createdb nuvira_foundation_restore_test
pg_restore --exit-on-error --clean --if-exists --no-owner \
  --dbname=nuvira_foundation_restore_test nuvira_before_foundation.dump
```

Run the adoption check against the restored database, not production.

## Failure recovery

- Baseline creation failure on a fresh disposable DB: drop/recreate only that disposable DB and rerun after correcting the migration.
- Email collision at `0001`: preserve the failed database, inspect duplicate groups, resolve accounts under an approved identity policy, and rerun. Do not delete arbitrary users.
- `0002` failure: stop application startup, preserve logs and database, restore the pre-upgrade backup into isolation, diagnose, and create a forward repair migration.
- Interrupted migration: inspect `alembic_version` and schema. Do not guess/stamp. Restore the clone if transactional guarantees are uncertain.
- Missing pgvector privilege: have the database owner run `CREATE EXTENSION vector` in the isolated database, then retry.

## Rollback limitations

`0001` lowercasing is intentionally irreversible. Downgrading `0000` drops all application tables and is suitable only for disposable tests. For any database containing valued data, the supported rollback is restore of the verified database dump together with its matching upload snapshot and previous application images.

## Owner-controlled production inspection procedure

If later authorized, use read-only credentials to collect table/column/index/constraint and Alembic-version metadata plus the duplicate-email query. Do not run the adoption tool with `--apply-stamp`, migrations, DDL, or backup commands until the owner separately authorizes the controlled deployment window.
