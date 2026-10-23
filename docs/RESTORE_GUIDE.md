# Nuvira Restore Guide

Use this procedure only for a Nuvira backup. For transferring legacy application data into Nuvira, use `SUZANNA_TO_NUVIRA_MIGRATION.md` instead of restoring a legacy `.env` wholesale.

## Requirements

- Nuvira source checked out at the reviewed commit in `/root/apps/nuvira/`.
- Docker Engine and Compose.
- The configured external proxy network.
- A trusted `backup_nuvira_<timestamp>.tar.gz` and its `.sha256` sidecar.
- Empty or intentionally replaceable Nuvira named volumes.

## Restore

```bash
cd /root/apps/nuvira
sha256sum -c /path/to/backup_nuvira_<timestamp>.tar.gz.sha256
./scripts/backup/restore.sh /path/to/backup_nuvira_<timestamp>.tar.gz
docker compose exec -T backend alembic upgrade head
```

## Verify internally

```bash
docker compose exec -T backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/db').read().decode())"
docker compose ps
```

Then verify login, subject access, learning history, private uploaded-file availability, published curriculum source access, chat, and worker processing through the production domains. Do not delete the source backup or pre-restore volumes until business-level counts and sampled accounts pass verification.
