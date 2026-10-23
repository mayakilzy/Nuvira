# NUVIRA STAGING-01 Open Risks

STAGING-01 closes the prior critical runtime-evidence gaps for isolated infrastructure. The following risks remain and prevent a production-ready claim.

## Critical

### Dependency vulnerability disposition is incomplete

The current frontend `npm ci` reported one critical-severity audit finding. GitHub also reported 54 Dependabot alerts on the unchanged default branch (5 critical, 26 high, 19 moderate, 4 low). Those two observations have different scopes; neither is silently treated as resolved by this branch.

- Impact: unknown until the exact dependency path, runtime reachability, and patched-version compatibility are reviewed.
- Evidence limit: a local `npm audit --json` retry on 2026-10-23 was **BLOCKED** by the local registry TLS trust chain (`unable to verify the first certificate`), so no package/advisory attribution is invented here.
- Required action: run and archive clean-container `npm audit --json`, backend `pip-audit`, image/SBOM scans, triage applicability, update dependencies on a dedicated remediation branch, and rerun STAGING-01.

### Actual production schema compatibility remains unproved

Legacy adoption passed on a synthetic fixture only. No production database, dump, or sanitized restored clone was accessed.

- Impact: undocumented drift could make adoption unsafe.
- Required action: the database owner creates a verified backup and isolated sanitized clone, runs the read-only classifier, reviews every difference, rehearses upgrade and restore, and approves the migration. Never stamp the live schema based only on the synthetic result.

## High

### Uploaded-file malware controls and parser isolation are incomplete

Signature, size, quota, archive-expansion, malformed-file, retry, and ownership controls passed. Antivirus/CDR quarantine and a separately resource-limited parser sandbox are not implemented or tested.

- Mitigation: keep `UPLOADS_ENABLED=false` in production until the control is delivered and malicious-corpus testing passes.

### Zero-subject dashboard blocks normal settings navigation

Playwright reproduced this defect on desktop and Pixel 7. Direct `/settings` works, but the dashboard empty state masks the expected settings navigation/content.

- Impact: a new student without a subject cannot use the normal product path to settings.
- Required action: handle this in the authorized onboarding/product mission with its own accessibility and browser tests. It was intentionally not redesigned in STAGING-01.

### Real AI and embeddings providers are unverified

OpenRouter and remote OpenAI embeddings were disabled. Document tests used a deterministic local 1536-dimension provider specifically to avoid sending synthetic or student content outside the runner.

- Impact: provider authentication, model availability, latency, rate limits, error mapping, cost controls, and data-processing terms remain unproved.
- Required action: approved provider sandbox tests with non-sensitive fixtures, explicit egress/privacy review, budgets, retry/circuit-breaking, and observability before enabling `AI_ENABLED` or production embeddings.

### Production HTTPS/reverse-proxy behavior is unverified

The browser ran against loopback HTTP. CORS and Origin rules passed, and the refresh cookie was HttpOnly/SameSite=Lax; `Secure=false` was correct for that isolated HTTP origin. Nginx Proxy Manager, TLS, forwarded headers, and production-domain cookies were not exercised.

- Required action: verify on an isolated HTTPS staging domain/network without modifying production DNS or proxy configuration.

## Medium

### Email verification policy is unresolved

External OAuth requires verified provider email, but password registration can establish a session before email verification. Product/security owners must decide which study, upload, and purchase operations require verification and add route/browser enforcement.

### Access tokens remain JavaScript-readable

Refresh tokens are HttpOnly, but the short-lived access token remains in `sessionStorage`. Maintain CSP/XSS controls and evaluate a backend-for-frontend/HttpOnly design with explicit CSRF protection.

### Rate limiting is process-local

Counters are not shared across backend replicas and reset on restart. Move authentication and abuse controls to Redis before horizontal production scaling, with trusted-proxy tests.

### Publication semantics remain implicit

Ownerless embeddings are treated as platform material after subject entitlement; the current schema has no explicit draft/review/publish predicate at embedding level. Curriculum ingestion must define versioning and publication before editors upload real platform content.

### Frontend API URL is build-time immutable

`NEXT_PUBLIC_API_URL` is compiled into the Next.js image. A runtime-only environment change cannot retarget an existing image. Record image digest and API origin together and build a distinct image per approved environment.

### Python dependency resolution is not hash-locked

Direct versions are pinned, but there is no fully resolved hash-locked backend dependency set or SBOM. Create both in a clean build and verify `pip check`/`pip-audit`.

### Legal retention and erasure policy requires approval

Payment and audit rows are anonymized rather than simply deleted. Legal/privacy owners must approve categories, retention duration, user notice, and operational deletion SLA.

## Low

### CI maintenance warnings

GitHub warned that actions using Node.js 20 were being forced to Node.js 24. Update pinned action majors after compatibility review. Pytest also reported upstream deprecations and a harmless cache-permission warning inside the non-root backend image.

### Windows line-ending notices

The Windows checkout reports LF-to-CRLF conversion notices. `git diff --check` passes. Standardize with `.gitattributes` in a separate maintenance change if desired.

