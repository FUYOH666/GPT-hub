# Agent handoff (Cursor / other)

Monorepo **GPT-hub** — multiple stack versions under `versions_dep/`.

## Product (v4)

- **Path:** [versions_dep/v4](versions_dep/v4) — OpenRouter Free Survival Engine (orchestrator → OpenRouter directly, no LiteLLM)
- **Docs hub:** [docs/README.md](docs/README.md)
- **Onboarding:** [docs/ZERO_ENTRY.md](docs/ZERO_ENTRY.md)
- **Backlog:** [versions_dep/v4/ROADMAP.md](versions_dep/v4/ROADMAP.md)
- **Continuation prompt:** [versions_dep/v4/CONTINUATION.md](versions_dep/v4/CONTINUATION.md)

## Common tasks

- Catalog refresh: `cd versions_dep/v4/apps/orchestrator && uv run python -m gpthub_orchestrator.tools.list_free_models --write-catalog`
- Ops validation: `uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock`
- Public WebUI: [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md)
- Open WebUI roles: [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md)

## Legacy

- **v3** hybrid (LiteLLM): [versions_dep/v3](versions_dep/v3) — frozen; do not treat as active product
- **Index:** [versions_dep/LEGACY.md](versions_dep/LEGACY.md)
- **Hackathon archive:** [docs/archive/hackathon/README.md](docs/archive/hackathon/README.md)

## Engineering rules

- Python: **`uv`** only (`pyproject.toml`, `uv.lock`)
- Logging: `logging`, not `print`
- Secrets: `.env` locally; `.env.example` in git
