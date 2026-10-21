# Known Gaps

## Release blockers

1. **Production/remote drift unknown.** The supplied archive had no Git remote or SHA and production access was prohibited. Reconcile read-only before deployment.
2. **Real chat not exercised locally.** A configured OpenRouter key and embeddings provider are required.
3. **Upload completion not exercised.** Validate Redis, Celery worker, PDF/PPT extraction, embeddings and persisted status in isolated staging.

## Product gaps

1. Concepts are scoped to subjects but not chapters. The API reports `chapter_filter_applied: false`; add an additive `chapter_id` association and migration after owner approval.
2. No real exam quiz bank/API exists. The prototype's hard-coded quiz was intentionally excluded.
3. Chat history is not persisted; `/agent/history` now represents study attempts.
4. Material retry/delete endpoints do not exist, so the UI does not pretend these actions work.
5. Several secondary SaaS pages retain the template's basic visual styling, though they are no longer the student landing experience.

## Security follow-up

Google OAuth currently returns access and refresh tokens in the frontend query string. Replace this with a short-lived, single-use exchange code and clear callback parameters after exchange.
