## What changed

Brief summary (1–3 sentences).

## Checklist

- [ ] `uv run pytest` in `versions_dep/v4/apps/orchestrator` (if orchestrator changed)
- [ ] `uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock` (if routing/catalog changed)
- [ ] [CHANGELOG.md](../CHANGELOG.md) updated under `[Unreleased]` for user-visible changes
- [ ] No secrets, Tailscale IPs, or personal paths in the diff

## Notes

Optional: manual check (Docker v4, WebUI scenario, `/trace`).
