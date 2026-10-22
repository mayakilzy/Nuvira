# NUVIRA FOUNDATION-01 Verification Matrix

Result vocabulary: **PASS**, **FAIL**, **BLOCKED**, **NOT RUN**.

| Workstream | Requirement | Implementation evidence | Test evidence | Result | Limitation / next action |
|---|---|---|---|---|---|
| Migration | One deterministic history | 0000 → 0001 → 0002 | `alembic history`, one head | PASS | PostgreSQL execution still required |
| Migration | Fresh initialization | Explicit 18-table baseline plus security migration | Empty SQLite upgrade reaches head; repeated upgrade passes | PASS locally | PostgreSQL/pgvector NOT RUN |
| Migration | pgvector before embeddings | 0000 creates extension first on PostgreSQL | Conditional integration test exists | NOT RUN | Run on pgvector/pg16 |
| Migration | No metadata drift | 0002/model indexes and nullability aligned | `alembic check`: no operations | PASS on SQLite | Repeat on PostgreSQL |
| Adoption | Classify schema safely | Read-only adoption CLI | fresh, compatible legacy, incompatible tests | PASS | Production-like clone not inspected |
| Adoption | Preserve populated relationships | Stamp baseline then upgrade | Synthetic user/subject/chapter/concept preserved | PASS on SQLite | Repeat on restored PostgreSQL clone |
| Adoption | Duplicate email safety | Existing abort retained | Interruption, correction, retry test | PASS | Owner must decide actual duplicate resolution |
| Adoption | Reject unknown schema | Exact table/column/type/FK/index gate | Unexpected column test | PASS | PostgreSQL introspection still required |
| Startup | No create-all in managed env | Revision guard for staging/production | Staging-mode native startup accepted migrated DB; guard negative tests | PASS | Docker startup NOT RUN |
| Docker | Worker healthcheck | Deterministic worker hostname and inspect ping | Static review/YAML parse | BLOCKED | Docker CLI absent |
| Docker | Frontend bind | `HOSTNAME=0.0.0.0` in both Compose files | Static review | BLOCKED | Container loopback/network checks not run |
| Docker | Five services healthy | Isolated staging Compose | Not executed | BLOCKED | Run staging guide on Docker host |
| Isolation | Separate names/volumes/network/images | `docker-compose.staging.yml`, staging env | Positive/negative isolation unit tests | PASS statically | Runtime labels/resources need Docker proof |
| Isolation | No production URL fallback | Staging build args and localhost Next fallback | Source scan/build | PASS | Browser network assertion blocked |
| PostgreSQL | Session/OAuth/security tables persist | 0002 and conditional suite | Three PostgreSQL tests skipped | NOT RUN | No PostgreSQL runtime |
| RAG | Cross-student pgvector isolation | Conditional PostgreSQL test | Skipped | NOT RUN | Run with two synthetic students |
| Billing | Concurrent event idempotency | Unique event constraint and threaded PostgreSQL test | Skipped | NOT RUN | Real PostgreSQL concurrency required |
| Redis/Celery | Registration, ping, result backend | Conditional live-worker test | Skipped | NOT RUN | Redis/worker unavailable |
| Documents | Worker retry/cleanup | SECURITY-01 bounded tasks | Unit tests only | NOT RUN integrated | Requires worker + mocked embeddings + synthetic file |
| Authentication | Unit regression | SECURITY-01 plus configuration tests | Included in 36 passes | PASS locally | Proxy/cookie/browser E2E pending |
| Frontend | Type/build | Playwright source plus patched Next build | TypeScript PASS; build PASS, 14 routes | PASS |
| Browser | Required auth journey | `foundation-auth.spec.ts` | Test discovery PASS; execution blocked before browser opened | BLOCKED | Increase Windows paging file or run CI Chromium |
| Backup/restore | Rehearsed isolated restore | Procedures documented | Not executed | NOT RUN | Docker/PostgreSQL required |
| Production safety | No production action | Separate local branch/resources | Git/source audit | PASS | Owner-controlled inspection remains future work |

## Exact local results

- Backend: `36 passed, 4 skipped in 18.78s`.
- Skips: three PostgreSQL/pgvector cases and one Redis/Celery case.
- Frontend production build: PASS, Next.js 16.3.8, 14 routes.
- npm audit: PASS, 0 vulnerabilities.
- pip-audit: PASS for direct pinned requirements; no known vulnerabilities, with the documented transitive-lock limitation.
- Compose YAML parsing: PASS; Docker Compose semantic/runtime validation: BLOCKED.
- Playwright: one test discovered; Chrome/Edge execution BLOCKED by host memory/paging failure.
