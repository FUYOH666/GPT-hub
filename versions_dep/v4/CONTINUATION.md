# Agent handoff: v4 (OpenRouter Free Survival Engine)

Copy this file or the **prompt section** into a new chat session.

---

## Current state

| Area | Status |
|------|--------|
| **v4** (`versions_dep/v4`) | **Active product.** Open WebUI → orchestrator → OpenRouter. **Auto catalog control loop:** role_scorer, probe-on-refresh, bandit EMA, curator overlay (opt-in). |
| **v3** (`versions_dep/v3`) | **Legacy frozen** — LiteLLM hybrid. Do not run alongside v4 (ports 3000/8089). |
| **Hackathon docs** | Archived under [docs/archive/hackathon/](../../docs/archive/hackathon/README.md). |

**Backlog:** [ROADMAP.md](ROADMAP.md) — **P2** (vision 400/422 fallback), **P6** (curator A/B в ops_simulator). Закрыто: P1 (catalog lock), control loop sprint.

---

## Docker (v4)

```bash
cd versions_dep/v4
cp .env.example .env   # ORCHESTRATOR_API_KEY, OPENROUTER_API_KEY, WEBUI_SECRET_KEY
docker compose up -d --build
docker compose down    # stop; add -v to wipe WebUI volume
```

- Open WebUI: http://localhost:3000  
- Orchestrator: http://localhost:8089 — `GET /healthz`, `GET /trace`, `GET /v1/admin/catalog`  
- Do **not** run v3 compose at the same time on 3000/8089.

---

## Request path

```text
Browser → Open WebUI :3000
  → OPENAI_API_BASE_URL=http://orchestrator:8000/v1
  → gpthub-orchestrator :8089 (host)
  → OpenRouter API (free model chains, key rotation)
```

- Trace: response header **`X-GPTHub-Trace`** (base64 JSON) or `/trace` decoder page.
- Stream fallback: non-stream retry on upstream failure (see ROADMAP P2 for vision 400).

---

## Local dev (orchestrator)

```bash
cd versions_dep/v4/apps/orchestrator
uv sync --extra dev
export OPENROUTER_API_KEY=...   # from .env, never commit
export ORCHESTRATOR_API_KEY=...
uv run pytest
uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock
uv run uvicorn gpthub_orchestrator.main:app --reload --port 8089
```

Optional live simulator (uses real OpenRouter quota):

```bash
uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=live
```

---

## Key modules (v4)

| Path | Role |
|------|------|
| `gpthub_orchestrator/openrouter/` | Client, catalog, health ban, curator |
| `gpthub_orchestrator/ops/routing_invariants.py` | Routing invariants for simulator |
| `gpthub_orchestrator/tools/ops_simulator.py` | Mock/live validation |
| `gpthub_orchestrator/data/ops_scenarios.yaml` | Scenario definitions |
| `gpthub_orchestrator/data/free_models_catalog.yaml` | Free model catalog |

---

## Docs to read first

| File | Purpose |
|------|---------|
| [README.md](README.md) | v4 quickstart |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack design |
| [ROADMAP.md](ROADMAP.md) | Phases + P1–P9 backlog |
| [docs/ZERO_ENTRY.md](../../docs/ZERO_ENTRY.md) | User onboarding |
| [docs/README.md](../../docs/README.md) | Full doc map |
| [AGENTS.md](../../AGENTS.md) | Repo-wide agent notes |

---

## Prompt for new chat (copy)

```
Continue GPTHub v4 (OpenRouter Free Survival Engine) in versions_dep/v4.

Read:
- versions_dep/v4/CONTINUATION.md
- versions_dep/v4/ROADMAP.md (Post-validation backlog P1–P9)
- versions_dep/v4/ARCHITECTURE.md
- docs/README.md

Stack: Open WebUI → orchestrator (uv, FastAPI) → OpenRouter. Ports: 3000 WebUI, 8089 orchestrator.
Validate: uv run pytest && uv run python -m gpthub_orchestrator.tools.ops_simulator --mode=mock

Task: <your task — prefer next ROADMAP item>.
```

---

## Engineering rules

- Python: **`uv`**; secrets in `.env` only
- No LiteLLM in v4 product path
- Log with `logging`; user-facing errors safe, details in logs
- CHANGELOG under `[Unreleased]` for user-visible changes
