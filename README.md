# GPTHub

Репозиторий под **МТС True Tech Hack 2026**, кейс **MWS GPT**: единый чат с мультимодальным вводом, маршрутизацией моделей и памятью/RAG — сборка из готовых OSS-слоёв и тонкая доработка.

## Документация (карта)

| Документ | Назначение |
|----------|------------|
| [README.md](README.md) | Точка входа в репозиторий (этот файл) |
| [versions_dep/v3/README.md](versions_dep/v3/README.md) | **Актуальный запуск Docker**, переменные, troubleshooting |
| [versions_dep/v3/ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md) | Архитектура v3: WebUI → orchestrator → LiteLLM |
| [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md) | Бэклог и фазы разработки |
| [versions_dep/v3/CONTINUATION.md](versions_dep/v3/CONTINUATION.md) | Handoff для нового чата: Docker v2↔v3, промпт |
| [CONSTRUCTOR.md](CONSTRUCTOR.md) | Конструктор: build/buy, OSS, риски, сроки хакатона |
| [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md) | Питч, сценарий демо, сдача на Платформу |
| [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) | **Канон:** публичный HTTPS для Open WebUI (Mac+туннель или VPS), прокси WS/SSE, безопасность; витрина — отдельный репо сайта |
| [docs/CLOUDFLARE_TUNNEL_HANDOFF.md](docs/CLOUDFLARE_TUNNEL_HANDOFF.md) | Текст задачи для человека с доступом к Cloudflare (Tunnel → `localhost:3000`) |
| [docs/AGENT_HANDOFF_SCANOVICH.md](docs/AGENT_HANDOFF_SCANOVICH.md) | Краткий контекст для агента другого проекта (например Scanovich) |
| [AGENTS.md](AGENTS.md) | Подсказка для Cursor: куда смотреть в монорепо |
| [AUTHORS.md](AUTHORS.md) | Авторство и контакты |
| [docs/PRIVATE_REPO_SETUP.md](docs/PRIVATE_REPO_SETUP.md) | Создать приватный репозиторий на GitHub и первый push |

**Архив эксперимента:** [versions_dep/v1_z/LEGACY.md](versions_dep/v1_z/LEGACY.md) — не отражает текущий v3.

Конфигурация: в каталоге стека скопируйте `.env.example` в `.env` (**не коммитьте** `.env`, реальные IP и ключи).

## Быстрый старт (Docker) — v3

Активная разработка ведётся в **v3** (orchestrator + тот же `litellm/config.yaml`, что и у v2).

1. Уточнить **Задачу** на [truetecharena.ru](https://truetecharena.ru/) после **10.04.2026 12:00** (ограничения кейса MWS GPT).
2. Перейти в [versions_dep/v3](versions_dep/v3): `cp .env.example` → `.env`, заполнить переменные (см. [v3/README.md](versions_dep/v3/README.md)).
3. `docker compose up -d --build`

- Open WebUI: http://localhost:3000  
- Подробности, RAG/PDF, порты: [versions_dep/v3/README.md](versions_dep/v3/README.md)

**v2_c2** ([versions_dep/v2_c2](versions_dep/v2_c2)): заморозка — Open WebUI **напрямую** в LiteLLM; **не поднимать одновременно с v3** (порты 3000/4000). Файл [litellm/config.yaml](versions_dep/v2_c2/litellm/config.yaml) **монтируется в v3** — правки алиасов и провайдеров делать в одном месте. Дорожная карта активной работы: [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md).

## Доступ команды в интернете

Единый гайд по деплою WebUI: **[docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md)** (поддомен или туннель, `WEBUI_URL`, WS/SSE и длинные таймауты, не публиковать `:4000`/`:8089`). Ссылка с лендинга (например Scanovich) ведёт на уже поднятый чат; оформление пути на сайте — в репозитории витрины, не здесь.

## Авторство

Инициатива и ведение репозитория: **Aleksandr Mordvinov** ([**@FUYOH666** на GitHub](https://github.com/FUYOH666)). Подробнее: [AUTHORS.md](AUTHORS.md).

## Лицензия и вклад

Правообладатель кода и условия передачи прав призёрам — по [Положению хакатона](https://truetechhack.ru); перед финалом уточнить у организаторов при необходимости.
