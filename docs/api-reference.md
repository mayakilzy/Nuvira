# Nuvira API Reference

Interactive documentation is available from a running API at `/docs` and `/openapi.json`.

## Auth

`POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` · `POST /auth/logout` · `GET /auth/me` · `GET /auth/verify-email/{token}` · `POST /auth/forgot-password` · `POST /auth/reset-password` · `GET /auth/google` · `GET /auth/google/callback`

## Educational API

`GET /agent/subjects` · `POST /agent/chat` · `GET /agent/preferences` · `PUT /agent/preferences` · `POST /agent/session/start` · `POST /agent/attempt` · `GET /agent/fun-fact` · `GET /agent/review-queue` · `GET /agent/chapters` · `GET /agent/concepts` · `POST /agent/materials/upload` · `GET /agent/materials` · `GET /agent/history`

Subject, chapter, concept, attempts, chat, and materials requests enforce authenticated access. Materials are restricted to the uploading student.

## Platform

- Billing: `/billing/*`
- Credits: `/credits/*`
- Profile/account: `/user/*`
- Administration: `/admin/*` (admin role)
- Health: `GET /health`, `GET /health/db`

There is no real quiz-generation endpoint in the reviewed version.
