# Nuvira Remediation Plan

Mission: `NUVIRA-ONBOARDING-01`

Baseline: `db9fc4823ce65f08f9f770b8a32ac860de024587`

Status: Proposed engineering plan; no implementation authorization is implied.

## 1. Priority summary

The correct implementation order is:

1. Contain security and data-isolation risks.
2. Establish authoritative migrations and reconcile deployment configuration.
3. Build the entitlement/curriculum domain and minimum onboarding journey.
4. Make personal ingestion private, recoverable and operational.
5. Complete learning semantics, AI reliability and commercial automation.
6. Prove the journey in isolated staging before production change.

Visual redesign is deliberately deferred. Existing styling can support the first functional release once the states, routes and contracts are corrected.

## 2. Critical blockers

| Priority | Blocker | Required disposition |
|---|---|---|
| P0 | Arbitrary credit grants through client-controlled `price_id` + `credits` | Disable or redesign credit-pack endpoint before enabling payments |
| P0 | OAuth access/refresh tokens in query string | Replace callback handoff before production OAuth use |
| P0 | Missing OAuth state verification | Add cryptographically bound, expiring state/PKCE flow |
| P0 | Cross-user private embedding retrieval | Enforce visibility scope and add regression tests before personal uploads are trusted |
| P0 | No initial Alembic schema migration | Create/reconcile an authoritative migration chain and rehearse against fresh + existing databases |
| P0 | Default JWT/admin secrets accepted in production | Add fail-closed startup validation |
| P0 | Account deletion does not prove complete erasure | Define and implement transactional database/file/vector cleanup |
| P1 | New student has no in-product path to content | Deliver onboarding plus catalog/personal-course choice |
| P1 | No API grants entitlements | Create an idempotent, audited entitlement service |
| P1 | Interface locale not end-to-end | Centralize i18n and anonymous/authenticated preference synchronization |

## 3. Phase 0 — security containment

### Backend changes

1. Replace `buy-credits {price_id, credits}` with a server-owned `credit_pack_id`.
2. Resolve provider price and credit quantity from an approved database/config record; never trust either value from the browser or webhook custom metadata alone.
3. Add database uniqueness on provider event/reference IDs and transaction-safe idempotency.
4. Replace OAuth token query parameters with one of:
   - secure HttpOnly/SameSite session cookies, or
   - an expiring single-use opaque exchange code stored server-side and redeemed by the frontend.
5. Generate and validate OAuth `state`; add PKCE where supported; bind intended locale/destination to signed server state.
6. Verify Google identity/email claims appropriate to the selected OAuth endpoint before account linking.
7. Introduce refresh-session/token-family persistence, rotation, reuse detection and logout/password-reset revocation.
8. Decide and enforce the email-verification gate consistently.
9. Validate production startup: reject placeholder JWT secret, bootstrap password, missing active-provider secrets and unsafe debug mode.
10. Redact provider/internal exception strings from public responses; log with correlation IDs.

### Data-isolation changes

Define embedding visibility explicitly:

- Platform-published chunks: `owner_user_id IS NULL` plus published subject/version scope.
- Private chunks: `owner_user_id = current_user.id`.
- Retrieval: platform chunks for the entitled published version **OR** the current user's private chunks; never all rows for a subject.

Enforce this rule in the service signature so callers must provide the current user. Add an index supporting subject/chapter/owner/document lookup.

### Upload hardening

- Verify allowed MIME and file signatures, not extension alone.
- Advertise only formats actually supported; convert legacy `.ppt` through an isolated converter or reject it.
- Stream uploads with quotas rather than reading the whole file into memory.
- Add safe parser limits, archive/decompression-bomb defenses and an approved malware-scanning strategy.
- Store safe user-facing error codes separately from protected diagnostic details.

### Acceptance criteria

- OAuth callback URLs contain no access/refresh token and invalid/replayed state is rejected.
- Logout and password reset revoke relevant refresh sessions.
- A cross-user same-subject RAG test proves no private chunk leakage.
- Buying a real low-value sandbox pack cannot award any other credit quantity.
- Production mode refuses placeholder secrets and debug configuration.
- Upload tests reject forged extensions, oversize streams and unsupported legacy files safely.

## 4. Phase 1 — database and deployment foundation

### Migration strategy

Current Alembic head only updates email casing and fails on a fresh database because it assumes `users` exists. `Base.metadata.create_all()` is masking the absence of schema history.

Required work:

1. Inventory the exact production schema read-only and compare it with SQLAlchemy metadata and the reported 18 application tables.
2. Create an authoritative initial/baseline migration covering the current schema, including pgvector extension prerequisites.
3. Define a safe adoption path for the existing production database using verified schema comparison and `alembic stamp` only after owner review/backups.
4. Place the lowercase-email data migration after the schema baseline or guard it explicitly for legacy adoption.
5. Stop using `create_all()` as the production schema-management mechanism after migration parity is proven.
6. Make schema/seed failures fail service startup in production rather than printing and continuing.
7. Add migrations for every later model change; no implicit table creation.

### Compose reconciliation

Bring the two already verified server corrections into a reviewed non-main implementation branch:

- Worker healthcheck based on `celery inspect ping` with a deterministic node name/timeouts.
- Frontend runtime `HOSTNAME=0.0.0.0`.

Do not copy the production Compose file blindly. Diff it read-only, isolate only intended corrections, and preserve project-specific networking/volumes.

### Acceptance criteria

- `alembic upgrade head` succeeds on an empty PostgreSQL+pgvector database and creates the expected schema.
- Upgrade from a sanitized production-schema clone succeeds without destructive drift.
- Downgrade/restore procedure is documented and rehearsed where technically safe.
- Application startup fails on schema mismatch in production.
- All five isolated staging services report meaningful health, including Celery and externally reachable Next.js bind.
- No public host ports are introduced; proxy-network isolation remains intact.

## 5. Phase 2 — curriculum and entitlement domain

### Additive domain model

Proposed entities/fields:

- `curricula`: title, country/system, level, grade/track, educational language, public slug.
- `curriculum_versions`: academic year, edition, content version/checksum, status, effective dates.
- Curriculum-to-subject association.
- Subject publication fields: draft/review/published/retired and preview policy.
- Licensing/provenance record: rights status, source, territory/term notes, review sign-off.
- `entitlements`: user, scope (curriculum/subject), source, status, start/end, revoked timestamp/reason, external reference.
- Server-owned product/price mapping to entitlement scope and/or credit pack.
- Unique constraints preventing duplicate active grants and duplicate provider fulfillment.

Keep existing table names where practical and migrate `UserSubjectAccess` additively or behind a compatibility service. Do not rename tables only for branding.

### APIs

- Public/authenticated catalog list and detail with publication filtering.
- Current-user entitlement list.
- Authorized acquire/start operation for approved free/trial flows.
- Internal payment fulfillment to entitlement service.
- Admin draft/review/publish/version operations.
- Admin gift/revoke operation with audit reason.
- Preview-content endpoint if owner approves preview behavior.

Every content lookup must enforce publication version plus entitlement; direct object IDs are not sufficient.

### Syrian curriculum preparation

Before content intake:

1. Owner confirms textbook rights/licensing.
2. Record curriculum year, edition, track and language.
3. Hash/version source files and preserve provenance.
4. Establish academic review and correction sign-off.
5. Publish the textbook once as platform content; do not duplicate it per student.

### Acceptance criteria

- A seeded test curriculum can be discovered without authentication if approved.
- A test student can obtain an approved test entitlement without database intervention.
- Entitlement grant, renewal, expiry, cancellation and revocation are idempotent and audited.
- Unpublished/retired/wrong-version content remains inaccessible through direct IDs.
- Subscription status alone never grants an unspecified subject.
- Admin can publish content and manage access through authorized application workflows.

## 6. Phase 3 — onboarding and end-to-end internationalization

### Frontend functional changes

- Add pre-login language control and centralized message catalogs for English, Arabic and German.
- Default to English; render locale and direction server-side from a cookie.
- Translate landing, auth, verification, reset, onboarding, dashboard, settings, billing, pricing, errors and empty states.
- Add a dedicated, routable, resumable onboarding flow.
- Keep app shell, settings, account, help and logout accessible with zero subjects.
- Replace the administrator-only empty state with two functional paths: browse curricula or use personal material.
- Persist/resume last accessible subject/chapter and use URLs for important learning state.
- Split dashboard initialization so failure of avatar/preferences/review data does not hide all content.

### Backend changes

- Add onboarding version/start/completion state.
- Accept/synchronize locale safely during registration and OAuth.
- Define authenticated preference precedence over anonymous cookie after initial sync.
- Return stable localized-error keys/codes rather than provider/internal messages.

### Accessibility acceptance criteria

- Full keyboard path through landing, auth, onboarding and first learning action.
- Visible focus on every operable element; associated labels and focusable error summary.
- Skip link on navigation-heavy pages.
- Mobile touch targets and spacing meet documented web accessibility requirements.
- Screen readers receive names/states for icon buttons, selected language/theme, processing status and active navigation.
- Reduced-motion disables both transitions and non-essential keyframe animations.
- Automated axe checks plus manual English/German/Arabic keyboard and screen-reader spot checks pass.
- RTL visual tests cover desktop/mobile, mixed text, back/chevron semantics, forms and chat.

## 7. Phase 4 — personal curriculum intake

### Product model

Add a private course/subject container owned by the student and independent of platform entitlements. If multi-subject personal curricula are in V1 scope, add an owned curriculum container; otherwise state that limitation clearly.

### Processing architecture

- Multi-file upload manifest and quotas.
- Durable processing attempt/event records.
- Idempotent Celery tasks with bounded retry/backoff and dead-letter/failed state.
- Transactional replacement: stage new chunks, then atomically switch visibility.
- Cleanup of partial embeddings/files after failure/cancel/delete.
- Retry, replace, delete and reprocess endpoints with owner authorization.
- Proposed chapter/concept extraction stored as draft structure requiring review.
- Checksums to detect duplicates and support replacement/versioning.

### Acceptance criteria

- User with no platform curriculum creates a private subject and uploads a supported PDF.
- Multiple files are tracked independently and as one course intake.
- Refresh/relogin preserves processing state.
- Failure offers retry/replace/delete and never leaves retrievable partial chunks.
- Cross-user listing, download, status, mutation and RAG isolation tests all pass.
- Account deletion removes or schedules verified deletion of files, document rows and embeddings according to policy.

## 8. Phase 5 — learning and AI reliability

### Required changes

- Add `chapter_id` (or ordered many-to-many placement) for concepts with migration and content backfill.
- Define versioned mechanism/explanation schema.
- Define progress semantics: viewed, practiced, mastered and completed must not be conflated.
- Test and optimize spaced repetition queries; preserve subject/content-version relationships.
- Persist conversation sessions/messages if product policy requires continuity, with retention/delete controls.
- Add OpenRouter timeout classification, retry/backoff, overload/rate-limit handling and safe fallbacks.
- Add credit deduction/refund only after owner approves AI commercial policy; current chat consumes no credits.
- Add moderation/safety and age-appropriate educational policy before school-market launch.
- Implement real quiz/question bank only under a separate approved scope; do not infer correctness from self-report buttons.

### Acceptance criteria

- Selecting a chapter returns only concepts assigned to that chapter.
- Progress rules are documented and tested against repeated/correct/incorrect attempts.
- AI failures never fabricate a reply and do not charge unrecoverable credits.
- Grounded badge is true only when authorized retrieved material was actually supplied.
- Conversation retention/deletion matches the privacy policy.
- OpenRouter and embedding costs, rate limits and operational alerts are measured in isolated staging.

## 9. Phase 6 — commercial and admin completion

### Billing hardening

- Choose one provider for the first release; configure only owner-approved products/plans.
- Validate interval and product mapping server-side.
- Correct Stripe renewal mapping using stored provider customer/subscription IDs.
- Handle payment failure, renewal, cancellation, expiry, refund and dispute states.
- Process webhooks idempotently under concurrency.
- Separate generic credits from curriculum entitlement unless the owner explicitly approves a combined policy.

### Admin capabilities

- Curriculum/version/subject/chapter/concept CRUD with draft/review/publish states.
- Entitlement grant/revoke and traceable reason.
- Processing dashboard with retry controls and protected diagnostic logs.
- User status/role changes with reauthentication safeguards and audit events.
- Content correction/version migration tools.

### Acceptance criteria

- Sandbox checkout → verified webhook → exact approved entitlement.
- Renewal extends access once; duplicate/replayed webhook has no duplicate effect.
- Cancellation/expiry behavior matches documented policy and preserves progress.
- Admin actions require server-side role checks and create immutable audit events.
- No pricing/access policy is hardcoded before owner approval.

## 10. Phase 7 — isolated staging verification and release safeguards

### Required automated coverage

- Backend unit and integration tests for every authorization boundary.
- PostgreSQL migration tests, not SQLite-only schema tests.
- Redis/Celery ingestion tests with fixture PDF/PPTX files.
- Payment-provider contract and webhook fixture tests.
- Browser E2E for English, German and Arabic/RTL.
- Responsive snapshots at representative mobile/tablet/desktop sizes.
- Accessibility automation plus manual keyboard/screen-reader review.
- Security regression tests for OAuth, token lifecycle, IDOR, upload isolation and pricing tampering.

### Minimum E2E journeys

1. Register → verify → onboarding → free/test curriculum entitlement → first concept.
2. Register in Arabic → private subject → upload → processing → grounded question.
3. Returning student → resume subject → due review → progress update.
4. Paid sandbox plan → webhook → exact entitlement → renewal/cancel/expiry.
5. Two same-subject students → private document isolation in list and AI retrieval.
6. Admin draft → review → publish curriculum; student catalog visibility changes correctly.

### Deployment safeguards

- Reconcile repository Compose with the two verified production-only corrections.
- Build immutable versioned images; record digests.
- Back up database and uploads; verify checksums and restore rehearsal.
- Apply migrations in isolated staging before production approval.
- Capture deployment-source SHA and migration revision.
- Define rollback separately for code, database and uploaded content.
- Do not run automatic destructive migrations.
- Do not deploy from this audit branch.

### Release gate

Production approval requires:

- All P0 security findings closed with tests.
- Fresh and upgrade migrations pass.
- At least one complete curriculum and one personal-material E2E path pass.
- Real payment/AI/email provider configuration is verified in sandbox or isolated staging.
- Content licensing/version approval is recorded.
- Backups/restores and rollback are rehearsed.
- Owner reviews commercial policy, privacy/retention, terms and child/student safety requirements.

## 11. Proposed implementation branch sequence

After owner approval, use separate reviewable branches; do not implement directly on `main`:

1. `security/oauth-billing-isolation`
2. `infra/migration-baseline-compose-reconcile`
3. `feature/curriculum-entitlements`
4. `feature/onboarding-i18n`
5. `feature/personal-curriculum-intake`
6. `feature/learning-ai-reliability`
7. `test/onboarding-e2e-staging`

Each branch should include migration notes, tests, threat-model delta and rollback impact. Deployment remains a separate owner-authorized operation.

## 12. Explicit non-actions from this audit

- No application code, schema or Compose file changed.
- No migration was generated or applied to production.
- No production account, curriculum, entitlement or upload was created.
- No payment, OAuth, email, OpenRouter or embedding credential was used.
- No production container, volume, proxy, DNS or certificate was touched.
- No branch was merged into `main`.
