# GPTHub v4 — Architecture

## Тезис

**Free Tier Survival Engine:** оркестратор — единственный умный слой между Open WebUI и OpenRouter. Не LiteLLM, не прямой pipe — role routing + ingest + multi-key survival + observability.

## Поток запроса

```text
Open WebUI
  POST /v1/chat/completions  (model: gpt-hub)
       ↓
Orchestrator
  1. ingest (PDF pypdf, audio → optional ASR)
  2. classifier → task_type, modalities
  3. router → role → resolve catalog chain (free_models_catalog.yaml)
  4. role_prompts → system instructions
  5. OpenRouterClient.chat_completions
       - model chain per role
       - key pool rotation on exhausted key
       - 429/5xx → next model (same key), then next key
  6. trace → X-GPTHub-Trace header + logs
       ↓
OpenRouter API (free slugs only)
```

## Модули

| Path | Role |
|------|------|
| `openrouter/client.py` | Direct httpx to OpenRouter; stream + non-stream |
| `openrouter/key_pool.py` | Quota, RPM, cooldown |
| `openrouter/catalog.py` | Load `free_models_catalog.yaml` |
| `router.py` | Role → catalog section |
| `trace.py` | Extended trace with `model_attempts`, `quota_remaining` |

## Конфигурация

- **Secrets:** `.env` only (never commit)
- **Catalog:** committed baseline + weekly refresh via CI
- **Roles:** `model_roles.yaml` v2 uses `chain: catalog.<section>`

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
