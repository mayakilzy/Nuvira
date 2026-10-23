# NUVIRA CURRICULUM-01 — Engineering Handoff

Date: 2026-10-23  
Branch: `feature/nuvira-curriculum-01`  
Verified base: `a9c275fba22f7acadfb00d5f292ef13472b2bb40` (`fix/nuvira-security-02`)  
Verified implementation SHA: `89fa4f18d1d24f5b0be9beed683d0e858885a7a3`  
GitHub verification: [successful isolated staging run 39923272760](https://github.com/mayakilzy/Nuvira/actions/runs/39923272760)

## Delivered

- Universal hierarchy: educational system → curriculum → version → subject → resource → unit → chapter → lesson → concept.
- Versioned, rights-aware publication lifecycle (`draft`, `processing`, `review`, `published`, `retired`) with explicit editorial approval. Editing invalidates approval; published/retired content cannot be edited in place.
- Private PDF upload and approved HTTPS import, streamed with size/quota limits, signature validation, safe names, SHA-256 deduplication, redirect limits and private/non-global destination blocking.
- Retry-safe Celery extraction into reviewable lessons with source page references, examples, exercises and preserved formula text when the PDF text layer supports it.
- Admin workflow at `/admin/curricula`: create hierarchy, upload/import, monitor processing, correct extracted titles/structure, approve review and publish.
- Student catalog in English, Arabic RTL and German; idempotent development enrollment, subject switching, lesson/source access and per-student progress.
- Authorization gates for admin actions, unpublished content, enrollment, cross-student access and subject-scoped AI context. When external AI is disabled, chat can answer from authorized published lesson text and identifies that stored-content mode.
- Isolated `curriculum_content` named volumes for backend/worker, non-root ownership, backup/restore coverage and staging isolation checks.
- The supplied four-page Arabic mathematics PDF was used locally as the real fixture. It produced two lessons and retained the checked expressions `f′(a) = lim ...` and `f′(x) = 9x² − 4x + 5`. The PDF itself is not tracked or committed.

## Data and migration

Alembic revision `0003_curriculum_library` adds `educational_systems`, `curricula`, `curriculum_versions`, `learning_resources`, `curriculum_units`, `lessons` and `user_lesson_progress`; it extends existing subjects, chapters, concepts and subject access without renaming legacy tables. The legacy-schema adoption script recognizes baseline, SECURITY-01 and CURRICULUM-01 profiles.

The authoritative curriculum sources remain outside the database in the private content volume; the database stores metadata, checksum, storage key, provenance, rights/review state, extracted structure and progress. Storage keys are deliberately adapter-friendly, but only the local-volume backend is implemented in this mission.

## API surface

- Admin: `POST /curricula/admin/systems`, `/curricula`, `/versions`, `/subjects`, `/resources/upload`, `/resources/import-url`; `GET /curricula/admin/library`, `/resources/{id}`; `POST /resources/{id}/retry`, `/resources/{id}/approve-review`, `/versions/{id}/publish|unpublish|retire`; `PATCH /curricula/admin/lessons/{id}`.
- Student: `GET /curricula/catalog`, `/subjects/{id}`, `/lessons/{id}`, `/resources/{id}/source`; `POST /subjects/{id}/enroll` (development/staging flag only), `/lessons/{id}/progress`.

Main implementation entry points: `backend/app/routers/curricula.py`, `backend/app/models/curriculum.py`, `backend/app/services/content_storage.py`, `backend/app/services/remote_import_service.py`, `backend/app/services/curriculum_processing_service.py`, `frontend/src/app/(admin)/admin/curricula/page.tsx`, `frontend/src/components/nuvira/NuviraApp.tsx`.

## Verification results

| Result | Environment | Command / suite | Evidence |
|---|---|---|---|
| PASS | Windows local, Python 3.11, SQLite test DB, supplied real PDF via `NUVIRA_CURRICULUM_FIXTURE` | `py -3 -m pytest -q` | 41 passed, 10 environment-gated skipped; 19.32 s final run |
| PASS | Windows local | `py -3 -m compileall -q app` | no errors |
| PASS | Windows local | `npx tsc --noEmit` | no errors |
| PASS | Windows local, Next.js 16.4.1 | `npm run build` | optimized build; 15 static pages including `/admin/curricula` |
| PASS | Windows local, temporary SQLite database | `py -3 -m alembic upgrade head`, `current`, `check` | `0003_curriculum_library (head)`; no new upgrade operations |
| NOT RUN | Windows local | Docker/Compose | Docker executable is not installed; equivalent isolated validation ran in GitHub Actions |
| PASS | GitHub-hosted Ubuntu 24.04, isolated Docker Compose, PostgreSQL 16/pgvector, Redis, Celery | workflow run 39923272760 | all workflow steps passed in 4m39s |
| PASS | Same GitHub run | backend suite | 37 passed, 11 skipped (fixture-gated unit case excluded because the real PDF is intentionally not committed) |
| PASS | Same GitHub run | PostgreSQL integration | 5 passed; Alembic at `0003`; no schema drift |
| PASS | Same GitHub run | Redis/Celery | 1 passed; worker registered curriculum task; broker outage recovery returned `pong` |
| PASS | Same GitHub run | live auth HTTP | 2 passed |
| PASS | Same GitHub run | live document HTTP | 1 passed |
| PASS | Same GitHub run | live curriculum HTTP with generated two-page PDF | 1 passed; upload → Celery review → approval → publication → enrollment → isolation → source/progress |
| PASS | Same GitHub run | Playwright desktop/mobile | report status `passed`, no failed tests |
| PASS | Same GitHub run | backup/restore rehearsal | DB restored at revision `0003`; uploads and curriculum source archives restored; original stack remained healthy |

The first two remote attempts exposed and then verified fixes for (1) leakage of the staging-only enrollment flag into production-default configuration tests and (2) non-root ownership of the new curriculum volume. Run 39923272760 is the clean full rerun after both corrections.

## Security and isolation notes

- Source downloads require authentication, a published subject and active enrollment (admin bypass is explicit).
- Cross-student progress and cross-subject lesson/resource access are rejected by server-side joins, not UI state.
- Remote imports require HTTPS, disallow embedded credentials/non-443 ports, revalidate every redirect, ignore proxy environment variables and reject resolved non-global addresses. DNS rebinding cannot be completely eliminated without a pinned-resolution transport; production operators should prefer direct uploads or an allowlisted fetch service until that adapter exists.
- The secret scan found no credential/private-key patterns in the implementation. The only connection-string match was the intentional `CHANGE_ME` isolation-test fixture. No `.env`, key, database dump, user data or PDF binary is tracked.
- The GitHub run reports only deprecation/cache warnings (Node 20 action runtime notice, Python library deprecations and non-writable pytest cache); no test failure remains.

## Remaining limitations and readiness

- Deterministic text-layer extraction only: no OCR, table reconstruction or guarantee of arbitrary mathematical-layout fidelity. Every import remains unpublished until human correction and approval.
- The attached PDF is an original development fixture, not a full or official Syrian curriculum. No claim is made that any national curriculum has been imported or certified.
- HTTPS positive-path import was not exercised against an external server; SSRF rejection paths were tested. External object storage/S3 is not implemented.
- Development enrollment is rejected by production configuration. A production registrar/admin assignment flow must be selected before production use.
- External AI, embeddings and payments were intentionally not enabled or tested. Stored-content chat is functional but is not a substitute for a production AI provider.
- Dependency/security findings outside this mission remain governed by SECURITY-02 and GitHub Dependabot; this mission did not perform broad dependency remediation.

**Readiness:** ready for isolated staging and engineering/content-editor evaluation. Not ready for production curriculum rollout until authoritative content rights/provenance, production enrollment operations, object-storage/backup operations, OCR/extraction acceptance criteria and production environment review are completed. No production deployment or `main` merge was performed.
