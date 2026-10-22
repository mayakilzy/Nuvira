# NUVIRA FOUNDATION-01 Open Risks

## Critical

### PostgreSQL/pgvector migration proof is missing

The full chain passes SQLite, but the mission explicitly requires PostgreSQL 16 + pgvector. Extension creation, native vector DDL, PostgreSQL constraint/index semantics, and Alembic drift have not executed here.

- Mitigation: production remains untouched; managed startup fails closed on revision mismatch.
- Next action/owner: infrastructure engineer runs the staging guide on an isolated pgvector stack and records logs.

### Five-service Docker staging proof is missing

Docker is not installed on this host. Compose semantic validation, image builds, healthchecks, service discovery, worker readiness, and runtime isolation are unproven.

- Mitigation: staging resources are separately named and only loopback ports are declared.
- Next action/owner: infrastructure engineer executes all Compose gates on a Docker host before staging approval.

### Existing production schema has not been compared

The adoption tool is tested against synthetic historical schemas, not a sanitized production-schema clone. Unknown live drift could invalidate adoption assumptions.

- Mitigation: arbitrary schemas are rejected; no production inspection or stamp occurred.
- Next action/owner: database owner creates a verified backup/restored clone and runs the read-only parity report.

## High

### Redis/Celery and document-processing integration is unverified

Task registration, live ping, result persistence, broker outage recovery, parser retry, and partial-embedding cleanup were not run with real services.

- Next action: run the conditional Celery suite and synthetic document workflow in isolated staging.

### PostgreSQL webhook concurrency is unverified

A threaded integration test exists, but the unique constraint/transaction behavior has only unit-level sequential proof on this host.

- Next action: execute the PostgreSQL integration suite and provider-fixture tests; keep payments disabled.

### Backup/restore rehearsal is incomplete

Backup and restore procedures are documented but were not executed against the new staging stack. RTO/RPO cannot be claimed.

- Next action: back up staging DB/uploads, verify checksums, restore to a second isolated project, migrate, and run smoke tests.

### Browser E2E is blocked by host virtual memory

The Playwright test compiles and is discovered. Chrome crashed, and Edge reported `The paging file is too small for this operation to complete (0x5AF)` before any page opened.

- Next action: increase Windows paging file or run the test in CI/isolated staging with supported Chromium resources.

## Medium

### Frontend build-time API injection remains immutable

`NEXT_PUBLIC_API_URL` is compiled into the client bundle. Changing only the container runtime variable does not redirect an existing image.

- Next action: record image digest and API URL together; rebuild frontend for each environment.

### Email-verification policy remains undecided

FOUNDATION-01 does not define the product gate for unverified password accounts.

- Next action: product/security owner decides before onboarding work.

### Platform publication semantics remain implicit

Ownerless embeddings are treated as platform material after entitlement, but the curriculum publication/version model is deferred.

- Next action: implement explicit publication/version state in the curriculum mission before content ingestion.

### Dependency reproducibility is not fully hash-locked

The npm lock is deterministic and audit-clean. Backend direct versions are pinned, but a transitive hash-locked Python lock/SBOM is not present.

- Next action: generate a clean-container lock with hashes and CI audit.

## Low

### Windows line-ending notices

Git reports LF-to-CRLF notices in the working copy; `git diff --check` reports no whitespace errors.

- Next action: standardize line endings separately with `.gitattributes` if desired.

