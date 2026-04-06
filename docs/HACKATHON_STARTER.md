# Чеклист: форк GPT-hub под свой хакатон

Краткий порядок действий. Детали запуска — [versions_dep/v3/README.md](../versions_dep/v3/README.md).

## 1. Форк и клон

- Форкните репозиторий под свою команду.
- Клонируйте **свой** fork; ветку `main` при необходимости переименуйте под правила площадки.

## 2. Официальное ТЗ

- Скачайте или выпишите **актуальные ограничения** с сайта соревнования (модели, API, формат сдачи, запреты).
- Сопоставьте их с текущим [litellm/config.yaml](../versions_dep/v2_c2/litellm/config.yaml) и [model_roles.yaml](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml). Этот репозиторий — заготовка; под финальное ТЗ почти всегда нужны правки алиасов и env.

## 3. Локальный запуск

```bash
cd versions_dep/v3
cp .env.example .env
# Заполните ключи: LITELLM_MASTER_KEY, OPENROUTER_API_KEY (если используете), URL локальной модели и т.д.
docker compose up -d --build
```

- Чат: http://localhost:3000  
- Не поднимайте одновременно **v3** и **v2_c2** (конфликт портов 3000/4000).

## 4. Модели и маршрутизация

- Алиасы LiteLLM — один файл [versions_dep/v2_c2/litellm/config.yaml](../versions_dep/v2_c2/litellm/config.yaml) (монтируется в v3). Vision — цепочка только **multimodal** free-моделей (без перехода на локальный текстовый instruct).
- Цепочки «роль оркестратора → алиас» — [model_roles.yaml](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml).
- Перед правкой slug’ов: из `versions_dep/v3/apps/orchestrator` — `uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-vision-chain` (актуальный порядок free+image с API OpenRouter).
- Идеи развития (free-модели, fallback, цена/качество): [versions_dep/v3/ROADMAP.md](../versions_dep/v3/ROADMAP.md).

## 5. Публичное демо (опционально)

- HTTPS, `WEBUI_URL`, без света внутренних портов: [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md).

## 6. Питч и сдача (опционально)

- Сценарий демо и платформа: [PITCH-DEMO.md](PITCH-DEMO.md).

## 7. Секреты

- **Не коммитьте** `.env`, реальные IP, токены туннелей. В git — только плейсхолдеры в `.env.example`.

Синхронизация команды (текст для чата, стратегия до/после ТЗ): [HACKATHON_TEAM_SYNC.md](HACKATHON_TEAM_SYNC.md).

Удачи на соревновании.
