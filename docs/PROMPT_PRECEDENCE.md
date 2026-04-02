# GPTHub Orchestrator: порядок системных промптов

Официальная иерархия для `POST /v1/chat/completions` через оркестратор v3. Одно правило на продукт — без скрытых перезаписей.

## Порядок (от сильного к слабому влиянию на «режим» ответа)

Итоговый **один** блок `role: system` собирается так (сверху вниз в тексте сообщения):

1. **Жёсткие safety-правила** — когда появятся в коде (сейчас не подмешиваются).
2. **Session clock** — актуальные дата и время **на момент запроса** (часовой пояс из `ORCHESTRATOR_CLOCK_TZ`, по умолчанию UTC), чтобы модель могла отвечать на «какой сегодня день / который час» без веб-поиска. Реализация: [clock_context.py](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/clock_context.py); в trace: `server_clock_iso`. Отключение: `INJECT_REQUEST_DATETIME=false`.
3. **GPTHub role system** — текст из [role_prompts.yaml](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml), выбирается по `model_role` маршрутизатора (`fast_text`, **`fast_text_chat`** для приветствий/коротких реплик без strong в цепочке, `doc_synthesis`, `reasoning_code_*`, `vision_general`). Задаёт **базовый режим** ответа.
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
