# NUVIRA SECURITY-01 Verification Matrix

Result vocabulary: **PASS**, **FAIL**, **NOT RUN**, **BLOCKED**.

| Finding | Severity | Root cause | Implemented control | Evidence | Result / limitation |
|---|---:|---|---|---|---|
| Vulnerable JWT/dependencies | Critical | Old `python-jose` and outdated web/parser packages | PyJWT strict verification; patched package set and lockfile | JWT negative tests; pip-audit; npm audit; frontend build | **PASS** locally. Python audit is direct pinned requirements with `--no-deps`, not a hashed transitive lock. |
| Tokens in OAuth callback URL | Critical | Callback serialized access and refresh tokens | One-time opaque exchange code; refresh cookie | `test_oauth_state_pkce_single_use_and_no_bearer_in_redirect` | **PASS** |
| Missing OAuth CSRF/replay protection | Critical | No durable validated state | Hashed expiring one-use state plus PKCE S256 | valid, invalid, missing, expired, replay and unsafe return tests | **PASS** |
| OAuth account takeover/linking | Critical | Email match could link unrelated provider identity | Verified identity required; provider-ID/email consistency; password account conflict | provider failure/unverified identity and cross-account tests | **PASS** with mocked provider. Real Google sandbox **NOT RUN**. |
| Long-lived browser refresh credential | High | Refresh token was exposed to JavaScript storage | Opaque HttpOnly cookie; hashed DB session; legacy local-storage removal | rotation/reuse/logout/reset tests and frontend build | **PASS**. Short-lived access token remains in `sessionStorage`; XSS risk remains. |
| Refresh replay/logout | Critical | Stateless refresh and local-only logout | Rotation, family reuse detection, server revocation | refresh rotation/reuse/logout/reset tests | **PASS** |
| Cookie CSRF | High | Cookie mutations lacked origin binding | Production Origin allowlist; SameSite cookie | code inspection and auth tests | **PASS** at unit level; browser/proxy E2E **NOT RUN**. |
| Cross-student RAG disclosure | Critical | Retrieval scoped by subject but not owner | DB query restricts platform or current owner; missing user fails closed | RAG isolation test plus existing entitlement tests | **PASS** with synthetic SQLite. PostgreSQL/pgvector integration **NOT RUN**. |
| Prompt injection from uploaded content | High | Retrieved text could be interpreted as control instructions | Prompt labels retrieved text untrusted; uploads off by default | code inspection and compile/tests | **PASS** for instruction boundary; adversarial model eval **NOT RUN**. |
| Client-controlled credit quantity/price | Critical | Browser could submit price and credit quantity | Server-owned active pack/plan lookup; only slug accepted | manipulated quantity, duplicate event, unknown-plan tests | **PASS** locally |
| Duplicate webhook fulfillment | Critical | Ledger lookup alone was not a concurrency boundary | Unique provider/event row claimed before fulfillment | duplicate-delivery test and migration unique constraint | **PASS** sequentially; real concurrent PostgreSQL stress **NOT RUN**. |
| Invalid webhook signature/failed payment | Critical | Must rely on provider adapters | Adapter verification retained; only normalized success types fulfill | code inspection; payments disabled by default | Provider sandbox vectors **NOT RUN**. Unsafe route remains disabled unless explicitly configured. |
| Unsafe production defaults | Critical | Placeholder secrets/debug/admin bootstrap | Production model validation and opt-in integrations | `test_security_config.py` | **PASS** |
| Incomplete account deletion | High | No end-to-end cleanup/status lifecycle | Disable/revoke, tracked cleanup, retry, removal/anonymization | deletion failure/retry and other-user/shared preservation test | **PASS** locally. Legal retention policy still owner/legal work. |
| Forged/oversized/archive uploads | High | Extension trust and unbounded parsing | Streaming quotas, signatures, PPTX archive limits, bounded retry | forged PDF/legacy PPT test and code inspection | **PASS** for tested vectors. Oversize/archive-bomb integration and malware scan **NOT RUN**. |
| Spoofed forwarded IP/rate-limit abuse | High | Arbitrary XFF trust and process-local counters | Trusted-proxy allowlist and auth-specific limit | code inspection and unit suite | **PASS** for parsing; distributed rate limiter **NOT IMPLEMENTED**. |
| Additive security migration | High | New durable security state requires schema | Revision `0002_security_controls` | simulated existing-schema migration test | **PASS** against stamped disposable schema. |
| Fresh database migration | Critical deployment blocker | Repository migration history starts after base tables already exist | Deferred to FOUNDATION-01; production `create_all` removed | empty SQLite `alembic upgrade head` | **FAIL**: `no such table: users`. Deployment blocked. |
| Docker/Redis/Celery worker | High integration risk | Required runtime unavailable on audit host | Compose isolation/healthcheck prepared; bounded tasks | attempted `docker compose config` | **BLOCKED**: Docker command not installed. |
| Browser auth/responsive flow | Medium | No browser E2E harness executed in this mission | Frontend compiled and statically generated | TypeScript/build | **NOT RUN** for E2E. |

## Command evidence

| Suite | Environment | Command | Result |
|---|---|---|---|
| Backend unit/security | Windows, Python 3.11.0, SQLite/mocks | `cd backend && python -m pytest -q` | **PASS** — 27 passed in 6.88s |
| Python bytecode | same | `python -m compileall -q app tests alembic` | **PASS** |
| Python advisories | pip-audit 2.10.1, advisory network enabled | `python -m pip_audit -r requirements.txt --no-deps --disable-pip --progress-spinner off` | **PASS** — no known vulnerabilities; scope caveat above |
| Frontend advisories | Node 22.19.0, npm 10.9.3 | `npm audit --json` | **PASS** — 0 total |
| TypeScript | frontend dependency lock | `npx tsc --noEmit` | **PASS** |
| Production build | `NEXT_PUBLIC_API_URL=https://api.nuvira.agentcraft.info` | `npm run build` | **PASS** — Next 16.3.8, 14 routes |
| Additive migration | disposable SQLite schema stamped at 0001 | included in pytest | **PASS** |
| Fresh migration | empty disposable SQLite file | `python -m alembic upgrade head` | **FAIL** at existing 0001 |
| Docker configuration/runtime | local host | `docker compose config` | **BLOCKED** — CLI unavailable |
| PostgreSQL/Redis/Celery/provider/browser integration | isolated services unavailable | not executed | **NOT RUN** |
