# FAHEM Integration Test Report

Date: 2026-10-22  
Branch: `integration/suzanna-ui`

## Automated checks

| Check | Command | Result |
|---|---|---|
| Backend tests | `$env:DATABASE_URL='sqlite://'; python -m pytest -q` | PASS — 9 tests in 3.54s |
| Authorization regression | included in pytest | PASS — enrolled student allowed; second student denied; cross-subject attempt denied |
| Frontend production build/type check | `npm run build` | PASS — Next.js compiled, TypeScript completed, 14 routes generated |
| Source safety scan | `rg` for SaaSForge URL, shared frontend image, removed endpoint and simulated timers | PASS for active student code |

## Browser checks (isolated localhost)

Environment: FastAPI on `127.0.0.1:8995`, Next.js on `localhost:3000`, local SQLite database populated with synthetic course data only.

| Journey | Result |
|---|---|
| Email/password login and redirect to `/dashboard` | PASS |
| Authenticated subject, chapter and concept loading | PASS |
| Garden renders from persisted history | PASS |
| SN2 mechanism renders three stored mechanism steps and official source note | PASS |
| Mobile layout at 390×844 | PASS |
| Arabic preference persistence and `html dir=rtl`, `lang=ar` | PASS |
| Concurrent initial avatar session requests | PASS after race-condition repair; covered by regression test |
| Desktop responsive branch | PASS by DOM/accessibility inspection; the in-app browser's enlarged-viewport screenshot surface was clipped, so no reliable desktop PNG is claimed. |
| Real AI response | NOT RUN — no local OpenRouter key was supplied. |
| File processing completion | NOT RUN — isolated worker/Redis and processing packages were unavailable. |

## Screenshots

- `screenshots/garden-mobile.png`
- `screenshots/mechanism-mobile.png`
- `screenshots/settings-ar-rtl-mobile.png`

## Limitations

Docker validation was not run. The closest feasible native validation was used. No production or shared infrastructure was contacted.
