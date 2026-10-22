# Nuvira Student Journey V1

Status: Proposed functional specification

Mission: `NUVIRA-ONBOARDING-01`

This document does not authorize implementation, pricing, content publication or UI redesign.

## 1. Product outcome

A student with no technical knowledge must be able to arrive at Nuvira, choose an interface language, create or access an account, select an approved platform curriculum or create a personal learning space, and reach one successful educational interaction without administrator or database intervention.

The journey must preserve a distinction between:

- **Interface language**: English, Arabic or German.
- **Educational content language**: defined independently by each curriculum/subject or personal course.
- **Content ownership**: platform-published content versus one student's private uploaded content.
- **Commercial access**: preview, free, trial, gifted or paid entitlement, according to owner-approved policy.

English is the default interface language. Arabic uses RTL from the first server-rendered page, not only after dashboard hydration.

## 2. Experience principles

1. No dead ends: every empty/error/restricted state offers a safe next action.
2. Account, language, help and logout remain reachable regardless of curriculum state.
3. Onboarding is resumable, skippable and versioned.
4. The student is never asked to understand “subject packages”, workers, embeddings or entitlements.
5. Platform curriculum and personal material are distinct choices with clear ownership and access language.
6. Access restrictions are explained before an action, not discovered only through a 403.
7. Progress reflects a documented learning rule, not decorative or fabricated percentages.
8. AI answers disclose whether approved material was used without exposing internal retrieval details.
9. Personal uploads are private by default and cannot enter another student's retrieval context.
10. Loading, processing and payment transitions survive refresh and provide recovery.

## 3. Journey map

### Stage 0 — Public arrival and language

Entry: `/`

Required interface:

- Language selector visible in the header: English, العربية, Deutsch.
- Default to English when no supported preference is available.
- Persist choice in a first-party cookie available to server rendering.
- Render `<html lang>` and `<html dir>` correctly on the first response.
- Preserve locale in links to pricing, login, registration, password reset and OAuth.
- Explain in one sentence that interface language can differ from course language.

Primary actions:

- Browse curricula.
- Start learning / create account.
- Sign in.
- Learn from my own material.

Empty/loading/error behavior:

- Catalog preview can render a skeleton while loading.
- Catalog failure must not remove register/login actions; show retry and help.
- If no curricula are published, explain that personal material remains available.

### Stage 1 — Authentication

Registration fields:

- Name, email, password.
- Interface locale carried from the anonymous cookie; no duplicate language question unless the student wants to change it.
- Clear password requirements validated on both client and server.
- Password-manager-friendly autocomplete and paste behavior.

After registration:

- Show a localized confirmation state.
- Apply an owner-approved email-verification policy consistently. If verification is required, do not pretend the account is fully ready; allow resend, change email, help and logout.
- Do not place access or refresh tokens in URLs.

OAuth:

- Use state and PKCE/nonce as applicable.
- Preserve locale and intended destination in signed server-side state.
- Complete login through a one-time exchange or secure HttpOnly session, then remove callback parameters.

Returning login:

- Resume the intended safe destination.
- If the last subject is no longer accessible, go to curriculum/home with an explanation rather than an authorization error.

### Stage 2 — Welcome and first-time onboarding

Entry condition: authenticated user with no completion record for the current onboarding version.

Recommended steps:

1. **Welcome** — personalized, localized summary of Nuvira.
2. **Choose how to learn** — platform curriculum or personal material.
3. **Optional preferences** — confirm interface language and accessibility/theme choices.

Controls:

- Back, Continue and Skip where safe.
- Save progress after each transition.
- Keep Settings, Help and Logout available.
- Never mark onboarding complete simply because the modal/page was viewed.

Completion rule:

Store `onboarding_version`, started/completed timestamps and selected path. Product analytics, if approved, should store minimal event data without educational content.

### Stage 3A — Platform curriculum library

Catalog information per curriculum:

- Title and short description.
- Country/educational system.
- Academic level, grade and track.
- Curriculum year/edition/version.
- Available subjects.
- Educational language.
- Publication/review status appropriate for public display.
- Access label: free, preview, trial, gifted, subscription or purchase—only after owner policy approval.
- Last content update and correction contact.

Filters:

- Country/system, level/grade, subject and educational language.
- Interface locale does not filter educational language implicitly.

Syrian Scientific Baccalaureate — Mathematics:

- Present as a curriculum plus a mathematics subject, not an ad hoc database grant.
- Identify textbook edition/year and licensing status before publication.
- Students select the published curriculum once; they do not upload the official textbook individually.

Entitlement transition:

1. Student opens curriculum details.
2. Student sees what access includes and any approved commercial terms.
3. Free/trial/gift/purchase/subscription flow produces an idempotent entitlement.
4. Entitlement is confirmed server-side.
5. Student enters the subject overview.

Payment pending/failure/cancel:

- Do not grant access based on browser redirect alone.
- Show pending state until a verified webhook or approved internal grant confirms access.
- Provide retry/change-method/back-to-catalog actions.

### Stage 3B — Personal material

This path must be available even when the student has no platform entitlement.

Step 1: create a private learning space

- Course/subject name.
- Optional educational language, level and description.
- Ownership explicitly marked private.

Step 2: choose scope

- One document.
- Multiple documents for one subject/course.
- Multiple subjects grouped into a personal curriculum, where supported.

Step 3: upload

- Supported formats clearly stated; V1 should advertise only formats actually parsed.
- Per-file and total quotas shown before selection.
- File name, size, type and upload progress.
- Allow removal before submission.
- Validate MIME/magic bytes and safely reject unsupported/encrypted/damaged files.

Step 4: processing

Durable stages:

- Uploaded.
- Extracting text.
- Organizing content.
- Creating search index.
- Ready.
- Needs attention / failed.

Refresh must restore the current stage. A failed item offers retry, replace, delete and help. User-facing errors use stable localized codes; raw internal exceptions remain in protected logs.

Step 5: review organization

- Nuvira may propose chapters/concepts, but the student can review/rename/reorder before using them as authoritative structure.
- V1 must not claim an entire curriculum was understood from files unless hierarchy extraction and review are implemented and tested.

Privacy contract:

- Only the uploader (and explicitly authorized administrators under a documented support process) can list, retrieve, process or delete the files and embeddings.
- Retrieval combines platform-public material with the current user's private material; it never includes another student's private material.

### Stage 4 — Subject overview

Show:

- Subject/curriculum identity and educational language.
- Continue last activity.
- Chapters and concepts.
- Personal/platform materials and readiness.
- Due review items.
- Access status and expiry where applicable.
- Clear first action such as “Start chapter 1” or “Ask Nuvira about this subject”.

If content is not yet ready:

- Explain whether publishing, processing, entitlement or configuration is pending.
- Do not render an empty garden as if learning progress exists.

### Stage 5 — First educational interaction

A successful first interaction is one of:

- Open an accessible concept and record a meaningful learning attempt.
- Ask a subject-scoped question and receive a successful answer.
- Complete an approved quiz item when real quiz functionality exists.

Requirements:

- Persist the event under the current user and subject.
- Update progress according to a defined rule.
- Show whether the AI answer was grounded in approved material.
- Provide retry/recovery for AI provider, rate-limit and insufficient-credit failures.
- Never convert a failed AI call into a fabricated answer.

### Stage 6 — Returning student

On return:

1. Restore secure session or request login.
2. Load authenticated language before the dashboard shell renders where practical.
3. Resume last accessible subject/chapter.
4. Present due reviews and processing updates.
5. If an entitlement expired, explain the state and offer owner-approved renewal/catalog alternatives.
6. If content version changed, retain progress where mappings are valid and explain any reset/remap.

## 4. Global states

### Empty states

| Context | Message purpose | Required actions |
|---|---|---|
| No curriculum/subject | Explain the two learning paths | Browse curricula; use personal material; settings; help; logout |
| No published curricula | Platform content is not yet available | Personal material; notify/help; return home |
| No chapters | Content setup or processing is incomplete | View materials/status; contact support; retry if owner |
| No personal materials | Explain why uploads help | Upload document; continue with platform content |
| No due reviews | Positive neutral state | Continue last topic; browse concepts |
| No plans | Do not expose implementation instructions | Explain unavailable checkout; return/catalog/help |

### Loading states

- Distinguish authentication, catalog, entitlement, curriculum content and document processing.
- Avoid a single indefinite spinner for multiple requests.
- Preserve layout to avoid content shift.
- Make long processing asynchronous and resumable.

### Error states

- Localized summary plus a specific recovery action.
- Field errors associated with inputs and an accessible error summary after submit.
- Retry only idempotent/safe operations automatically.
- Payment and entitlement states must not rely on the browser's last redirect.
- Provide a correlation/reference ID for support without leaking stack/provider details.

### Access restrictions

| Condition | Behavior |
|---|---|
| Not signed in | Redirect to localized login and retain intended safe destination |
| Email verification pending | Restrict according to approved policy; show resend/change/help/logout |
| No entitlement | Catalog/details remain visible; protected learning content stays unavailable |
| Expired/cancelled entitlement | Preserve account/progress; explain access state and approved renewal options |
| Unpublished content | Never expose through direct IDs; show unavailable state |
| Admin-only operation | Server returns 403; student UI never presents the control |

## 5. Navigation and accessibility contract

- Use real routes or URL state for curriculum, subject, chapter and important tabs so refresh/back/deep links work predictably.
- Current location must have a visible and programmatic active state.
- All icon-only buttons require accessible names.
- All controls must have visible keyboard focus and logical tab order.
- Mobile web targets should meet WCAG target-size expectations and retain adequate spacing.
- Forms require associated labels, inline errors and focusable error summary behavior.
- Status is not communicated by color alone.
- Respect reduced-motion for both transitions and keyframe animations.
- Add a skip-to-content link for navigation-heavy authenticated pages.
- RTL testing must include navigation order, chevrons/back semantics, mixed Arabic/Latin text, numbers, forms, tables and chat bubbles.

## 6. Persistence contract

Recommended additive entities/fields, subject to implementation approval:

- User onboarding state/version and timestamps.
- Curriculum, curriculum version and curriculum-subject relationships.
- Publication/review/licensing metadata.
- Personal course/curriculum ownership.
- Entitlement with source, status, start/end, revocation and external reference.
- Product/price-to-entitlement mapping controlled by the server.
- Concept-to-chapter association.
- Last learning location.
- Upload processing events/attempts and safe error code.
- Refresh-session/token-family records.
- One-time OAuth exchange state/code.

Existing tables should be extended with additive migrations; do not rename legacy tables merely for branding.

## 7. V1 acceptance criteria

The journey is acceptable only when an isolated E2E suite proves all of the following:

1. Anonymous user selects Arabic, reaches registration in RTL, registers, and keeps Arabic through onboarding and dashboard.
2. English is used when no preference exists.
3. New user can browse a seeded, licensed test curriculum and receive a test entitlement without database intervention.
4. New user can alternatively create a private subject, upload a supported test PDF, survive refresh during processing, and open the resulting content.
5. Settings/help/logout remain reachable with zero subjects.
6. Two users in the same platform subject cannot see or retrieve each other's private files/chunks.
7. Expired/unpublished/unentitled direct IDs are denied server-side.
8. OAuth callback contains no bearer/refresh tokens and rejects invalid state.
9. Payment sandbox maps an approved product/price to the correct entitlement; client-supplied credit/entitlement quantities are ignored.
10. Fresh database migration, rollback rehearsal, worker healthcheck and frontend bind configuration pass in isolated staging.
