# gpthub-orchestrator (v4)

Python-пакет FastAPI — **OpenRouter Free Survival Engine**. Запуск: [../../README.md](../../README.md).

```bash
export OPENROUTER_API_KEY=... ORCHESTRATOR_API_KEY=...
uv sync --extra dev
uv run uvicorn gpthub_orchestrator.main:app --host 0.0.0.0 --port 8000
```

## OpenRouter catalog

```bash
uv run python -m gpthub_orchestrator.tools.list_free_models --write-catalog
uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-text-chain --limit 4
uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-vision-chain --limit 5
```

Каталог: `gpthub_orchestrator/data/free_models_catalog.yaml`. Роли: `model_roles.yaml` (`chain: catalog.text_fast`, …).

## Roles & prompts

`role_prompts.yaml` — system по `model_role`; порядок слияния — [../../../docs/PROMPT_PRECEDENCE.md](../../../docs/PROMPT_PRECEDENCE.md).

## UI catalog

`ORCHESTRATOR_MODELS_CATALOG=single_public` — одна модель `gpt-hub` в UI; `all` — все slug'и из catalog.

## Health & ops

- `GET /healthz` — liveness
- `GET /readyz` — OpenRouter `/models` reachable + catalog refresh meta
- `GET /trace` — decode `X-GPTHub-Trace` (HTML)
- `GET /v1/admin/catalog` — catalog, curator, bans, quota (Bearer admin key)

## Ingest

PDF/аudio — `gpthub_orchestrator/ingest/`; [../../../docs/WEBUI-PAYLOAD.md](../../../docs/WEBUI-PAYLOAD.md).

## Tests

```bash
OPENROUTER_API_KEY=or-test-key ORCHESTRATOR_API_KEY=test-key uv run pytest -q
```
