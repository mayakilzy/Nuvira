# API Reference

Interactive docs are always live at `/docs` (Swagger) and `/openapi.json`.

## Auth
`POST /auth/register` · `POST /auth/login` · `POST /auth/refresh` ·
`GET /auth/me` · `GET /auth/verify-email/{token}` ·
`POST /auth/forgot-password` · `POST /auth/reset-password` ·
`GET /auth/google` · `GET /auth/google/callback`

## Billing
`GET /billing/plans` · `POST /billing/create-checkout-session` ·
`POST /billing/buy-credits` · `POST /billing/create-portal-session` ·
`POST /billing/webhook` · `GET /billing/subscription`

## Credits
`GET /credits/balance` · `GET /credits/history`

## User
`GET /user/profile` · `PUT /user/profile` · `PUT /user/password` ·
`DELETE /user/account`

## Admin (role: admin)
`GET /admin/users` · `GET /admin/stats`

## Agent (per project)
`POST /agent/execute` · `GET /agent/history`

## Health
`GET /health` · `GET /health/db`
