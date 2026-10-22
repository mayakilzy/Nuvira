# Nuvira Feature Connection Matrix

Baseline: `db9fc4823ce65f08f9f770b8a32ac860de024587`

Mission: `NUVIRA-ONBOARDING-01`

## Status definitions

- `IMPLEMENTED_AND_VERIFIED`: implementation is present and relevant behavior was exercised by an isolated automated or read-only live check.
- `IMPLEMENTED_NOT_VERIFIED`: implementation is present, but its real dependencies or end-to-end behavior were not exercised.
- `PARTIALLY_CONNECTED`: some layers are connected, but a required transition, authorization rule, persistence contract or recovery path is absent.
- `BLOCKED`: the code path exists or is intended, but a known dependency or defect prevents safe use.
- `MISSING`: no implementation exists for the required capability.

Passing compilation is not treated as functional verification.

## Frontend → API → persistence matrix

| # | Capability | Frontend entry point | API and backend handler | Persistence | Authorization | Status | Evidence, gap and remediation |
|---:|---|---|---|---|---|---|---|
| 1 | Landing and pre-login language | `/`, `frontend/src/app/page.tsx` | None | None | Public | `MISSING` | Landing is predominantly German and has no locale control (`page.tsx:3-40`). Add server-readable locale cookie, translated public shell and locale-preserving auth links. |
| 2 | Registration | `/register`; `AuthProvider.register()` | `POST /auth/register`; `auth.register` | `users` | Public | `PARTIALLY_CONNECTED` | User creation and token return pass unit coverage for email normalization (`auth.py:53-63`; `test_auth_email.py`). No locale/onboarding/entitlement state is created; password policy is frontend-only. |
| 3 | Login and session restore | `/login`; `AuthProvider.refresh()` | `POST /auth/login`, `GET /auth/me`, `POST /auth/refresh` | Stateless JWT only | Public login; bearer for `/me` | `PARTIALLY_CONNECTED` | Login unit tests pass. Tokens are stored in local storage, refresh tokens rotate without server state, and logout cannot revoke them (`frontend/src/lib/api.ts:6-47`; `auth.py:81-97`). |
| 4 | Google OAuth | “Continue with Google” on `/login` | `GET /auth/google`, `GET /auth/google/callback` | `users.google_id`; JWT generated | Public callback | `BLOCKED` | Tokens are returned in the URL and OAuth state is not validated (`auth.py:148-175`; `oauth_service.py:15-25`). Replace with PKCE/state and a short-lived one-time exchange or secure server session. |
| 5 | Email verification | `/verify-email?token=...` | `GET /auth/verify-email/{token}` | `users.is_verified` | Purpose-scoped token | `PARTIALLY_CONNECTED` | Token expiry/type exists and updates the flag (`auth.py:101-111`; `core/tokens.py`). Registration/login/educational access do not enforce the flag; no resend endpoint or pending-verification state. |
| 6 | Password reset | `/forgot-password`, `/reset-password` | `POST /auth/forgot-password`, `POST /auth/reset-password` | `users.password_hash` | Purpose-scoped token | `IMPLEMENTED_NOT_VERIFIED` | Anti-enumeration response and one-hour token exist (`auth.py:114-144`). No direct tests, password policy, token jti/single-use storage or email-provider verification. |
| 7 | First-time onboarding | None | None | None | Authenticated | `MISSING` | No route, API, model or completion/version marker. Add resumable welcome and learning-path states that never hide settings/help. |
| 8 | Dashboard guard and initialization | Dashboard layout and `NuviraApp` | `GET /auth/me`; then subjects/preferences/session | User, preferences, avatar | Bearer | `PARTIALLY_CONNECTED` | Auth guard works structurally. Three startup calls are combined, so one failure can blank all initialization (`NuviraApp.tsx:104-112`). Split recoverable states and route first-time users to onboarding. |
| 9 | Empty dashboard | `NuviraApp` empty state | `GET /agent/subjects` | `user_subject_access` | Bearer | `BLOCKED` | Empty subjects override all embedded tabs and show only an administrator instruction (`NuviraApp.tsx:184-208`). Provide catalog/upload/settings/help/logout actions and keep app shell usable. |
| 10 | Interface language and RTL | Embedded Settings tab | `GET/PUT /agent/preferences` | `user_preferences` | Bearer, owner by current user | `PARTIALLY_CONNECTED` | Preference API and runtime `lang/dir` exist and are type-limited (`agent.py:193-236`; `NuviraApp.tsx:123-127`). Default is German, public/auth/billing screens are untranslated, and anonymous/authenticated synchronization is missing. |
| 11 | User profile/settings | Direct `/settings`; embedded account panel | `GET/PUT /user/profile`, `PUT /user/password`, `DELETE /user/account` | `users`; dependent data unspecified | Bearer | `PARTIALLY_CONNECTED` | Profile save is wired; password-change API has no frontend. Delete claims complete erasure but does not remove files/embeddings and may encounter non-cascading foreign keys (`user.py:25-55`; settings page:17-42). |
| 12 | Public curriculum catalog | None | None | `subject_packages` is insufficient catalog schema | Public/authenticated | `MISSING` | Existing `/agent/subjects` lists entitlements, not discoverable curricula. Add curriculum/system/level/version/publication/license metadata and catalog endpoints. |
| 13 | Subject enrollment | No entry point | No grant/enroll endpoint | `user_subject_access` | Should be student/service/admin with explicit policy | `MISSING` | No application write path exists. Define idempotent entitlement service and authorized grant sources; never write access directly from payment adapters. |
| 14 | Entitlement enforcement | Educational shell subject selector | `_require_subject_access()` used by subject resources | `user_subject_access` | Bearer; admin bypass | `IMPLEMENTED_AND_VERIFIED` | Unit tests prove an outsider receives 403 for chapters and attempts (`test_agent_access.py:58-98`). Model has no uniqueness, expiry, revocation, curriculum version or subscription reference. |
| 15 | Subscription catalog | `/pricing`, `/billing` | `GET /billing/plans` | `plans` | Public | `IMPLEMENTED_NOT_VERIFIED` | Route returns active plans in source and the frontend build succeeds, but no API request test or commercial plan/provider configuration was verified. Seeded generic SaaS plans are not approved Nuvira policy. |
| 16 | Checkout | `/billing` choose-plan button | `POST /billing/create-checkout-session` | Provider + later webhook | Bearer | `IMPLEMENTED_NOT_VERIFIED` | Provider adapters exist; no sandbox/live checkout was run. Interval is unvalidated and external errors are reflected to clients. |
| 17 | Credit-pack purchase | No current frontend entry point | `POST /billing/buy-credits` | Provider metadata, `credits_ledger` | Bearer | `BLOCKED` | Client supplies both provider price ID and awarded credits (`billing.py:49-61`), enabling underpayment/overgrant. Replace with server-owned pack IDs and server-side credit lookup. |
| 18 | Subscription renewal/expiry | Billing status display | `POST /billing/webhook`, `GET /billing/subscription` | `subscriptions`, `credits_ledger` | Signed webhook; bearer read | `PARTIALLY_CONNECTED` | Signature adapters and shared fulfillment exist. Stripe renewal parsing lacks a user mapping and plan in invoice events, so events can be ignored (`stripe_provider.py:77-81`; `base.py:122-143`). No tests or expiry-driven subject revocation. |
| 19 | Subscription → subject entitlement | None | None | Subscription and subject-access tables are unrelated | N/A | `MISSING` | Payment activation grants generic credits only. Define product/price-to-curriculum mapping and idempotent entitlement lifecycle after owner approves commercial policy. |
| 20 | Admin user management | `/admin/users` | `GET /admin/users`, `GET /admin/stats` | `users` | `require_admin` | `IMPLEMENTED_NOT_VERIFIED` | Server role guard exists and user UI is read-only (`admin.py:1-20`), but no dedicated admin request test was run. No activation, role, entitlement or content operation exists. |
| 21 | Curriculum publishing/admin content | None | None | Existing subject/chapter/concept tables | Admin required | `MISSING` | No create/update/publish/version/review endpoints or UI. Build an explicit draft→review→published workflow with audit records. |
| 22 | Subject selection | Dashboard header select (only if more than one) | `GET /agent/subjects` | `user_subject_access`, `subject_packages` | Bearer | `PARTIALLY_CONNECTED` | Entitled list and switching work in code. First item is silently auto-selected; choice/last subject is not persisted or deep-linked. |
| 23 | Chapters | Chapters tab | `GET /agent/chapters` | `chapters` | Subject access | `IMPLEMENTED_AND_VERIFIED` | Access and returned chapter are covered by unit test (`test_agent_access.py:65-86`). No uniqueness/order constraints or publishing state are evident. |
| 24 | Concepts | Chapter/concept UI | `GET /agent/concepts` | `concepts` | Subject access | `PARTIALLY_CONNECTED` | Endpoint explicitly returns `chapter_filter_applied: false`; concepts have no `chapter_id` (`agent.py:315-349`; `models/subject.py:39-50`). UI shows all subject concepts for every selected chapter. |
| 25 | Explanation/mechanism player | Concept detail in `NuviraApp` | Data included in `/agent/concepts` | `Concept.everyday_analogy`, `mechanism_json` | Subject access | `IMPLEMENTED_NOT_VERIFIED` | Rendering exists (`NuviraApp.tsx:202`); no seeded/current content was inspected and no browser E2E asserts it. Mechanism JSON lacks a documented schema/version. |
| 26 | Worked examples/quiz | No dedicated route; understanding buttons | `POST /agent/attempt` | `study_log` | Concept/subject access | `PARTIALLY_CONNECTED` | Self-reported “understood/review” persists attempts; there is no question bank, response evaluation or quiz generation. Do not label this as an assessed quiz. |
| 27 | Progress history | Garden and summary | `GET /agent/history` | `study_log`, `concepts` | Bearer; own user + subject gate when filtered | `IMPLEMENTED_NOT_VERIFIED` | Attempt recording is exercised indirectly by an access test, but the history endpoint and garden calculation have no direct automated or browser test in this audit. Progress counts distinct concepts with any successful attempt, not curriculum completion. |
| 28 | Spaced repetition | “Due for review” card | `GET /agent/review-queue` | `study_log` | Subject access | `IMPLEMENTED_NOT_VERIFIED` | Interval algorithm exists (`companion_service.py:124-201`). No tests cover due dates/time zones/large subjects and no scheduled notification system exists. |
| 29 | Avatar/session feedback | Workspace avatar | `POST /agent/session/start` | `avatar_state` | Bearer; own user | `IMPLEMENTED_AND_VERIFIED` | A concurrency regression test passes (`test_companion_session.py`). Session key is browser-generated on each mount, so remount semantics should be specified. |
| 30 | AI companion chat | Chat panel | `POST /agent/chat` | No conversation persistence; optional embeddings | Bearer + subject access if selected | `IMPLEMENTED_NOT_VERIFIED` | API invokes OpenRouter and optionally embeddings (`agent.py:147-190`). No real key call was run; no chat history, retry/backoff, credits, moderation or conversation isolation model exists. |
| 31 | Grounded retrieval | “Linked to material” badge | Embedding call + `search_scoped()` | `embeddings` | Subject access only | `BLOCKED` | Retrieval filters subject/chapter but not uploader. Personal chunks can cross students sharing a subject (`vector_service.py:47-64`). Apply visibility scope: platform content plus current user's private content. |
| 32 | Single-document upload | Materials tab file picker | `POST /agent/materials/upload` | `uploaded_documents`, filesystem volume | Bearer + subject access | `IMPLEMENTED_NOT_VERIFIED` | File is saved and task queued; status contract exists. No real worker run, and upload is unavailable before entitlement. Validation is extension-only. |
| 33 | Multiple-document/course/curriculum intake | Repeated manual single-file uploads only | No batch/course endpoints | No course/curriculum ingestion model | Bearer | `MISSING` | Add user-owned course container, multi-file manifest, atomic intake state and limits. Automatic hierarchy extraction needs review/edit before publication. |
| 34 | Processing status | Materials list and polling | `GET /agent/materials` | `uploaded_documents.status` | Subject access + uploader filter | `PARTIALLY_CONNECTED` | Polling/status/error note work structurally (`NuviraApp.tsx:114-121`; `agent.py:399-420`). No durable progress stages, timestamps, retryability or safe user-facing error codes. |
| 35 | Celery processing | No direct route | `process_uploaded_document_task` | Documents, embeddings, uploads | Internal worker | `IMPLEMENTED_NOT_VERIFIED` | Task exists but has no retry policy; document service commits chunks individually. Redis/Celery/OpenAI path was not run (`workers/tasks.py:19-29`). |
| 36 | Material retry/replace/delete | None | None | Existing documents/files/embeddings | Owner required | `MISSING` | Required for recovery and privacy. Implement ownership checks, idempotent cleanup and audit records. |
| 37 | Cross-student document isolation | Materials list | `GET /agent/materials` | `uploaded_documents` | Uploader filter | `PARTIALLY_CONNECTED` | List metadata is correctly uploader-filtered (`agent.py:399-420`), but RAG search is not, so end-to-end isolation fails. |
| 38 | Error recovery | Alerts/status labels | Various | Varies | Varies | `PARTIALLY_CONNECTED` | Errors are visible but usually dismiss-only. Add localized retry/help/back actions, stable error codes and partial-load handling. Do not display raw worker/provider exceptions. |
| 39 | Logout | Settings/account links | `POST /auth/logout` exists but frontend does not call it | No token/session record | Bearer not required | `PARTIALLY_CONNECTED` | Frontend only clears local storage (`auth.tsx:41`); backend logout is a no-op (`auth.py:95-97`). Introduce server-managed refresh sessions and revocation. |
| 40 | Account lifecycle | `/settings` delete | `DELETE /user/account` | User plus dependent tables/files | Bearer | `BLOCKED` | Complete deletion is neither transactional nor demonstrated; uploads and embeddings persist and foreign-key behavior is incomplete. Define deletion/export/retention policy and test it. |

## Security regression matrix

| Area | Test/source evidence | Result |
|---|---|---|
| Case-insensitive email identity | Four tests in `test_auth_email.py` | PASS |
| Subject/chapter/concept access | `test_agent_access.py` | PASS for enrolled vs non-enrolled users |
| Attempt cross-subject access | `test_agent_access.py` | PASS |
| Document embedding insert scope | `test_embedding_scope.py` | PASS for stored scope columns |
| Document retrieval user isolation | No test; query lacks user filter | FAIL by static trace |
| OAuth token redirect regression | Direct source trace | FAIL — vulnerability remains |
| OAuth state/PKCE | Direct source trace | FAIL — absent |
| Admin role enforcement | `require_admin` source; no dedicated request test | IMPLEMENTED_NOT_VERIFIED |
| Webhook signature handling | Provider source; no tests | IMPLEMENTED_NOT_VERIFIED |
| Credit-pack server pricing | Direct source trace | FAIL — client controls credit grant |
| Refresh revocation/logout | Direct source trace | MISSING |
| Production-secret fail-closed validation | Direct source trace | MISSING |
| Dependency vulnerability posture | GitHub Dependabot API: 54 open alerts (5 critical/26 high/19 medium/4 low); critical `python-jose` and Next.js advisories | BLOCKED |

## Database and deployment connection matrix

| Concern | Repository state | Result |
|---|---|---|
| Initial schema migration | Only `0001_lowercase_emails`; assumes `users` exists | BLOCKED — fresh Alembic upgrade fails |
| Runtime schema | `Base.metadata.create_all()` at startup | Works around initial creation but is not a migration strategy |
| Migration errors | Startup catches and prints schema/seed errors | Service may start in a partially initialized state |
| Worker healthcheck | Absent from repository Compose | Reconcile verified server correction: `celery inspect ping` |
| Frontend bind address | `HOSTNAME=0.0.0.0` absent | Reconcile verified server correction |
| Network isolation | DB/Redis/worker internal; frontend/backend also on proxy; no host ports | Static configuration PASS |
| Fresh Docker runtime | Docker unavailable on audit host | NOT RUN |

## Test coverage conclusion

The current 11-test suite provides useful narrow regressions but does not verify a complete student journey. It has no tests for onboarding, catalog, enrollment writes, OAuth callback security, email-verification policy, password reset, billing/webhooks, credits race safety, personal-content retrieval isolation, upload API, Celery retry/recovery, account deletion, frontend behavior, accessibility, RTL screenshots or browser E2E.
