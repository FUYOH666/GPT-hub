# GPTHub Workspace — `versions_dep/v3`

**Open WebUI (UI)** + **GPTHub Orchestrator (FastAPI)** + **LiteLLM (gateway к моделям)**.

Отличие от [v2_c2](../v2_c2): вся продуктовая логика (маршрутизация, будущий perception, память, trace) живёт **в оркестраторе**, а не в настройках WebUI/LiteLLM.

- Архитектура и рецепт: [ARCHITECTURE.md](ARCHITECTURE.md)
- **План реализации по фазам (задачи, тесты, приёмка):** [ROADMAP.md](ROADMAP.md)
- **Handoff / новый чат:** [CONTINUATION.md](CONTINUATION.md) — остановка v2, Docker, промпт для агента
- **Публичный HTTPS (канон):** [../../docs/TEAM_PUBLIC_ACCESS.md](../../docs/TEAM_PUBLIC_ACCESS.md) — деплой WebUI; лендинг/редирект — репо сайта
- **Cloudflare Tunnel:** готовый текст для коллеги / [community](https://community.cloudflare.com/) — [../../docs/CLOUDFLARE_TUNNEL_HANDOFF.md](../../docs/CLOUDFLARE_TUNNEL_HANDOFF.md); шаблон [deploy/cloudflared/config.example.yml](deploy/cloudflared/config.example.yml)
- **Пользователи и роли Open WebUI** (регистрация, один admin, `webui.db`): [../../docs/OPENWEBUI_ROLES.md](../../docs/OPENWEBUI_ROLES.md)
- **Порядок system-промптов (роль GPTHub + клиент):** [../../docs/PROMPT_PRECEDENCE.md](../../docs/PROMPT_PRECEDENCE.md)
- **Демо-запросы для жюри / проверка trace:** [../../docs/DEMO_PROMPTS.md](../../docs/DEMO_PROMPTS.md)
- **Формат `messages` от WebUI (ingest):** [../../docs/WEBUI-PAYLOAD.md](../../docs/WEBUI-PAYLOAD.md)

## Быстрый старт

```bash
cd versions_dep/v3
cp .env.example .env
# Заполните LITELLM_MASTER_KEY, OPENROUTER_API_KEY (как в v2_c2). В .env есть WEBUI_BANNERS — баннер-атрибуция сверху; без строки скопируйте её из .env.example (см. OPENWEBUI_ROLES.md).
# Только чат (LiteLLM + orchestrator + WebUI): embedding-shim не обязателен.
docker compose up -d --build
# RAG в WebUI + embedding-shim: нужен BGE :9001 на хосте, затем:
# docker compose --profile rag up -d --build
# либо в .env: COMPOSE_PROFILES=rag
```

После **изменений кода оркестратора** (в т.ч. `role_prompts.yaml`, `model_roles.yaml`) пересоберите образ и поднимите сервис:

```bash
docker compose build orchestrator && docker compose up -d orchestrator
```

- Open WebUI: http://localhost:3000  
- LiteLLM: http://localhost:4000  
- Orchestrator: http://localhost:8089/healthz  

**Конфликт портов:** v3 и [v2_c2](../v2_c2) оба используют **3000** и **4000** — остановите другой стек перед запуском.

В compose WebUI направлен на **orchestrator** (`OPENAI_API_BASE_URL`). Оркестратор проксирует **`GET /v1/models`** и **`POST /v1/chat/completions`** в LiteLLM. По умолчанию **`ORCHESTRATOR_MODELS_CATALOG=single_public`**: в селекторе Open WebUI одна модель **`gpt-hub`** (фасад); реальные алиасы (`gpt-hub-fast`, `gpt-hub-strong`, …) остаются внутри LiteLLM и выбираются оркестратором (см. `X-GPTHub-Trace`). `DEFAULT_MODELS` / `DEFAULT_PINNED_MODELS` / `TASK_MODEL_EXTERNAL` в compose согласованы с **`ORCHESTRATOR_PUBLIC_MODEL_ID`** (по умолчанию `gpt-hub`). Для отладки списка алиасов в UI: **`ORCHESTRATOR_MODELS_CATALOG=all`** и пересборка `orchestrator`. Подробнее — [OPENWEBUI_ROLES](../../docs/OPENWEBUI_ROLES.md). При **`AUTO_ROUTE_MODEL=false`** запрос с `gpt-hub` маппится на **`DEFAULT_TEXT_MODEL`** оркестратора (`default_text_model` в настройках, по умолчанию `gpt-hub-turbo` — локальный :8002).

**Веб-поиск (Tavily):** в compose по умолчанию `ENABLE_WEB_SEARCH=true`; в `.env` задайте `TAVILY_API_KEY=…` (секрет не коммитить), при необходимости `WEB_SEARCH_ENGINE=tavily`. После смены ключа — `docker compose up -d --force-recreate open-webui`. В чате часто нужно явно включить режим веб-поиска у сообщения (иконка), иначе Tavily не вызывается. Подробнее — [.env.example](.env.example) и [docs/TEAM_PUBLIC_ACCESS.md](../../docs/TEAM_PUBLIC_ACCESS.md).

**Дата и время («который час», «какой сегодня день»):** оркестратор подмешивает в `system` актуальные дату/время на каждый запрос (`INJECT_REQUEST_DATETIME`, по умолчанию `true`; часовой пояс — `ORCHESTRATOR_CLOCK_TZ`, например `Europe/Moscow`). В trace: `server_clock_iso`. Это не заменяет веб-поиск для новостей. После смены env — `docker compose up -d orchestrator`.

**PDF / вложения в чат (RAG):** сервис **`embedding-shim`** (профиль Compose **`rag`**) проксирует `POST /v1/embeddings` на BGE на хосте (`BGE_EMBEDDING_UPSTREAM`, по умолчанию `host.docker.internal:9001`) и копирует **`dense_embedding` → `embedding`**, иначе Open WebUI падает с `KeyError: 'embedding'` и оранжевый статус «embedding» не завершается. Нужен запущенный BGE на Mac; без профиля `rag` чат работает, индексация RAG — нет.

**PDF в сообщении чата (не RAG):** оркестратор может извлечь текст из `file` + `data:application/pdf` и подмешать его в system-контекст (`INGEST_ENABLED`, см. [WEBUI-PAYLOAD.md](../../docs/WEBUI-PAYLOAD.md)).

**Если источник найден, но красная ошибка про `TransferEncodingError` / обрыв stream:** часто это **HTTP 400 от LiteLLM до начала SSE** (раньше — ложный `detect_prompt_injection` на текст из PDF; в `v2_c2/litellm/config.yaml` guardrail отключён) или **таймаут** — поднимите **`LITELLM_TIMEOUT_SECONDS`** (compose / `.env`, по умолчанию 600). Оркестратор при 4xx в stream отдаёт SSE `error` + `[DONE]` вместо обрыва тела.

**Роли и маршрутизация:** цепочки LiteLLM-алиасов — [apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml](apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml); **system-промпты по роли** — [apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml](apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml) (`prompt_version` в trace). Модели в [v2_c2/litellm/config.yaml](../v2_c2/litellm/config.yaml): текст — локальный **`gpt-hub-turbo`** (+ алиасы `fast`/`strong`/`doc`/`reasoning-or` на тот же endpoint); **OpenRouter free** — цепочка **`gpt-hub-vision` → … → `gpt-hub-fallback`** (только multimodal для картинок; без fallback на локальный Qwen). При 429 на free — BYOK / пауза / обновление slug’ов по `--suggest-vision-chain`.

**Автовыбор модели (по умолчанию включён):** `AUTO_ROUTE_MODEL=true` — оркестратор подменяет `model` по classifier + роли (`fast_text`, `fast_text_chat`, `doc_synthesis`, `vision_general`, `reasoning_code_*`). В UI при этом остаётся один id **`gpt-hub`**. `AUTO_ROUTE_MODEL=false` — в LiteLLM уходит модель из запроса; для id **`gpt-hub`** применяется маппинг на `default_text_model`. `CODE_ROUTE_PREFERENCE=local|openrouter` — меняет **роль и system-промпт** для кода; цепочка моделей одна и та же (локальный turbo, затем OR fallback).

**Fallback (non-stream):** при включённом автовыборе и `ORCHESTRATOR_LITELLM_FALLBACK=true` при **429/503** перебирается цепочка алиасов; в `X-GPTHub-Trace` — `orchestrator_fallback`. Stream: одна попытка, дублирующие fallbacks на стороне LiteLLM.

**Список free-моделей OpenRouter (курация):** из `apps/orchestrator` — `uv run python -m gpthub_orchestrator.tools.list_free_models` (`OPENROUTER_API_KEY` или `--no-auth`; опции `--vision-only`, `--json`). Порядок vision для ручного обновления `litellm/config.yaml`: `--suggest-vision-chain [--limit 5]`.

## Локальная разработка orchestrator

```bash
cd apps/orchestrator
uv sync
export LITELLM_BASE_URL=http://127.0.0.1:4000
export ORCHESTRATOR_API_KEY=your-master-key-same-as-litellm
# optional: export AUTO_ROUTE_MODEL=false  # только если нужен выбор модели только из UI
uv run uvicorn gpthub_orchestrator.main:app --reload --port 8089
```

## Trace

Trace пишется в **логи** orchestrator и в заголовке **`X-GPTHub-Trace`** (base64 JSON). Ключевые поля: `task_type`, `model_role`, `model_used` / `selected_model`, `prompt_version`, `classifier_source` (сейчас `heuristic`), `attachments_detected`, `fallback_used`, `fallback_aliases`, `orchestrator_fallback` (попытки / `model_selected` / `retries_after_failure`), `server_clock_iso` (если включена подстановка времени), **`canned_response`** (если ответ собран без LiteLLM для `greeting_or_tiny`). Декодирование: base64 → UTF-8 → JSON. Open WebUI заголовок в UI не показывает — см. [DEMO_PROMPTS.md](../../docs/DEMO_PROMPTS.md) и ROADMAP фаза 4.

**Видимый ответ vs «мышление»:** оркестратор не подмешивает trace в `content`; промпты `role_prompts.yaml` — только внешнее поведение (`prompt_version` сейчас **v0.5.2**). Опционально canned без LLM для **`greeting_or_tiny`** («привет», «как дела?»): **`GREETING_CANNED_RESPONSE_ENABLED=true`** (по умолчанию выключено). В запрос к LiteLLM по умолчанию мержится **`reasoning: { exclude: true }`** (`ORCHESTRATOR_REQUEST_REASONING_EXCLUDE`); из ответа клиенту вырезаются поля **`reasoning*` / `thinking*`** в JSON и SSE (`ORCHESTRATOR_STRIP_REASONING_FROM_RESPONSE`). Если в UI всё ещё видно «Рассуждение» — см. [OPENWEBUI_ROLES.md](../../docs/OPENWEBUI_ROLES.md) и [PROMPT_PRECEDENCE.md](../../docs/PROMPT_PRECEDENCE.md) (контракт видимости и чеклист).

## Медленные ответы, будто идёт OpenRouter

1. В **`X-GPTHub-Trace`** посмотрите **`model_used`** / **`selected_model`**: ожидается **`gpt-hub-turbo`** для текста. Если **`gpt-hub-fallback`** — локальный instruct не ответил, сработал fallback в LiteLLM на OpenRouter.
2. У контейнера **litellm** должен быть задан **`LLM_INSTRUCT_API_BASE`** (в compose по умолчанию `http://host.docker.internal:8002/v1`). Шлюз **:8002** должен слушать на **хосте** (Mac), не внутри Docker. Для GPU по Tailscale — явно **`LLM_INSTRUCT_API_BASE=http://100.x.x.x:8002/v1`** в `.env` и `docker compose up -d --force-recreate litellm`.
3. Не оставляйте в `.env` строку **`LLM_INSTRUCT_API_BASE=`** с пустым значением — иначе подставится пустой URL, долгие таймауты и переход на OpenRouter.

## Переменные

См. [.env.example](.env.example).
