# gpthub-orchestrator

Python-пакет FastAPI. Запуск: см. [../../README.md](../../README.md).

```bash
uv sync
uv run uvicorn gpthub_orchestrator.main:app --host 0.0.0.0 --port 8000
```

Список бесплатных моделей OpenRouter (курация whitelist): `uv run python -m gpthub_orchestrator.tools.list_free_models` (нужен `OPENROUTER_API_KEY`, либо `--no-auth`).

**Роли и промпты (фаза 0.5):** `gpthub_orchestrator/data/role_prompts.yaml` — system по `model_role`; порядок слияния с клиентским system — [../../../docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md). Альтернативный файл: env `ROLE_PROMPTS_PATH`.

**Каталог моделей для UI:** `ORCHESTRATOR_MODELS_CATALOG=single_public` (по умолчанию) — в `GET /v1/models` одна запись `ORCHESTRATOR_PUBLIC_MODEL_ID` (`gpt-hub`); `all` — прокси как у LiteLLM.

**Canned / reasoning:** короткий `greeting_or_tiny` (в т.ч. «как дела?») без картинок — ответ без LiteLLM при `GREETING_CANNED_RESPONSE_ENABLED`; в запрос мержится `reasoning.exclude`, из ответа клиенту убираются поля `reasoning*` / `thinking*` — см. `reasoning_response_filter.py`, `settings.py`, [docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md).
