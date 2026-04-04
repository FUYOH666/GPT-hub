# GPTHub

**Стартовая точка** для сборки хакатонного или учебного стека «чат + маршрутизация моделей + RAG»: можно **форкнуть** и подставить свой кейс. Официальное **ТЗ конкретной площадки** всегда сверяйте отдельно после публикации ([True Tech Arena](https://truetecharena.ru/) и т.п.) — этот репозиторий — **заготовка и идеи**, не обещание совпадения с финальными ограничениями жюри.

Изначально ориентир — **МТС True Tech Hack 2026**, кейс **MWS GPT**: единый чат с мультимодальным вводом, маршрутизацией моделей и памятью/RAG — сборка из готовых OSS-слоёв и тонкая доработка (оркестратор).

## Статус

**Исследовательский прототип:** несколько быстрых итераций за короткий спринт, не «финальный продукт соревнования». Текущий компромисс — **локальный instruct** (если есть GPU за gateway) + **OpenRouter** для vision и резервных текстовых вызовов где настроено (см. [versions_dep/v2_c2/litellm/config.yaml](versions_dep/v2_c2/litellm/config.yaml), [versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml)). Очередность фаз и бэклог: [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md).

## Идеи для улучшения (кратко)

- Авто-актуализация списка **бесплатных** моделей у провайдера (например OpenRouter).
- Более **умный fallback** при 429/недоступности upstream.
- Выбор или ранжирование моделей по **цена / качество / латентность** под тип задачи.

Детали и другие направления: [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md) (раздел «LiteLLM / OpenRouter: идеи развития»).

## Зачем репозиторий открыт

Кейс взяли как повод **собрать рабочий прототип** «ради интереса»: Open WebUI, LiteLLM, при необходимости **OpenRouter** и своя модель за gateway, плюс небольшой **оркестратор** (маршрутизация, trace, ingest, промпты). Это не прорыв в смысле новой задачи — интеграция такого типа известна; ценность для нас — **пройденный путь**: документация, Docker, тесты, отладка, деплой, в том числе работа в паре с AI-ассистентом в IDE как с отдельным навыком.

От хакатона осталось и другое наблюдение: формат во многом проверяет не «кто глубже в коде или архитектуре», а умение **организовать людей** — роли, коммуникация, договорённости, удержание процесса к дедлайну. Сам репозиторий тогда — честный **артефакт процесса**, а не мера «уникальности идеи».

Если этот слепок кому-то сэкономит время на сборке похожего стека или даст опору для своей команды — смысл публичности уже есть. **Форкайте и используйте**; претензий на монополию на «правильный» хакатонный код здесь нет. Это **шаблон идей и рабочий код**, а не замена официальному регламенту площадки без вашей проверки.

## Документация (карта)

| Документ | Назначение |
|----------|------------|
| [README.md](README.md) | Точка входа в репозиторий (этот файл) |
| [docs/HACKATHON_STARTER.md](docs/HACKATHON_STARTER.md) | **Чеклист** для форка: env, compose, модели, ТЗ площадки |
| [versions_dep/v3/README.md](versions_dep/v3/README.md) | **Актуальный запуск Docker**, переменные, troubleshooting |
| [versions_dep/v3/ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md) | Архитектура v3: WebUI → orchestrator → LiteLLM |
| [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md) | Бэклог и фазы разработки |
| [versions_dep/v3/CONTINUATION.md](versions_dep/v3/CONTINUATION.md) | Handoff для нового чата: Docker v2↔v3, промпт |
| [CONSTRUCTOR.md](CONSTRUCTOR.md) | *Опционально для конкурса:* build/buy, OSS, риски, сроки |
| [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md) | *Опционально для сдачи:* питч, сценарий демо, платформа |
| [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) | **Канон:** публичный HTTPS для Open WebUI (туннель или VPS), прокси WS/SSE, безопасность; витрина — отдельный репо сайта |
| [docs/CLOUDFLARE_TUNNEL_HANDOFF.md](docs/CLOUDFLARE_TUNNEL_HANDOFF.md) | Текст задачи для человека с доступом к Cloudflare (Tunnel → `localhost:3000`) |
| [docs/AGENT_HANDOFF_EXTERNAL_REPO.md](docs/AGENT_HANDOFF_EXTERNAL_REPO.md) | Краткий контекст для агента другого репо / витрины |
| [docs/ISSUES_REPLY_DRAFTS_USATOV.md](docs/ISSUES_REPLY_DRAFTS_USATOV.md) | Тезисы ответов по issues команды (архитектура / метрики / память) |
| [AGENTS.md](AGENTS.md) | Подсказка для Cursor: куда смотреть в монорепо |
| [AUTHORS.md](AUTHORS.md) | Авторство и контакты |
| [LICENSE](LICENSE) | Лицензия MIT (код репозитория) |
| [SECURITY.md](SECURITY.md) | Как сообщать о уязвимостях |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Как предлагать изменения, pytest, Docker |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Правила общения в issues и PR |
| [docs/PRIVATE_REPO_SETUP.md](docs/PRIVATE_REPO_SETUP.md) | Создать приватный репозиторий на GitHub и первый push |
| [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md) | Open WebUI: регистрация, роли, один админ, `WEBUI_URL` |
| [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md) | Оркестратор: порядок system-промптов (роль GPTHub + клиент) |
| [docs/DEMO_PROMPTS.md](docs/DEMO_PROMPTS.md) | Готовые запросы для демо и проверки `X-GPTHub-Trace` |
| [docs/WEBUI-PAYLOAD.md](docs/WEBUI-PAYLOAD.md) | Формат `messages` Open WebUI → оркестратор (ingest PDF/аудио) |

**Архив эксперимента:** [versions_dep/v1_z/LEGACY.md](versions_dep/v1_z/LEGACY.md) — не отражает текущий v3.

Конфигурация: в каталоге стека скопируйте `.env.example` в `.env` (**не коммитьте** `.env`, реальные IP и ключи).

## Быстрый старт (Docker) — v3

Активная разработка ведётся в **v3** (orchestrator + тот же `litellm/config.yaml`, что и у v2).

1. **Официальную задачу** кейса уточните на площадке соревнования (для MWS GPT см. [truetecharena.ru](https://truetecharena.ru/) — дата публикации ограничений может быть позже старта репо).
2. Перейти в [versions_dep/v3](versions_dep/v3): `cp .env.example` → `.env`, заполнить переменные (см. [v3/README.md](versions_dep/v3/README.md)).
3. `docker compose up -d --build`

- Open WebUI: http://localhost:3000  
- Подробности, RAG/PDF, порты: [versions_dep/v3/README.md](versions_dep/v3/README.md)

**v2_c2** ([versions_dep/v2_c2](versions_dep/v2_c2)): заморозка — Open WebUI **напрямую** в LiteLLM; **не поднимать одновременно с v3** (порты 3000/4000). Файл [litellm/config.yaml](versions_dep/v2_c2/litellm/config.yaml) **монтируется в v3** — правки алиасов и провайдеров делать в одном месте. Дорожная карта активной работы: [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md).

## Доступ команды в интернете

Единый гайд по деплою WebUI: **[docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md)** (поддомен или туннель, `WEBUI_URL`, WS/SSE и длинные таймауты, не публиковать `:4000`/`:8089`). Ссылка с лендинга ведёт на уже поднятый чат; оформление пути на сайте — в репозитории витрины, не здесь.

## Авторство

Инициатива и ведение репозитория: **Aleksandr Mordvinov** ([**@FUYOH666** на GitHub](https://github.com/FUYOH666)). Команда и соавторство: [AUTHORS.md](AUTHORS.md) (в т.ч. **Pavel Usatov** / [@UsatovPavel](https://github.com/UsatovPavel)).

## Лицензия и вклад

Исходный код в этом репозитории (оркестратор, доки, скрипты интеграции) распространяется по лицензии **[MIT](LICENSE)**. Сторонние OSS-компоненты (Open WebUI, LiteLLM и др.) — по их лицензиям.

PR и идеи — см. [CONTRIBUTING.md](CONTRIBUTING.md); тон общения — [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Участие в **МТС True Tech Hack / кейс MWS GPT:** права на результат соревнования и передача прав призёрам — по [положению хакатона](https://truetechhack.ru); при расхождении с MIT для конкретной поставки уточнить у организаторов. Сообщения об уязвимостях: [SECURITY.md](SECURITY.md).
