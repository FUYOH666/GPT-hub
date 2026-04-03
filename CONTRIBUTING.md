# Contributing

Спасибо за интерес к репозиторию. Кратко, как не ломать стек и что проверить перед PR.

## Окружение

- **Оркестратор (Python):** `uv` — см. [versions_dep/v3/apps/orchestrator/README.md](versions_dep/v3/apps/orchestrator/README.md).
- **Docker v3:** [versions_dep/v3/README.md](versions_dep/v3/README.md) — `cp .env.example .env`, без коммита `.env` и секретов.

## Перед PR

1. Из `versions_dep/v3/apps/orchestrator`: `uv sync --dev` и `uv run pytest`.
2. Если менялись `model_roles.yaml`, `role_prompts.yaml` или код оркестратора — пересоберите образ: `docker compose build orchestrator` (из `versions_dep/v3`).
3. Секреты, TailScale IP, внутренние id моделей ASR — только в локальном `.env`, не в git.

## Документация

- Публичные изменения поведения — строка в [CHANGELOG.md](CHANGELOG.md) под `[Unreleased]`.
- Ссылки на архитектуру: [versions_dep/v3/ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md).

## Поведение в общении

См. [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
