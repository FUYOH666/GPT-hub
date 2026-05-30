# GPTHub v4 — OpenRouter Free Survival Engine

**Активная линия разработки.** Open WebUI → оркестратор → **OpenRouter API напрямую** (без LiteLLM и без локального GPU LLM).

Пошагово для всех: [docs/ZERO_ENTRY.md](../../docs/ZERO_ENTRY.md).

## Быстрый старт

```bash
cd versions_dep/v4
cp .env.example .env
# Заполните ORCHESTRATOR_API_KEY, OPENROUTER_API_KEY, WEBUI_SECRET_KEY
docker compose up -d --build
bash scripts/verify_v4.sh   # smoke (нужен ORCHESTRATOR_API_KEY в env)
```

- Open WebUI: http://localhost:3000
- Orchestrator: http://localhost:8089 (`/healthz`, `/readyz`)
- Trace decoder: http://localhost:8089/trace
- Admin catalog: `GET /v1/admin/catalog` (Bearer admin key)

## Что такое `gpt-hub`

Один публичный id модели в Open WebUI. Оркестратор **не** показывает десятки slug OpenRouter — он сам:

1. Классифицирует задачу (текст / код / документ / картинка)
2. Выбирает цепочку free-моделей из live-каталога
3. При 429/5xx переключается на следующую модель или ключ
4. Возвращает trace: `X-GPTHub-Trace` (base64 JSON)

## Что внутри

| Компонент | Назначение |
|-----------|------------|
| **orchestrator** | Classifier, role routing, ingest PDF/audio, trace, **OpenRouterClient** |
| **open-webui** | UI; один публичный id `gpt-hub` |
| **embedding-shim** (profile `rag`) | BGE → OpenAI embedding shape для RAG |

## OpenRouter free-only

- **Live catalog** at startup + optional periodic refresh (`OPENROUTER_CATALOG_REFRESH_INTERVAL_HOURS`)
- **Role-specific chains:** `text_fast`, `text_code`, `text_doc`, `vision` (not one list copied 4×)
- **Micro-probe** on refresh (default ON): head slug per section; failures demoted to tail
- **Bandit EMA** (default ON): resort chains from traffic stats every 30 min
- Baseline for offline tests: [`free_models_catalog.yaml`](apps/orchestrator/gpthub_orchestrator/data/free_models_catalog.yaml)
- Runtime persist: `free_models_catalog.runtime.yaml`
- Роли → цепочки: [`model_roles.yaml`](apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml)
- **Key pool:** `OPENROUTER_KEYS=key1:50,key2:1000` — rotation, RPM throttle, cooldown on 429
- **Fallback:** model-first, then key rotation (non-stream **и** stream)
- **Health ban:** после N×429 slug временно исключается из цепочки (TTL)
- **LLM Curator** (opt-in): runs **after** refresh, overlay merge on heuristic pools
- Trace: `routing_source` (`heuristic` | `curator` | `bandit`), `manifest_version`, `openrouter_model`, `model_attempts`

## Troubleshooting 429

Сообщение `openrouter_exhausted` (RU) означает: все модели/ключи в цепочке вернули retryable ошибку.

1. Подождите 1–5 минут (free tier)
2. Добавьте второй ключ: `OPENROUTER_KEYS=key1:50,key2:1000`
3. Проверьте `/v1/admin/catalog` — banned slugs, quota
4. Non-stream имеет более длинную цепочку fallback, чем stream (env `ORCHESTRATOR_STREAM_FALLBACK_MAX_ATTEMPTS`)

## Переменные окружения

См. [`.env.example`](.env.example). Ключевые:

- `ORCHESTRATOR_API_KEY` — Bearer для WebUI → orchestrator
- `OPENROUTER_API_KEY` / `OPENROUTER_KEYS` — ключи OpenRouter
- `OPENROUTER_CATALOG_REFRESH_INTERVAL_HOURS=6` — периодический re-fetch
- `OPENROUTER_PROBE_ON_REFRESH=true` — micro-probe после refresh (default ON)
- `OPENROUTER_BANDIT_ENABLED=true` — EMA resort (default ON)
- `OPENROUTER_CURATOR_ENABLED=true` — LLM curator после refresh (overlay)
- `ORCHESTRATOR_OPENROUTER_FALLBACK=true` — цепочка моделей при 429/5xx

## Validation

После `docker compose up` или локального uvicorn:

```bash
bash scripts/verify_v4.sh              # smoke (1 запрос)
bash scripts/run_ops_simulator.sh mock # CI-safe: routing + fault injection
bash scripts/run_ops_simulator.sh live  # OpenRouter live (routing + degraded upstream)
curl -s -H "Authorization: Bearer $ORCHESTRATOR_API_KEY" \
  http://localhost:8089/v1/admin/catalog | jq '.catalog_diff, .probe_results, .bandit_stats, .active_catalog.text_fast, .active_catalog.text_code'
```

**Live checklist:**

1. Startup refresh → `source: openrouter_live`; `text_fast` ≠ `text_code`
2. `probe_results` visible in admin (pass/fail per section)
3. After traffic → `bandit_stats.by_section` accumulates samples
4. 429 on slug → health ban → chain skips slug
5. Curator enabled → `routing_source: curator`; ops invariants still pass

Отчёты: `reports/ops-mock.json`, `reports/ops-live.json` (+ `.md` summary).  
Staff review: [docs/reviews/2026-05-30-v4-staff-review.md](../../docs/reviews/2026-05-30-v4-staff-review.md) · Demo: [docs/DEMO_PROMPTS.md](../../docs/DEMO_PROMPTS.md).

## Тесты

```bash
cd apps/orchestrator
export OPENROUTER_API_KEY=or-test-key ORCHESTRATOR_API_KEY=test-key
uv sync --extra dev
uv run pytest -q
```

## Legacy

- [versions_dep/LEGACY.md](../LEGACY.md) — v1→v4
- **v3** — hybrid LiteLLM + локальный instruct; заморожена

Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md) · Roadmap: [ROADMAP.md](ROADMAP.md)
