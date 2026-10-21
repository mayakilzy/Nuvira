# Screen-to-API Matrix

| Screen/action | API | State | Notes |
|---|---|---|---|
| Auth guard/profile | `GET /auth/me` | Real | Existing JWT refresh flow preserved. |
| Enrolled subjects | `GET /agent/subjects` | Real | Server filters by `UserSubjectAccess`; admins may inspect all. |
| Garden progress | `GET /agent/history` | Real | Derived from persisted successful attempts; no fabricated score. |
| Review suggestions | `GET /agent/review-queue` | Real | Uses persisted study log and spaced-review intervals. |
| Chapters | `GET /agent/chapters` | Real | Enrollment enforced server-side. |
| Concepts/mechanism | `GET /agent/concepts` | Real, incomplete grouping | Returns authorized subject concepts and stored mechanism JSON. Current schema cannot filter concepts by chapter. |
| Record learning attempt | `POST /agent/attempt` | Real | Concept access checked; attempt number validated. |
| Companion session/avatar | `POST /agent/session/start` | Real | Uses persisted avatar state. |
| Companion chat | `POST /agent/chat` | Real contract | Auth and subject access enforced; local AI call needs configured OpenRouter/embedding keys. |
| Material list | `GET /agent/materials` | Real | Restricted to current student's documents. |
| Material upload | `POST /agent/materials/upload` | Real contract | Validates enrollment, chapter ownership, extension and 50 MB limit; requires worker for completion. |
| Processing status | polling `GET /agent/materials` | Real | UI polls only while a document is processing; no timer-generated success. |
| Preferences | `GET/PUT /agent/preferences` | Real | Validated DE/EN/AR and light/dark/system values. |
| Billing/profile/admin | Existing routes | Real | Reachable from Settings according to role. |
| Exam quiz | None | Blocked | Prototype hard-coded questions were not shipped as fake functionality. Requires an authorized persistent question bank/API. |

## UI states

Every educational load path has a loading, empty or error state. Missing enrollment is explicit. Chat errors are shown as errors rather than invented replies. Failed material processing displays the backend error note. The interface does not claim that an answer used course material unless `used_material_context` is true.
