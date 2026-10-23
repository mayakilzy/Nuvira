# NUVIRA STAGING-01 Verification Matrix

Status vocabulary: **PASS**, **FAIL**, **EXPECTED FAIL**, **NOT RUN**, **BLOCKED**. An expected failure means the defect was reproduced and Playwright treated that exact failure as the expected test outcome; it does not mean the product behavior works.

| Area | Verification | Status | Environment / command / evidence |
|---|---|---|---|
| Git | FOUNDATION-01 exact baseline and SECURITY-01 ancestry | PASS | `git merge-base --is-ancestor` for `433849f...` and `9cba55b...`. |
| Isolation | Static staging validator | PASS | `python3 scripts/staging/verify_isolation.py --env-file .env.staging`. |
| Isolation | Compose semantic validation | PASS | `docker compose ... config --quiet`; staging-specific images, limits, labels, resources. |
| Secrets | No committed staging secrets | PASS | Ephemeral random values created inside Actions; `.env.staging` not uploaded or committed. |
| Build | Backend production image | PASS | Docker multi-stage build completed. |
| Build | Frontend production build | PASS | `npm run build` in image; Next.js 16.3.8. |
| TypeScript | Static validation | PASS | Local `npx tsc --noEmit`; no diagnostics. |
| Runtime | PostgreSQL/pgvector health | PASS | Healthy `pgvector/pgvector:pg16`; `/health/db` returned `{"database":"ok"}`. |
| Runtime | Redis health | PASS | Healthy `redis:7-alpine`; internal-only port. |
| Runtime | FastAPI health | PASS | Healthy; `127.0.0.1:8800` only. |
| Runtime | Celery health | PASS | Healthy worker, concurrency 1, registered ping task. |
| Runtime | Next.js health and binding | PASS | Healthy; container port 3000 mapped only to `127.0.0.1:3300`. |
| Isolation | Database/Redis public exposure | PASS | No published DB/Redis ports in runtime inspection. |
| Isolation | Production network/volume reuse | PASS | Only `nuvira-foundation-staging_internal` and prefixed staging volumes. |
| Isolation | Resource limits | PASS | CPU, memory and PID limits required by validator for every service. |
| Migrations | Fresh upgrade chain | PASS | `0000_authoritative_schema -> 0001_lowercase_emails -> 0002_security_controls`. |
| Migrations | Current/check/idempotency | PASS | Head at `0002_security_controls`; `alembic check` clean; repeat upgrade passed. |
| Migrations | Fail-closed stale/missing revision | PASS | Backend regression suite plus legacy test before adoption. |
| pgvector | Extension and native vector use | PASS | Extension query returned `vector`; real PostgreSQL vector rows queried. |
| Legacy | Synthetic legacy classification | PASS | Compatible synthetic schema classified safe. |
| Legacy | Stamp acknowledgement guard | PASS | Stamp without `--acknowledge-backup` returned code 3. |
| Legacy | Data preservation and repeat upgrade | PASS | Synthetic user, subject, chapter and concept retained; email normalized; second upgrade clean. |
| Legacy | Incompatible schema rejection | PASS | Unexpected `unreviewed_data` column caused fail-closed rejection. |
| Legacy | Sanitized clone of actual production schema | BLOCKED | Requires database-owner backup/clone authorization; production was intentionally not accessed. |
| Auth | Registration/login/email normalization | PASS | Backend regression suite plus live HTTP/Playwright registration and invalid-login tests. |
| Auth | Refresh rotation and reuse-family revocation | PASS | Live HTTP suite and browser API flow. |
| Auth | Logout and password-reset revocation | PASS | Live HTTP suite. |
| Auth | Expired/tampered/wrong-purpose token rejection | PASS | Live expired token plus backend security regressions. |
| Auth | OAuth state, PKCE, one-time exchange, safe redirect | PASS | Backend security regression suite; no external OAuth provider enabled. |
| CORS/cookie | Origin restrictions | PASS | Evil origin rejected; approved loopback origin accepted. |
| CORS/cookie | HttpOnly refresh cookie and no URL credentials | PASS | Playwright desktop/mobile. HTTP staging used `Secure=false` by design on loopback HTTP. |
| Student isolation | Same-subject pgvector visibility | PASS | PostgreSQL test: B saw platform+B only, never A. |
| Student isolation | Private document listing | PASS | Live API/worker test: B received no A documents; unauthenticated request returned 401. |
| Student isolation | Embedding ownership | PASS | PDF/PPTX embeddings all retained A's user ID. |
| Student isolation | Direct subject/attempt tampering | PASS | Backend authorization regressions. |
| Billing | Client-provided credit quantity ignored | PASS | PostgreSQL event requested 999999; server pack granted 100. |
| Billing | Concurrent duplicate idempotency | PASS | Two concurrent deliveries produced one ledger row. |
| Billing | Invalid signature / refunded event | PASS | Invalid signature rejected; correctly signed refund granted no credits. |
| Billing | Live provider sandbox checkout/webhook | NOT RUN | Payments intentionally disabled; provider credentials absent. |
| Celery | Registration, ping, result backend | PASS | Real Redis/Celery integration, 1 passed. |
| Celery | Temporary broker outage recovery | PASS | Redis stopped/started; Redis and worker pings recovered. |
| Documents | Synthetic PDF and PPTX processing | PASS | Both reached `ready`, generated chunks, and produced owned embeddings. |
| Documents | Controlled transient retry | PASS | PPTX marker failed once then succeeded; `processing_attempts == 2`. |
| Documents | Unsupported/malformed/oversized rejection | PASS | HTTP responses 400/400/413. |
| Documents | Malware/CDR scanning and parser sandbox | NOT RUN | Capability is not implemented; uploads remain a production blocker. |
| Embeddings | Offline deterministic provider | PASS | Local SHA-256-derived 1536-dimension seam; no student data left the runner. |
| Embeddings | Real OpenAI embeddings | NOT RUN | Deliberately disabled; no external credential or student content used. |
| AI | Real OpenRouter companion integration | NOT RUN | Deliberately disabled and not a STAGING-01 success claim. |
| Browser | Desktop Chromium normal flows | PASS | Registration/session/settings/refresh/logout/error/URL/API-origin assertions. |
| Browser | Pixel 7 normal flows | PASS | Same flow on mobile emulation. |
| Browser | Zero-subject dashboard settings navigation | EXPECTED FAIL | Reproduced on desktop and mobile; error contexts preserved. Direct `/settings` remained accessible. |
| Browser | HTTPS reverse-proxy cookie behavior | NOT RUN | No DNS/TLS/proxy configured in the isolated local-origin run. |
| Backup | PostgreSQL dump checksum | PASS | SHA-256 preserved in artifact. |
| Restore | Separate database restore | PASS | Users/documents/embeddings counts 10/2/2; revision `0002_security_controls`. |
| Backup | Upload archive checksum and restore | PASS | Two files restored into a separately named staging volume. |
| Restore | Original stack remains healthy | PASS | Post-restore DB health returned `{"database":"ok"}`. |
| Production | Shared host/resources untouched | PASS | GitHub-hosted disposable runner; no production access. |

## Aggregate result

- Real PostgreSQL integration: 5 passed.
- Backend regression invocation: 36 passed, 9 skipped because those integration gates require dedicated runtime variables.
- The nine conditional tests: 5 PostgreSQL + 1 Celery + 2 HTTP auth + 1 HTTP documents, all passed in their dedicated invocations.
- Browser: six accepted outcomes across two projects; four normal passes and two explicit expected failures.
- Mandatory infrastructure gates: all passed.
- Production-product gates: remain blocked by the risks in `NUVIRA_STAGING_01_OPEN_RISKS.md`.
