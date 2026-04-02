# GPTHub Orchestrator: порядок системных промптов

Официальная иерархия для `POST /v1/chat/completions` через оркестратор v3. Одно правило на продукт — без скрытых перезаписей.

## Response Visibility Contract

- **Видимый ответ пользователю** — только итоговый текст ассистента в `choices[].message.content` (и эквивалентные дельты в stream). Маршрутизация, классификатор, версии промптов и прочая диагностика **не** попадают в это поле.
- **Trace** (`X-GPTHub-Trace`, логи `execution_trace`) — отдельный канал. Оркестратор **не** склеивает trace в `content`.
- **Canned greeting:** при `task_type == greeting_or_tiny` без изображений и включённом `GREETING_CANNED_RESPONSE_ENABLED` ответ собирается локально; в trace — `canned_response: true`, вызова LiteLLM нет.
- Утечки «мышления» в UI могут идти от **модели** (текст в `content`) или от **клиента** (отдельные поля вроде `reasoning` / `reasoning_content` от провайдера — см. [OPENWEBUI_ROLES.md](OPENWEBUI_ROLES.md)). Промпты снижают риск цитирования мета-инструкций. По умолчанию оркестратор шлёт **`reasoning.exclude`** upstream и **вырезает** `reasoning*` / `thinking*` из ответа (non-stream и stream); при необходимости — настройки Reasoning Tags в Open WebUI. Если CoT всё ещё целиком в **`content`**, last-resort: **`ORCHESTRATOR_STRIP_KNOWN_COT_PREAMBLE=true`** (только non-stream).

## Порядок (от сильного к слабому влиянию на «режим» ответа)

Итоговый **один** блок `role: system` собирается так (сверху вниз в тексте сообщения):

1. **Жёсткие safety-правила** — когда появятся в коде (сейчас не подмешиваются).
2. **Session clock** — актуальные дата и время **на момент запроса** (часовой пояс из `ORCHESTRATOR_CLOCK_TZ`, по умолчанию UTC), чтобы модель могла отвечать на «какой сегодня день / который час» без веб-поиска. Реализация: [clock_context.py](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/clock_context.py); в trace: `server_clock_iso`. Отключение: `INJECT_REQUEST_DATETIME=false`.
3. **GPTHub role system** — текст из [role_prompts.yaml](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml), выбирается по `model_role` маршрутизатора (`fast_text`, **`fast_text_chat`** для приветствий/коротких реплик без strong в цепочке, `doc_synthesis`, `reasoning_code_*`, `vision_general`). Задаёт **базовый режим** ответа. Для **`greeting_or_tiny`** без вложений-картинок при включённом canned этот блок **не** уходит в LLM — ответ фиксированный (см. контракт видимости выше).
4. **Workspace / project** — зарезервировано под фазы памяти и RAG по workspace; пока не внедрено.
5. **Системные сообщения из клиента** (Open WebUI, API) — **дополняют** роль: добавляются **после** ролевого текста с разделителем `--- Additional instructions (from chat client) ---`. Так пользовательский «отвечай как философ» **не отменяет** выбранный GPTHub-режим.
6. **Сообщения пользователя и ассистента** — без изменения порядка после нормализации `system`.
7. **Артефакты / RAG / память** — когда появятся в pipeline, вставляются отдельными блоками согласно ROADMAP фазы 1–3.

Реализация слияния п.3 и п.5: [messages.py](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/messages.py) (`apply_role_system_messages`).

**Свежие новости и внешний интернет** — это отдельно: веб-поиск Open WebUI (Tavily и т.д.), его нужно включить в UI/админке; часы оркестра **не заменяют** поиск по СМИ.

## Версионирование

Поле `prompt_version` в `role_prompts.yaml` попадает в `X-GPTHub-Trace` (base64 JSON) для демо и отладки.

## Переменные окружения

- `ROLE_PROMPTS_PATH` — необязательный путь к альтернативному YAML (см. `Settings.role_prompts_path` в оркестраторе).
- `INJECT_REQUEST_DATETIME` — `true` / `false` (по умолчанию в compose: `true`).
- `ORCHESTRATOR_CLOCK_TZ` — IANA, например `Europe/Moscow`, `UTC`.
- `GREETING_CANNED_RESPONSE_ENABLED` — `true` / `false` (по умолчанию `true`): короткие приветствия без картинок — ответ без вызова LiteLLM.
- `GREETING_CANNED_MESSAGE` — текст canned-ответа (строка, не пустая).
- `ORCHESTRATOR_STRIP_KNOWN_COT_PREAMBLE` — `true` / `false` (по умолчанию `false`): last-resort вырезание известных преамбул CoT из `content` **только для non-stream** ответов upstream.
- `ORCHESTRATOR_REQUEST_REASONING_EXCLUDE` — `true` / `false` (по умолчанию `true`): мерж `reasoning: { exclude: true }` в запрос к LiteLLM (OpenRouter и др.).
- `ORCHESTRATOR_STRIP_REASONING_FROM_RESPONSE` — `true` / `false` (по умолчанию `true`): удаление `reasoning*` / `thinking*` полей из ответа клиенту (non-stream и stream).
