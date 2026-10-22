# Nuvira Onboarding Audit

Mission: `NUVIRA-ONBOARDING-01`

Audit date: 2026-10-22

Repository: `https://github.com/mayakilzy/Nuvira`

Source baseline: `db9fc4823ce65f08f9f770b8a32ac860de024587` (`origin/main`)

Audit branch: `audit/nuvira-onboarding-01`

## 1. Executive assessment

Nuvira contains a functional authenticated learning workspace, but it does not contain a student onboarding or curriculum-acquisition flow. Registration creates a user and immediately redirects to `/dashboard`; it does not create preferences, record onboarding state, enroll the student, grant a trial, or offer a catalog. The dashboard then asks `GET /agent/subjects`, which returns only rows already present in `user_subject_access`. A new student therefore reaches a dead end unless an administrator changes the database outside the application.

The original vision is not currently achievable without manual intervention:

> register → select language → choose platform curriculum or upload personal material → begin learning

The implemented flow is instead:

> register → receive tokens → dashboard → no entitled subject → administrator instruction with no in-product action

The application is online and its database health endpoint responds successfully, but production health does not prove onboarding, payment, AI, or ingestion behavior. The current source is suitable as an implementation baseline, not as a production-complete commercial student journey.

## 2. Audit method and evidence

### Repository preparation

- Remote verified as `https://github.com/mayakilzy/Nuvira.git`.
- `git fetch origin --prune` completed successfully.
- Local `main` and `origin/main` both resolved to `db9fc4823ce65f08f9f770b8a32ac860de024587`.
- Ahead/behind before branching: `0/0`.
- Working tree was clean.
- The audit branch was created directly from `origin/main`.
- A remote Dependabot branch exists but does not alter this audit baseline.

### Non-destructive verification performed

| Check | Result |
|---|---|
| Backend suite: `DATABASE_URL=sqlite://; python -m pytest -q` | PASS — 11 tests, 3.55 seconds; one non-failing pytest-asyncio deprecation warning |
| TypeScript: `tsc --noEmit` | PASS — no diagnostics |
| Frontend production build with production API URL | PASS — 14 static routes generated |
| Fresh Alembic database: `DATABASE_URL=sqlite://; python -m alembic upgrade head` | FAIL — `no such table: users` |
| Public frontend `HEAD https://nuvira.agentcraft.info/` | PASS — HTTP 200 |
| Public API `GET /health` | PASS — `Nuvira`, `production` |
| Public API `GET /health/db` | PASS — `database: ok` |
| Authenticated production journey | NOT RUN — would require creating or using production student data |
| OpenRouter and embedding calls | NOT RUN — external credentials/paid services required |
| Redis/Celery document completion | NOT RUN — no isolated Docker runtime on the audit host |
| Browser E2E | NOT RUN — no Playwright/Cypress suite exists |

The public checks were read-only. No account was created and no production data, containers, volumes, proxy configuration, DNS, certificates, or environment secrets were touched.

## 3. Current onboarding behavior

### Registration and first login

1. `/register` submits email, password and name to `POST /auth/register` and unconditionally routes successful requests to `/dashboard` (`frontend/src/app/register/page.tsx:13-17`).
2. The backend normalizes the email, creates a `User`, attempts a verification email, returns access and refresh tokens, and does not create any other student state (`backend/app/routers/auth.py:53-63`).
3. Email verification is not required by login or by educational routes. `is_verified` is returned by `/auth/me`, but neither `login()` nor `get_current_user()` rejects unverified users (`backend/app/routers/auth.py:66-74`; `backend/app/core/deps.py:13-30`).
4. There is no onboarding route, onboarding model, `onboarding_completed_at`, onboarding version, initial language field on registration, or first-login transition.

### Dashboard initialization

`NuviraApp` starts three requests in parallel: entitled subjects, authenticated preferences and avatar-session initialization (`frontend/src/components/nuvira/NuviraApp.tsx:104-112`). Preferences default to German in the database (`backend/app/models/preferences.py:11-18`) and the root HTML also defaults to German (`frontend/src/app/layout.tsx:11-16`), despite the approved requirement that English be the default.

`GET /agent/subjects` joins `subject_packages` to `user_subject_access` for non-admin users (`backend/app/routers/agent.py:117-137`). Registration never inserts `UserSubjectAccess`, and no production API inserts it. The only constructor usage outside the model is in a test fixture.

When the returned subject collection is empty, `NuviraApp` renders a single empty state instead of the selected tab content (`frontend/src/components/nuvira/NuviraApp.tsx:184-208`). The sidebar and mobile navigation can change `tab`, but the outer `!subjects.length` condition continues to win. Consequently the embedded Settings tab, language control, account links and chat remain visually inaccessible. Direct `/settings` and `/billing` routes still exist, but the empty state does not link to them.

The empty state instructs the student to ask an administrator for access (`frontend/src/components/nuvira/NuviraApp.tsx:186`). There is no call to action for curriculum browsing, personal-course creation, upload, support, settings, or logout.

## 4. State-transition analysis

### Current state machine

| State | Entry condition | Available transition | Failure |
|---|---|---|---|
| Anonymous | No local token | Login/register/pricing | No language selection or anonymous preference persistence |
| Registered, unverified | Successful registration | Automatic dashboard redirect | Verification is optional in practice and no verification reminder appears |
| Authenticated, no entitlement | `/agent/subjects` returns empty | None in product | Dead end requiring administrator/database intervention |
| Authenticated, entitled | At least one `UserSubjectAccess` | First subject auto-selected | No catalog or explicit subject-choice onboarding |
| Subject loaded | Five subject requests succeed | Garden, chapters, materials, chat, settings | One rejected request makes the combined load fail; partial successes are hidden |
| Upload processing | Upload accepted and Celery task queued | Poll every three seconds | No cancel, retry, replace or delete action |
| Returning student | Tokens remain in `localStorage` | `/auth/me`, dashboard | No onboarding-version check, last subject/chapter restoration or safe refresh-token revocation |

### Required target state machine

| State | Required transition |
|---|---|
| Anonymous | Choose `en`, `ar` or `de`; persist locally/cookie; keep selection through auth links |
| Registration/login complete | Exchange or establish secure session; synchronize anonymous language preference to the user profile |
| Verification pending | Explain status, allow resend/change email/logout, enforce the owner-approved verification policy |
| First authenticated visit | Welcome, explain Nuvira, let the student skip/back, then choose a learning path |
| No curriculum selected | Show curriculum library and personal-material path while keeping settings/help/account available |
| Curriculum selected, entitlement required | Show access terms; invoke an owner-approved free, trial, purchase or gift flow |
| Entitlement active | Open subject overview and explicit first chapter/concept action |
| Personal material selected | Create a user-owned course/subject container before upload; show processing and recovery states |
| First learning success | Persist attempt/progress; mark onboarding complete only after a meaningful educational interaction |
| Returning student | Resume last accessible subject/chapter or show a recoverable state if access expired/content changed |

## 5. Internationalization and RTL

Status: `PARTIALLY_CONNECTED`.

Positive evidence:

- The educational shell has English, Arabic and German dictionaries (`NuviraApp.tsx:21-25`).
- Authenticated preferences validate `de`, `en` and `ar` (`backend/app/routers/agent.py:193-236`).
- The workspace updates `<html lang>`, `<html dir>` and theme after preferences load (`NuviraApp.tsx:123-127`).
- CSS uses several logical properties such as `border-inline-end` and `inset-inline-end`.

Blocking gaps:

- The public landing page is predominantly German and has no language control (`frontend/src/app/page.tsx:3-40`).
- Root HTML defaults to `lang="de"`, not English (`frontend/src/app/layout.tsx:13`).
- Login, registration, password reset, email verification, pricing, billing, profile and admin pages are hardcoded in English.
- Several educational strings remain hardcoded in German or English even when Arabic is selected, including brand subtitle, garden note, concept labels, upload settings and account links (`NuviraApp.tsx:178`, `200`, `202`, `204`, `206`).
- Anonymous choice is not stored in a cookie or local storage and is not sent during registration.
- No framework-level locale routing or centralized message catalog exists.
- RTL is applied after authenticated preferences load, so Arabic users initially receive German/LTR markup and may see a direction flash.

Recommended synchronization contract:

1. Store anonymous locale in a first-party cookie usable during server rendering, with local storage only as a convenience mirror.
2. Pass the locale explicitly through registration/login/OAuth state.
3. On first authenticated session, copy the anonymous choice to `UserPreferences` only if the user has not made an authenticated choice.
4. Thereafter treat authenticated preferences as authoritative and refresh the cookie after each change/logout as appropriate.
5. Keep interface locale separate from `SubjectPackage.language`; the current model already supports this separation.

## 6. Curriculum paths

### Path A — platform curriculum library

Status: `MISSING`.

`SubjectPackage` stores only name, university, language, price and review status (`backend/app/models/subject.py:13-25`). It lacks a curriculum hierarchy, country/system, academic level, grade/track, edition/version, publication state, licensing metadata, cover/description, preview policy and availability window.

The only subject endpoint lists subjects already entitled to the current user. It is not a public or authenticated catalog. No enrollment, checkout-to-subject mapping, entitlement grant, entitlement expiry/revocation, preview or publishing endpoint exists. The admin API can only list users and count them (`backend/app/routers/admin.py:11-20`).

The planned Syrian Scientific Baccalaureate Mathematics journey therefore cannot be configured or purchased through Nuvira today.

Before commercial publication, the owner must document:

- Rights to digitize, process, display and generate derivative explanations from the supplied textbook.
- Territory, term, audience and redistribution limits.
- Official curriculum year, textbook edition, track and language.
- A content checksum/version identifier and a review/sign-off record.
- A takedown/correction/version-retirement process.

No textbook was downloaded, fabricated, ingested or published during this audit.

### Path B — personal material upload

Status: `PARTIALLY_CONNECTED`.

Implemented:

- One PDF/PPT/PPTX file per request, maximum 50 MB by byte length (`backend/app/routers/agent.py:353-396`).
- Optional association to an existing chapter.
- User-owned document metadata and status.
- Celery task dispatch, PDF/PPTX text extraction, chunking and embeddings (`backend/app/services/document_service.py:11-70`; `backend/app/workers/tasks.py:19-29`).
- UI polling while documents are processing (`NuviraApp.tsx:114-121`).

Not implemented or blocked:

- Upload requires entitlement to an existing platform subject, so a student with no subject cannot use Path B.
- No create-personal-subject/course/curriculum operation exists.
- The browser supports one selected file per action; repeated uploads are possible but batch semantics are absent.
- No automatic chapter/concept structure generation exists.
- `.ppt` is accepted but `python-pptx` does not support legacy binary `.ppt` reliably.
- No delete, replace, retry, cancel, reprocess or download endpoint exists.
- No content-type/magic-byte verification, archive-bomb mitigation, malware scanning, per-user quota or storage quota exists.
- Worker retries/backoff and transactional cleanup are absent; partial embeddings may remain after a failure because each chunk is committed separately.
- Raw exception text is persisted and returned to the uploader.
- Actual Redis/Celery/OpenAI processing was not executed in this audit.

## 7. Educational experience

| Capability | Assessment |
|---|---|
| Entitled subject selection | Implemented; first entitled subject is selected automatically |
| Chapter navigation | Implemented but concepts cannot be filtered by chapter |
| Concepts and explanations | Stored analogies/mechanism JSON are rendered |
| Worked examples | No dedicated model or workflow |
| Progress | Successful attempt count and study log are persisted |
| Spaced repetition | Basic confidence intervals and due queue exist |
| AI companion | API contract exists; real OpenRouter call not verified in this audit |
| Conversation memory | Missing; only current browser component state exists |
| Avatar | Persisted shape/color; implementation is operational under unit coverage for one race case |
| Grounding | RAG code exists, but real embeddings were not verified and user isolation is unsafe as described below |
| Quiz/exam generation | Missing; buttons record self-reported understanding rather than assess generated answers |
| Error recovery | Partial; errors display but many lack retry/help/rollback actions |

## 8. Security and privacy findings

| Severity | Finding | Evidence and consequence |
|---|---|---|
| CRITICAL | Client-controlled credit quantity | `POST /billing/buy-credits` accepts arbitrary `price_id` and `credits` (`backend/app/routers/billing.py:49-61`). Providers echo both into signed metadata and fulfillment grants the supplied amount. A cheap valid price could be paired with an arbitrary credit quantity. |
| HIGH | OAuth access and refresh tokens in redirect URL | Backend redirects to `/login?access_token=...&refresh_token=...` and frontend reads them (`backend/app/routers/auth.py:173-175`; `frontend/src/app/login/page.tsx:16-21`). Tokens can reach browser history, logs, screenshots and referrers. The previously reported vulnerability still exists. |
| HIGH | OAuth login-CSRF/state protection absent | Consent URL defaults `state` to an empty string and callback does not accept or validate state (`backend/app/services/oauth_service.py:15-25`; `backend/app/routers/auth.py:155-175`). |
| HIGH | Cross-student uploaded-content exposure in RAG | Upload embeddings record `user_id`, but `search_scoped()` filters only subject/chapter (`backend/app/services/vector_service.py:47-64`). Two students entitled to the same subject can retrieve each other's uploaded chunks through chat. Existing tests verify insert scoping, not query isolation. |
| HIGH | Production does not fail closed on default auth/admin secrets | Defaults include `JWT_SECRET=CHANGE_ME_IN_PRODUCTION` and `FIRST_ADMIN_PASSWORD=ChangeMe123!`; no production startup validation rejects them (`backend/app/config.py:26-30`, `70-72`). |
| HIGH | Account deletion does not define complete erasure | The route deletes only the user row (`backend/app/routers/user.py:51-55`). Several dependent models lack cascade policy, and uploaded files/embeddings are not deleted. The UI promises all data will be removed (`frontend/src/app/(dashboard)/settings/page.tsx:39-42`) without implementation evidence. |
| MEDIUM | Tokens stored in local storage; logout is not server-side | Both long-lived refresh and access tokens use `localStorage`; logout only removes them client-side (`frontend/src/lib/api.ts:6-15`; `frontend/src/lib/auth.tsx:41`). No rotation, token family, revocation or reuse detection exists. |
| MEDIUM | Email verification is advisory | Registration grants tokens before verification; authenticated dependencies ignore `is_verified`. A failed/missing mail configuration does not stop registration. |
| MEDIUM | Password rules and credential rate limits are insufficient | Backend accepts any password string. Rate limiting is a process-local per-IP list and does not use Redis (`backend/app/core/ratelimit.py:20-39`); behind a proxy it may see the proxy address unless trusted forwarding is configured. |
| MEDIUM | Upload validation is extension-only | No MIME/magic-byte validation, scanning or decompression safeguards; the entire upload is read into memory (`backend/app/routers/agent.py:366-379`). |
| MEDIUM | Internal/provider error detail is exposed | Checkout exceptions include provider text in API errors; upload `error_note` exposes truncated internal exceptions (`backend/app/routers/billing.py:42-45`; `NuviraApp.tsx:204`). |
| MEDIUM | Inactive BYOK table is not safe to enable | `UserApiKey.encrypted_key` explicitly has no encryption implementation (`backend/app/models/preferences.py:24-35`). |
| LOW | Security headers are incomplete | `nosniff`, frame denial and referrer policy exist, but application middleware does not set CSP, HSTS or Permissions-Policy (`backend/app/core/ratelimit.py:42-48`). Proxy-level headers were not inspected. |

## 9. Database and deployment reconciliation

The repository has 18 SQLAlchemy models/tables but only one Alembic revision. That revision lowercases `users.email`; it does not create the `users` table or any initial schema. A fresh `alembic upgrade head` failed with `sqlite3.OperationalError: no such table: users`. Application startup currently calls `Base.metadata.create_all()` and suppresses startup exceptions (`backend/app/main.py:19-44`), creating an untracked schema path that cannot safely evolve production.

Two server-side Compose fixes reported by deployment are absent from Git:

1. `worker` has no Celery-specific healthcheck (`docker-compose.yml:63-76`).
2. `frontend` does not set `HOSTNAME=0.0.0.0` (`docker-compose.yml:78-97`; `frontend/Dockerfile:17-27`).

These are reconciliation items only; this audit did not modify Compose or production.

## 10. Overall readiness

- Existing entitled-student workspace: `PARTIALLY_CONNECTED` and locally buildable.
- New-student onboarding: `MISSING`.
- Platform curriculum discovery/enrollment: `MISSING`.
- Personal material path for a student without an entitlement: `BLOCKED`.
- Commercial subscription-to-entitlement automation: `MISSING`.
- Secure production authentication/payment posture: `BLOCKED` by critical/high findings.
- Fresh database deployment: `BLOCKED` by incomplete migrations.
- Production modification readiness: not authorized and not recommended.

The next implementation should begin with security, migration and entitlement-domain corrections, then deliver the minimum end-to-end student journey before any broad visual redesign.
