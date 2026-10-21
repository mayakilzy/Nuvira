# Handover Guide

Everything you need to own and run your platform — written for a non-technical
owner. Keep this file.

## 1. What you received

A complete, self-contained web platform: user accounts, payments, a credit
system, an admin panel, and an AI feature — all running in Docker.

## 2. First-time setup (5 steps)

1. Copy `.env.example` to `.env` and fill in your keys (payments, email, AI).
2. Set a strong `POSTGRES_PASSWORD`, `JWT_SECRET`, and `FIRST_ADMIN_PASSWORD`.
3. Run `docker compose pull && docker compose up -d`.
4. Point your domain at the server (frontend + API subdomain).
5. Turn on backups: `./scripts/backup/install-cron.sh`.

You can now sign in with the admin email/password from your `.env`.

## 3. Day-to-day

- **Admin panel** — manage users and see stats.
- **Plans & pricing** — edit in the seed file (or have your developer expose it
  in the admin panel).
- **Money** — handled by your payment provider's own dashboard (Lemon Squeezy,
  Paddle, or Stripe). The platform records every credit grant and charge.

## 4. Safety (already built in)

- Automatic daily backups to up to three locations.
- One-command restore on any server (see RESTORE_GUIDE.md).
- Monitoring that emails you if the site, database, disk, or SSL has a problem.
- The database is never exposed to the internet; every admin action is logged.

## 5. If something breaks

1. Don't panic — your data is backed up.
2. Restore with: `./scripts/backup/restore.sh <latest backup file>`.
3. Verify with: `curl https://<your-api-domain>/health/db`.

## 6. Keys you must keep safe

Your `.env` file contains every secret. Keep a copy somewhere safe and private.
The nightly backup includes it automatically.
