# GPTHub v4 — Architecture

## Thesis

**Free Tier Survival Engine:** orchestrator is the smart layer between Open WebUI and OpenRouter. Not LiteLLM, not a dumb pipe — role routing + ingest + multi-key survival + **auto catalog control loop**.

## Request flow

```text
Open WebUI
  POST /v1/chat/completions  (model: gpt-hub)
       ↓
Orchestrator
  1. ingest (PDF pypdf, audio → optional ASR)
  2. classifier → task_type, modalities
  3. router → role → resolve catalog chain (runtime catalog)
  4. role_prompts → system instructions
  5. OpenRouterClient.chat_completions
       - model chain per role
       - key pool rotation on exhausted key
       - 429/5xx → next model (same key), then next key
  6. trace → X-GPTHub-Trace header + logs
       ↓
OpenRouter API (free slugs only)
```

## Catalog control loop (live-first)

```text
GET /models (OpenRouter)
  → role_scorer (fast / code / doc / vision — different chains)
  → micro-probe head slug per section (default ON)
  → install runtime catalog + diff log
  → optional LLM curator (overlay merge, after refresh, under lock)
  → traffic → EMA bandit resort (default every 30 min, under lock)
  → health ban filters chain at request time
```

**Prod source of truth:** runtime catalog from startup + periodic refresh (`free_models_catalog.runtime.yaml` when persist enabled).

**Packaged** [`free_models_catalog.yaml`](apps/orchestrator/gpthub_orchestrator/data/free_models_catalog.yaml) — CI/offline fallback only (not auto-committed by weekly bot during active development).

## Modules

| Path | Role |
|------|------|
| `openrouter/client.py` | Direct httpx to OpenRouter; stream + non-stream; stats hooks |
| `openrouter/key_pool.py` | Quota, RPM, cooldown |
| `openrouter/catalog.py` | Load catalog; runtime overlay |
| `openrouter/role_scorer.py` | Deterministic per-role ranking |
| `openrouter/catalog_pipeline.py` | Refresh, diff, coordinator lock |
| `openrouter/catalog_probe.py` | Micro-probe on refresh |
| `openrouter/model_stats.py` | EMA bandit resort |
| `openrouter/curator.py` | Optional LLM overlay manifest |
| `router.py` | Role → catalog section |

## Configuration

- **Secrets:** `.env` only (never commit)
- **Roles:** `model_roles.yaml` v2 uses `chain: catalog.<section>`
- **Flags:** `OPENROUTER_PROBE_ON_REFRESH`, `OPENROUTER_BANDIT_ENABLED`, `OPENROUTER_CURATOR_MERGE_MODE=overlay`

## Free-only policy

- Only zero-priced models in catalog
- No `openrouter/free` auto-router slug
- Exhaustion → HTTP 503 with explicit `openrouter_exhausted` and full attempts in trace
- No silent downgrade to paid models

## RAG / ASR (optional)

- RAG: Open WebUI → embedding-shim → BGE (profile `rag`)
- ASR: optional external Whisper; not part of OpenRouter

## Ports

| Service | Host port |
|---------|-----------|
| open-webui | 3000 |
| orchestrator | 8089 |

Do not run v3 and v4 simultaneously (both bind 3000/8089).
