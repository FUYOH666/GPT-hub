# Подсказка для агента (Cursor / др.)

Монорепозиторий **GPT-hub**: несколько версий стека под `versions_dep/`.

- **Продуктовая разработка:** [versions_dep/v4](versions_dep/v4) — OpenRouter Free Survival Engine (orchestrator → OpenRouter напрямую, без LiteLLM).
- **Legacy hybrid:** [versions_dep/v3](versions_dep/v3) — orchestrator + LiteLLM + локальный instruct; конфиг LiteLLM: [versions_dep/v2_c2/litellm/config.yaml](versions_dep/v2_c2/litellm/config.yaml).
- **Карта документов:** [README.md](README.md).
- **OpenRouter catalog refresh:** `apps/orchestrator` → `uv run python -m gpthub_orchestrator.tools.list_free_models --write-catalog`
- **Публикация WebUI:** [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md)
- **Роли Open WebUI:** [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md)

Архив: [versions_dep/v1_z/LEGACY.md](versions_dep/v1_z/LEGACY.md).
