# gpthub-orchestrator

Python-пакет FastAPI. Запуск: см. [../../README.md](../../README.md).

```bash
uv sync
uv run uvicorn gpthub_orchestrator.main:app --host 0.0.0.0 --port 8000
```

Список бесплатных моделей OpenRouter (курация whitelist): `uv run python -m gpthub_orchestrator.tools.list_free_models` (нужен `OPENROUTER_API_KEY`, либо `--no-auth`).

**Роли и промпты (фаза 0.5):** `gpthub_orchestrator/data/role_prompts.yaml` — system по `model_role`; порядок слияния с клиентским system — [../../../docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md). Альтернативный файл: env `ROLE_PROMPTS_PATH`.

**Каталог моделей для UI:** `ORCHESTRATOR_MODELS_CATALOG=single_public` (по умолчанию) — в `GET /v1/models` одна запись `ORCHESTRATOR_PUBLIC_MODEL_ID` (`gpt-hub`); `all` — прокси как у LiteLLM.

**Canned / reasoning:** при `GREETING_CANNED_RESPONSE_ENABLED=true` короткий `greeting_or_tiny` без картинок — ответ без LiteLLM (по умолчанию выключено); в запрос мержится `reasoning.exclude`, из ответа клиенту убираются поля `reasoning*` / `thinking*` — см. `reasoning_response_filter.py`, `settings.py`, [docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md).

**Health:** `GET /healthz` — liveness процесса. `GET /readyz` — LiteLLM `/health/liveliness` доступен (без Bearer).

**Ingest (фаза 1):** PDF/аудио из последнего user-сообщения — `gpthub_orchestrator/ingest/`, env `INGEST_ENABLED`, `ORCHESTRATOR_ASR_*`; контракт WebUI — [../../../docs/WEBUI-PAYLOAD.md](../../../docs/WEBUI-PAYLOAD.md).

**Stream vs fallback:** при `stream=true` оркестратор не перебирает цепочку алиасов сам (одна попытка); дублирующие fallbacks остаются на стороне LiteLLM — в trace поле `orchestrator_fallback.mode` = `stream_single_attempt`.
