# Customization Guide

Building a new product on the template touches only a few files.

1. **Agent logic** — `backend/app/routers/agent.py`. Replace the example with
   your product's endpoints. Use `credits_service.check_and_deduct(...)` to
   charge, and `ai_service.chat(...)` for AI calls.
2. **Background jobs** — `backend/app/workers/tasks.py`. Add Celery tasks.
3. **Workspace UI** — `frontend/src/app/(dashboard)/workspace/page.tsx` and any
   components under `frontend/src/components`.
4. **Plans & prices** — `backend/app/core/seed.py` (names, prices, credits) plus
   each plan's `provider_price_ids`.
5. **Costs** — `CREDIT_COSTS` in `backend/app/services/credits_service.py`.
6. **Model** — `OPENROUTER_MODEL` in `.env`.
7. **Branding** — change `--accent` (and a few tokens) in
   `frontend/src/app/globals.css`; edit landing copy in `page.tsx`.

Rebuild and push base images with `./scripts/build-and-push.sh <version>` when
the stable layer changes; for product-only changes, build a thin image
`FROM` the base.
