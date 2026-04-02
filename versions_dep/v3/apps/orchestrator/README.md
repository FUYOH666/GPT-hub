# gpthub-orchestrator

Python-пакет FastAPI. Запуск: см. [../../README.md](../../README.md).

```bash
uv sync
uv run uvicorn gpthub_orchestrator.main:app --host 0.0.0.0 --port 8000
```

Список бесплатных моделей OpenRouter (курация whitelist): `uv run python -m gpthub_orchestrator.tools.list_free_models` (нужен `OPENROUTER_API_KEY`, либо `--no-auth`).
