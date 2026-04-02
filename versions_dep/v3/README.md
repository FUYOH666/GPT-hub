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

## Быстрый старт

```bash
cd versions_dep/v3
cp .env.example .env
# Заполните LITELLM_MASTER_KEY, OPENROUTER_API_KEY (как в v2_c2)
docker compose up -d --build
```

После **изменений кода оркестратора** (в т.ч. `role_prompts.yaml`, `model_roles.yaml`) пересоберите образ и поднимите сервис:

```bash
docker compose build orchestrator && docker compose up -d orchestrator
```

- Open WebUI: http://localhost:3000  
- LiteLLM: http://localhost:4000  
- Orchestrator: http://localhost:8089/healthz  

**Конфликт портов:** v3 и [v2_c2](../v2_c2) оба используют **3000** и **4000** — остановите другой стек перед запуском.

В compose WebUI направлен на **orchestrator** (`OPENAI_API_BASE_URL`). Оркестратор проксирует **`GET /v1/models`** и **`POST /v1/chat/completions`** в LiteLLM. По умолчанию **`ORCHESTRATOR_MODELS_CATALOG=single_public`**: в селекторе Open WebUI одна модель **`gpt-hub`** (фасад); реальные алиасы (`gpt-hub-fast`, `gpt-hub-strong`, …) остаются внутри LiteLLM и выбираются оркестратором (см. `X-GPTHub-Trace`). `DEFAULT_MODELS` / `DEFAULT_PINNED_MODELS` / `TASK_MODEL_EXTERNAL` в compose согласованы с **`ORCHESTRATOR_PUBLIC_MODEL_ID`** (по умолчанию `gpt-hub`). Для отладки списка алиасов в UI: **`ORCHESTRATOR_MODELS_CATALOG=all`** и пересборка `orchestrator`. Подробнее — [OPENWEBUI_ROLES](../../docs/OPENWEBUI_ROLES.md). При **`AUTO_ROUTE_MODEL=false`** запрос с `gpt-hub` маппится на **`DEFAULT_TEXT_MODEL`** оркестратора (`default_text_model` в настройках, по умолчанию `gpt-hub-strong`).

**Веб-поиск (Tavily):** в compose по умолчанию `ENABLE_WEB_SEARCH=true`; в `.env` задайте `TAVILY_API_KEY=…` (секрет не коммитить), при необходимости `WEB_SEARCH_ENGINE=tavily`. После смены ключа — `docker compose up -d --force-recreate open-webui`. В чате часто нужно явно включить режим веб-поиска у сообщения (иконка), иначе Tavily не вызывается. Подробнее — [.env.example](.env.example) и [docs/TEAM_PUBLIC_ACCESS.md](../../docs/TEAM_PUBLIC_ACCESS.md).

**Дата и время («который час», «какой сегодня день»):** оркестратор подмешивает в `system` актуальные дату/время на каждый запрос (`INJECT_REQUEST_DATETIME`, по умолчанию `true`; часовой пояс — `ORCHESTRATOR_CLOCK_TZ`, например `Europe/Moscow`). В trace: `server_clock_iso`. Это не заменяет веб-поиск для новостей. После смены env — `docker compose up -d orchestrator`.

**PDF / вложения в чат (RAG):** сервис **`embedding-shim`** проксирует `POST /v1/embeddings` на BGE на хосте (`BGE_EMBEDDING_UPSTREAM`, по умолчанию `host.docker.internal:9001`) и копирует **`dense_embedding` → `embedding`**, иначе Open WebUI падает с `KeyError: 'embedding'` и оранжевый статус «embedding» не завершается. Нужен запущенный BGE на Mac; без него RAG не заработает.

**Если источник найден, но красная ошибка про `TransferEncodingError` / обрыв stream:** часто это **HTTP 400 от LiteLLM до начала SSE** (раньше — ложный `detect_prompt_injection` на текст из PDF; в `v2_c2/litellm/config.yaml` guardrail отключён) или **таймаут** — поднимите **`LITELLM_TIMEOUT_SECONDS`** (compose / `.env`, по умолчанию 600). Оркестратор при 4xx в stream отдаёт SSE `error` + `[DONE]` вместо обрыва тела.

**Роли и OpenRouter free:** цепочки LiteLLM-алиасов — [apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml](apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml); **system-промпты по роли (фаза 0.5)** — [apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml](apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml) (`prompt_version` в trace). Альтернативный файл: `ROLE_PROMPTS_PATH` в `.env` / compose. Сами модели — в [v2_c2/litellm/config.yaml](../v2_c2/litellm/config.yaml) (`gpt-hub-fast`, `gpt-hub-doc`, `gpt-hub-reasoning-or`, `gpt-hub-fallback`, …).

**Автовыбор модели (по умолчанию включён):** `AUTO_ROUTE_MODEL=true` — оркестратор подменяет `model` по classifier + роли (`fast_text`, `fast_text_chat`, `doc_synthesis`, `vision_general`, `reasoning_code_*`). В UI при этом остаётся один id **`gpt-hub`**. `AUTO_ROUTE_MODEL=false` — в LiteLLM уходит модель из запроса; для id **`gpt-hub`** применяется маппинг на `default_text_model`. `CODE_ROUTE_PREFERENCE=local|openrouter` — для кода первым идёт свой `:8002` или только OpenRouter free.

**Fallback (non-stream):** при включённом автовыборе и `ORCHESTRATOR_LITELLM_FALLBACK=true` при **429/503** перебирается цепочка алиасов; в `X-GPTHub-Trace` — `orchestrator_fallback`. Stream: одна попытка, дублирующие fallbacks на стороне LiteLLM.

**Список free-моделей OpenRouter (курация):** из `apps/orchestrator` выполните `export OPENROUTER_API_KEY=...` и `uv run python -m gpthub_orchestrator.tools.list_free_models` (опции `--vision-only`, `--json`, `--no-auth`).

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

**Видимый ответ vs «мышление»:** оркестратор не подмешивает trace в `content`; промпты `role_prompts.yaml` — только внешнее поведение (`prompt_version` сейчас **v0.5.2**). Canned-приветствия по умолчанию без LLM (`GREETING_CANNED_RESPONSE_ENABLED`). Если в UI всё ещё показывается reasoning — см. [OPENWEBUI_ROLES.md](../../docs/OPENWEBUI_ROLES.md) (Reasoning Tags и чеклист сырого payload) и [PROMPT_PRECEDENCE.md](../../docs/PROMPT_PRECEDENCE.md) (Response Visibility Contract).

## Переменные

См. [.env.example](.env.example).
