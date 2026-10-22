# Nuvira Brand Guidelines

## Identity

- Official product name: **Nuvira**
- Repository slug: `mayakilzy/Nuvira`
- Product descriptor: multilingual learning companion
- Voice: calm, encouraging, precise, and non-punitive

Use `Nuvira` in visible UI, metadata, email identity, documentation, images, and deployment names. Legacy names may appear only when documenting provenance or an explicitly reviewed data migration.

## Visual continuity

The rebrand preserves the approved calm learning interface rather than introducing an unreviewed visual redesign:

- soft blue primary accent;
- supportive green progress states;
- warm neutral surfaces;
- high-contrast light/dark themes;
- German, English, and Arabic RTL behavior.

The implementation tokens are scoped under `--nuvira-*` in `frontend/src/components/nuvira/nuvira.css`.

## Naming

- Docker project: `nuvira`
- Images: `localdev/nuvira-frontend:1.0.0`, `localdev/nuvira-backend:1.0.0`
- Networks/volumes: `nuvira_*`
- Production directory: `/root/apps/nuvira/`
- Frontend/API: `nuvira.agentcraft.info`, `api.nuvira.agentcraft.info`
