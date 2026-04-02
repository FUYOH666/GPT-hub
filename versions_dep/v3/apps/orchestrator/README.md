# gpthub-orchestrator

Python-пакет FastAPI. Запуск: см. [../../README.md](../../README.md).

```bash
uv sync
uv run uvicorn gpthub_orchestrator.main:app --host 0.0.0.0 --port 8000
```

Список бесплатных моделей OpenRouter (курация whitelist): `uv run python -m gpthub_orchestrator.tools.list_free_models` (нужен `OPENROUTER_API_KEY`, либо `--no-auth`).

**Роли и промпты (фаза 0.5):** `gpthub_orchestrator/data/role_prompts.yaml` — system по `model_role`; порядок слияния с клиентским system — [../../../docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md). Альтернативный файл: env `ROLE_PROMPTS_PATH`.
