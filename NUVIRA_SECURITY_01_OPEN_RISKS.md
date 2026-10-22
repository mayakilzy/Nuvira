# NUVIRA SECURITY-01 Open Risks

## Critical

### Authoritative database baseline is missing

- Evidence: a fresh disposable `python -m alembic upgrade head` fails at `0001_lowercase_emails.py` with `no such table: users`.
- Impact: new installations and controlled migration proof are not reliable; SECURITY-01 schema cannot be safely applied to production without schema reconciliation.
- Decision: deferred to FOUNDATION-01 as required by mission scope. Revision 0002 is additive and tested only after a simulated existing schema is stamped at 0001.
- Owner/next action: platform/database owner must inventory the live schema, create or adopt an authoritative baseline, rehearse backup/upgrade/restore, then approve staging.

## High

### Runtime integration evidence is unavailable

- Docker CLI is absent, so Compose validation, PostgreSQL/pgvector, Redis, Celery, container health, and proxy-network behavior are **BLOCKED/NOT RUN**.
- Next action: infrastructure owner provisions an isolated project and executes the deployment-handoff staging procedure.

### Real webhook concurrency and provider behavior are unverified

- A database unique constraint and transaction boundary prevent duplicate event claims, and sequential replay tests pass. PostgreSQL concurrent delivery, provider signature fixtures, failed/cancelled payments, and sandbox checkout were not run.
- Mitigation: `PAYMENTS_ENABLED=false` by default and no packs are seeded.
- Next action: billing owner configures approved sandbox products and runs concurrent signed webhook tests before enabling payments.

### Upload malware and parser isolation are incomplete

- Signature, size, quota, archive expansion, and retry controls exist, but no antivirus/CDR scanner or separate resource-limited parsing sandbox is implemented.
- Mitigation: `UPLOADS_ENABLED=false` by default.
- Next action: platform security owner adds malware scanning/quarantine and CPU/memory/time isolation, then runs malicious corpus tests.

### End-to-end cross-student isolation needs PostgreSQL proof

- SQLite regression tests prove the ownership predicate and existing API entitlement tests pass, but the complete upload→Celery→pgvector→RAG path was not executed against PostgreSQL.
- Mitigation: uploads and AI are independently disabled by default.
- Next action: security QA runs two-student adversarial staging tests with synthetic material.

### Email verification policy is not an authentication gate

- OAuth requires verified provider email; password registration can create a session before email verification. The mission did not define whether unverified password users may study, upload, or purchase.
- Next action: product/security owner defines the policy, then add route-level enforcement and browser tests if required.

## Medium

### Access token remains readable by frontend JavaScript

- The long-lived refresh credential is HttpOnly, but the short-lived access token is held in `sessionStorage` for the existing bearer-token architecture.
- Next action: maintain CSP/XSS controls and evaluate a complete backend-for-frontend or HttpOnly access-cookie design with robust CSRF protection.

### Rate limiting is process-local

- Multiple backend replicas do not share counters, and counters reset on restart.
- Next action: move authentication and abuse limits to Redis with tested trusted-proxy behavior.

### Dependency reproducibility is incomplete

- `pip-audit` reports no known issue in direct pinned requirements, but the backend does not have a fully resolved, hash-locked transitive requirements file. `pip check` on the host reported conflicts from unrelated globally installed packages, so it is not valid deployment evidence.
- GitHub still reports 54 alerts (5 critical, 26 high, 19 moderate, 4 low) on the unchanged default branch. SECURITY-01 is an unmerged review branch; alert closure and applicability cannot be claimed from that default-branch count.
- Next action: build in a clean virtual environment/container, generate a hash-locked transitive set, run `pip check` and `pip-audit` there, and add CI/SBOM scanning.

### Browser E2E and responsive/security headers were not exercised

- TypeScript and production compilation passed, but a real browser was not used for cookie, CORS, OAuth redirect, refresh, logout, mobile, or reverse-proxy headers.
- Next action: add Playwright tests through the isolated proxy.

### Platform-content publication state is implicit

- Retrieval treats an ownerless embedding as platform content after the API has verified subject entitlement. The current schema has no separate embedding-level publication flag, and `review_status` is not an explicit publication state.
- Next action: the curriculum owner must define draft/review/publish semantics in FOUNDATION-01; add an explicit state and query predicate before editors can ingest unpublished material.

### Legal retention rules need owner approval

- Payment/audit records are anonymized rather than deleted; no jurisdiction-specific retention schedule was supplied.
- Next action: legal/privacy owner approves record categories, retention durations, user notices, and operational erasure SLA.

## Low

### Windows line-ending notices

- `git diff --check` reported no whitespace errors, only LF-to-CRLF conversion notices from the Windows checkout.
- Next action: optionally enforce repository line endings with `.gitattributes` in a separate maintenance change.

### Tailwind/Next major-version follow-up

- The patched Next/Tailwind build passes, but visual browser regression was not run.
- Next action: compare key routes in isolated staging before merge.
