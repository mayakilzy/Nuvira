# Nuvira Integration Baseline and Drift

## Legacy inputs inspected

- `fahem-main.zip`: FastAPI backend, Next.js App Router frontend, PostgreSQL/pgvector models, Redis/Celery worker, authentication, billing, credits, admin, Docker Compose, backup scripts.
- `suzanna.zip`: React/Vite visual prototype centered in `src/app/App.tsx`, plus local UI primitives and design tokens.
- `FAHEM_UI_INTEGRATION_MISSION.md`: authoritative acceptance and safety specification.

The archives were extracted separately. The original ZIP files were not modified. The FAHEM archive contained no Git metadata, so a new repository was initialized on `integration/suzanna-ui`; baseline commit: `6a61cae`.

## Source structure

| Area | Authoritative source | Finding |
|---|---|---|
| Authentication/accounts | FAHEM | JWT access/refresh tokens, bcrypt hashes, email flows and Google OAuth already exist. |
| Educational API | FAHEM | Chat, preferences, session avatar, attempts, review queue, chapters and materials exist. |
| Student visual experience | Suzanna prototype | Approved garden, companion, chapters, materials, preferences, DE/EN/AR and RTL. |
| Deployment | FAHEM | Self-contained Compose stack with private PostgreSQL/Redis and optional worker. |

## Baseline conflicts

1. The prototype was a monolithic Vite component with hard-coded chapters, quizzes, files and chat replies.
2. The old Next.js `/dashboard` was the generic SaaS overview and `/workspace` called nonexistent `/agent/execute`.
3. Educational endpoints accepted arbitrary subject/concept IDs without enforcing `UserSubjectAccess`.
4. Materials listing exposed every document in a subject instead of only the current student's uploads.
5. The schema has subject-level concepts but no concept-to-chapter association.
6. No persistent quiz-question model or quiz-generation endpoint exists.
7. The archive has no remote metadata, so GitHub HEAD/live SHA drift could not be assessed without contacting external or production systems. The mission explicitly prohibited production access.

## Compatibility and restore points

- No schema migration was added.
- Existing auth token shapes and database models remain compatible.
- The frontend continues to use the existing authenticated Axios client and refresh interceptor.
- Production was not contacted, restarted or modified.
- Restore point: baseline commit `6a61cae`.

## Risks

- OAuth still transfers tokens in the callback query string. This is pre-existing and should be replaced with a short-lived one-time exchange code in a separate security change.
- A real OpenRouter key is required for end-to-end chat.
- Material processing requires the Celery worker, Redis, PDF/PPT dependencies and an embeddings provider.
- Live/remote drift must be reconciled read-only before rollout.
