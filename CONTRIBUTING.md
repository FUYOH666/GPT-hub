# Contributing

Thank you for contributing to GPT-hub.

## Active stack (v4)

- **Orchestrator:** [versions_dep/v4/apps/orchestrator](versions_dep/v4/apps/orchestrator) — Python 3.12+, **`uv`**
- **Docker:** [versions_dep/v4/docker-compose.yml](versions_dep/v4/docker-compose.yml) — `cp .env.example .env` (never commit `.env`)

## Before a pull request

From `versions_dep/v4/apps/orchestrator`:

```bash
uv sync --extra dev
uv run pytest
uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock
```

If you changed orchestrator code or data YAML, rebuild the image:

```bash
cd versions_dep/v4
docker compose build orchestrator
```

**Secrets:** no API keys, Tailscale IPs, or personal paths in git — only placeholders in `.env.example`.

## Documentation

- User-visible behavior changes → entry under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md)
- Doc map: [docs/README.md](docs/README.md)
- Architecture: [versions_dep/v4/ARCHITECTURE.md](versions_dep/v4/ARCHITECTURE.md)

## Legacy (v3 and earlier)

Touch legacy code only when fixing or documenting that line. Tests: `versions_dep/v3/apps/orchestrator` with the same `uv` workflow.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
