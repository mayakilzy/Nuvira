# NUVIRA STAGING-01 Deployment Readiness

## Readiness decision

| Target | Decision | Reason |
|---|---|---|
| Isolated engineering staging | **READY, with controls below** | All mandatory STAGING-01 real-infrastructure gates passed on a disposable five-service stack. |
| Shared production host staging | **NOT AUTHORIZED / NOT ASSESSED** | Host capacity, collision analysis, and owner approval were not obtained; GitHub-hosted isolation was used instead. |
| Production deployment | **NOT READY** | Dependency vulnerability disposition, real-schema rehearsal, malware/parser controls, HTTPS proxy proof, provider validation, and onboarding defect remain open. |
| Merge to `main` | **NOT AUTHORIZED** | Mission explicitly forbids automatic merge; external review and owner decision are required. |

## What is ready for isolated staging

- Staging-only Compose with PostgreSQL/pgvector, Redis, FastAPI, Celery, and Next.js.
- Separate network and PostgreSQL/Redis/upload named volumes.
- Resource limits and worker concurrency 1.
- Database/Redis not published; application ports loopback-only.
- Fresh authoritative migrations and fail-closed revision guard.
- Synthetic legacy classification/adoption safeguards.
- Cross-student PostgreSQL/pgvector isolation and live document ownership.
- Authentication rotation, reuse detection, revocation, Origin controls, and browser cookie/URL boundaries.
- Server-owned credit packs and concurrent payment idempotency using local fixtures.
- Real Redis/Celery tasks, document retry, and broker recovery.
- Desktop/mobile Playwright reporting with the zero-subject defect explicitly expected.
- Disposable database/upload backup and separate restore rehearsal.

## Conditions for the next isolated staging deployment

1. Use a dedicated host or obtain explicit owner approval after CPU, memory, disk, port, volume, network, and image collision review.
2. Create new staging-only random database/JWT/admin values; never reuse CI or production secrets.
3. Run the isolation validator and `docker compose config` before startup.
4. Keep OAuth, payments, email, AI, external embeddings, first-admin, and uploads disabled initially.
5. Build the frontend with the exact staging `PUBLIC_API_URL`; record that URL with the image digest.
6. Bind application ports to loopback unless an explicitly isolated staging proxy network is approved. Do not attach to the production proxy network by assumption.
7. Run the same workflow gates against the candidate image/configuration and retain the evidence.
8. If uploads are enabled for testing, use only synthetic files and the deterministic local provider until malware/parser isolation is remediated.
9. Preserve backups by default. Use scoped `down` without `--volumes`; destructive staging-volume removal needs a separate exact-target review.

## Required production gates

Production approval requires all of the following, none inferred from this report:

- Triage and remediation/acceptance of the critical npm finding and relevant Dependabot/image/backend findings.
- Verified production backup plus successful upgrade/restore rehearsal on an isolated sanitized clone of the actual schema and files.
- Antivirus/CDR and parser resource isolation for uploads, or uploads kept disabled by an approved product decision.
- Isolated HTTPS staging proof for Nginx/proxy headers, secure cookies, CORS, redirects, and production-domain configuration.
- Approved OpenRouter/embedding configuration with privacy, egress, model, cost, timeout, retry, and failure-mode tests; otherwise AI remains disabled.
- Approved payment-provider sandbox proof before payments are enabled.
- A decision and enforcement tests for password-account email verification.
- Resolution of the zero-subject dashboard/settings navigation defect before student-product launch.
- Explicit platform-content publication/version semantics before real curriculum ingestion.
- Production environment-variable inventory, secret-store procedure, image digests, rollback owner, monitoring, and maintenance window.
- Independent engineering review and explicit authorization to merge/deploy.

## Rollback boundary

The staging rehearsal proves that a PostgreSQL custom-format dump and upload tar can be checksummed and restored to separate disposable targets while the original stack stays healthy. It does not prove a production RTO/RPO or authorize an in-place production restore.

For production, rollback must use pre-change database and upload backups, immutable image digests, the prior environment inventory, and a rehearsed decision tree. Schema rollback should prefer restoring the verified backup into a separate target and switching only after validation; do not improvise destructive downgrade SQL on the live database.

## Final recommendation

Proceed to a separately authorized isolated staging environment after dependency triage. Do not deploy to production and do not merge automatically. The infrastructure foundation is verified; the remaining risks are product, supply-chain, provider, proxy, and production-data gates rather than missing proof that the five-service secured foundation can run.
