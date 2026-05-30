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

- Baseline каталог: [`free_models_catalog.yaml`](apps/orchestrator/gpthub_orchestrator/data/free_models_catalog.yaml)
- Live refresh при старте → `free_models_catalog.runtime.yaml` (не перезаписывает baseline)
- Роли → цепочки: [`model_roles.yaml`](apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml)
- **Key pool:** `OPENROUTER_KEYS=key1:50,key2:1000` — rotation, RPM throttle, cooldown на 429
- **Fallback:** model-first, then key rotation (non-stream **и** stream)
- **Health ban:** после N×429 slug временно исключается из цепочки (TTL)
- **LLM Curator** (opt-in): async ranking free-моделей → `RoutingManifest`
- Trace: `routing_source`, `manifest_version`, `openrouter_model`, `model_attempts`

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
- `OPENROUTER_CURATOR_ENABLED=true` — фоновый LLM-куратор
- `ORCHESTRATOR_OPENROUTER_FALLBACK=true` — цепочка моделей при 429/5xx

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
