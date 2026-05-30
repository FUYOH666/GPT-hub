# Documentation hub

Single map for GPT-hub. Entry from root: [README.md](../README.md).

## Start here

| Document | Purpose |
|----------|---------|
| [ZERO_ENTRY.md](ZERO_ENTRY.md) | Zero-friction onboarding: OpenRouter key → Docker → first chat |
| [versions_dep/v4/README.md](../versions_dep/v4/README.md) | v4 stack quickstart and env |
| [versions_dep/v4/ARCHITECTURE.md](../versions_dep/v4/ARCHITECTURE.md) | WebUI → orchestrator → OpenRouter |
| [versions_dep/v4/ROADMAP.md](../versions_dep/v4/ROADMAP.md) | Product roadmap and backlog |

## Build and operate

| Document | Purpose |
|----------|---------|
| [DEMO_PROMPTS.md](DEMO_PROMPTS.md) | Demo prompts + ops simulator scenarios |
| [versions_dep/v4/apps/orchestrator/README.md](../versions_dep/v4/apps/orchestrator/README.md) | Package: pytest, CLI tools |
| [PROMPT_PRECEDENCE.md](PROMPT_PRECEDENCE.md) | System prompt order |
| [WEBUI-PAYLOAD.md](WEBUI-PAYLOAD.md) | Open WebUI → orchestrator payload (ingest) |
| [OPENWEBUI_ROLES.md](OPENWEBUI_ROLES.md) | Registration, admin, `WEBUI_URL` |
| [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md) | Public HTTPS for Open WebUI |
| [CLOUDFLARE_TUNNEL_HANDOFF.md](CLOUDFLARE_TUNNEL_HANDOFF.md) | Cloudflare Tunnel handoff text |
| [AGENTS.md](../AGENTS.md) | Cursor agent handoff |
| [versions_dep/v4/CONTINUATION.md](../versions_dep/v4/CONTINUATION.md) | Agent continuation prompt (v4) |

**Validation:** from `versions_dep/v4/apps/orchestrator`:

```bash
uv run pytest
uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock
```

## Quality and reviews

| Document | Purpose |
|----------|---------|
| [reviews/2026-05-30-v4-staff-review.md](reviews/2026-05-30-v4-staff-review.md) | Staff review (v4) |
| [reviews/2026-04-02-multi-version-audit.md](reviews/2026-04-02-multi-version-audit.md) | *Historical* multi-version audit |

## Open work

Backlog source of truth: [versions_dep/v4/ROADMAP.md](../versions_dep/v4/ROADMAP.md) (Post-validation P1–P9).

- [P1 — Catalog refresh lock](../versions_dep/v4/ROADMAP.md#post-validation-backlog-2026-05-30)
- [P2 — Vision 400/422 fallback](../versions_dep/v4/ROADMAP.md#post-validation-backlog-2026-05-30)
- [P3 — Admin key docs](../versions_dep/v4/ROADMAP.md#post-validation-backlog-2026-05-30)
- [GitHub Issues](https://github.com/FUYOH666/GPT-hub/issues)

## Archive

| Document | Purpose |
|----------|---------|
| [archive/hackathon/README.md](archive/hackathon/README.md) | Hackathon docs index |
| [versions_dep/LEGACY.md](../versions_dep/LEGACY.md) | v1 → v4 legacy index |

## Governance

[CONTRIBUTING.md](../CONTRIBUTING.md) · [CHANGELOG.md](../CHANGELOG.md) · [AUTHORS.md](../AUTHORS.md) · [SECURITY.md](../SECURITY.md) · [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md)

Internal inventory (team): [DOC_INVENTORY.md](DOC_INVENTORY.md).
