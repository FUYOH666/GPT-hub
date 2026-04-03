# Changelog

## [Unreleased]

### Changed

- Репозиторий **публичный** на GitHub; краткое описание репозитория обновлено.
- **ASR / STT:** дефолтный id модели в репозитории заменён на нейтральный `whisper-1` (внутренние slug’и ASR — только в локальном `.env`). Затронуты [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml), [settings.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/settings.py), v2_c2 compose, `.env.example`, [v2_c2/README.md](versions_dep/v2_c2/README.md).
- **LiteLLM / OpenRouter vision:** [versions_dep/v2_c2/litellm/config.yaml](versions_dep/v2_c2/litellm/config.yaml) — цепочка `gpt-hub-vision` … `gpt-hub-vision-4` + `gpt-hub-fallback` (Qwen / NVIDIA / Gemma); убран fallback `gpt-hub-fallback` → локальный Qwen (исправление 400 «not multimodal» при картинках). `num_retries: 3`. [model_roles.yaml](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml) — расширен `vision_general`. Доки: [versions_dep/v3/README.md](versions_dep/v3/README.md), [versions_dep/v2_c2/README.md](versions_dep/v2_c2/README.md), [ROADMAP](versions_dep/v3/ROADMAP.md).
- **Позиционирование как публичный hackathon starter:** [README.md](README.md) — якорь аудитории, блоки «Статус» и «Идеи для улучшения», смягчённый шаг 1 быстрого старта (ТЗ только с площадки); в таблице документов — [docs/HACKATHON_STARTER.md](docs/HACKATHON_STARTER.md), пометки *опционально* для [CONSTRUCTOR.md](CONSTRUCTOR.md) и [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md). [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md) — раздел «LiteLLM / OpenRouter: идеи развития».
- [README.md](README.md) — раздел «Зачем репозиторий открыт»: контекст хакатона, прототип (OpenRouter/OSS), акцент на команде и процессе, приглашение к форкам.
- Доки: убраны конкретные домены витрины из [TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md); handoff для внешнего репо — [AGENT_HANDOFF_EXTERNAL_REPO.md](docs/AGENT_HANDOFF_EXTERNAL_REPO.md) (вместо удалённого `AGENT_HANDOFF_SCANOVICH.md`); обновлены [README.md](README.md), [AGENTS.md](AGENTS.md).

### Added

- [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), шаблоны [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md) и [.github/ISSUE_TEMPLATE/bug_report.md](.github/ISSUE_TEMPLATE/bug_report.md); CI [.github/workflows/ci.yml](.github/workflows/ci.yml) — `pytest` оркестратора на push/PR.
- Оркестратор: `python -m gpthub_orchestrator.tools.list_free_models --suggest-vision-chain` — эвристика порядка free+image и YAML-черновик для `litellm/config.yaml`; тесты [test_list_free_models.py](versions_dep/v3/apps/orchestrator/tests/test_list_free_models.py).
- [docs/HACKATHON_STARTER.md](docs/HACKATHON_STARTER.md) — чеклист для форка: env, compose, модели (`litellm/config.yaml`), официальное ТЗ, ссылки на TEAM_PUBLIC_ACCESS и PITCH-DEMO.
- **[LICENSE](LICENSE)** (MIT) и **[SECURITY.md](SECURITY.md)**; в [README.md](README.md) — ссылки, разделение MIT vs положение хакатона / MWS.
- **v3 — ingest (фаза 1) и ops:** модуль [`versions_dep/v3/apps/orchestrator/gpthub_orchestrator/ingest/`](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/ingest/) (PDF через `pypdf`, аудио через `ORCHESTRATOR_ASR_*` → OpenAI-compatible transcriptions), интеграция в [`main.py`](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/main.py), trace `ingest_ms` / `artifacts`; [`GET /readyz`](versions_dep/v3/apps/orchestrator/README.md) (LiteLLM liveliness); [`embedding_shim` lifespan + `JSONDecodeError`](versions_dep/v3/embedding_shim/main.py). Документ [docs/WEBUI-PAYLOAD.md](docs/WEBUI-PAYLOAD.md); [versions_dep/v3/apps/orchestrator/CHANGELOG.md](versions_dep/v3/apps/orchestrator/CHANGELOG.md).

### Changed

- **v3 orchestrator — canned greeting по умолчанию выключен:** `GREETING_CANNED_RESPONSE_ENABLED` default **`false`** ([`settings.py`](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/settings.py), [compose](versions_dep/v3/docker-compose.yml)); «привет» / «как дела?» снова через LiteLLM. Включить: `GREETING_CANNED_RESPONSE_ENABLED=true`. Доки: [PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md), [OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md).

- [`versions_dep/v3/docker-compose.yml`](versions_dep/v3/docker-compose.yml) — **`litellm`**: `extra_hosts` + дефолт **`LLM_INSTRUCT_API_BASE`** (`host.docker.internal:8002/v1`); сервис **`embedding-shim`** только с профилем **`rag`**; WebUI не ждёт shim; см. [versions_dep/v3/README.md](versions_dep/v3/README.md), [.env.example](versions_dep/v3/.env.example), [CONTINUATION.md](versions_dep/v3/CONTINUATION.md).
- [docs/reviews/2026-04-02-multi-version-audit.md](docs/reviews/2026-04-02-multi-version-audit.md) — актуализация (ingest, профиль `rag`, shim client).
- **v3 — мало OpenRouter:** [`versions_dep/v2_c2/litellm/config.yaml`](versions_dep/v2_c2/litellm/config.yaml) — текстовые алиасы на локальный instruct; OpenRouter free — vision-цепочка и **`gpt-hub-fallback`** (актуальная схема см. тот же файл и README v3). [`model_roles.yaml`](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml), `default_text_model` → **`gpt-hub-turbo`**; доки [.env.example](versions_dep/v3/.env.example), [versions_dep/v3/README.md](versions_dep/v3/README.md).

### Added

- **Open WebUI — атрибуция:** переменная **`WEBUI_BANNERS`** в [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) и готовая строка в [versions_dep/v3/.env.example](versions_dep/v3/.env.example) (dismissible баннер: Aleksandr Mordvinov / [FUYOH666](https://github.com/FUYOH666)); раздел в [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md), подсказка в [versions_dep/v3/README.md](versions_dep/v3/README.md).
- **v3 orchestrator — reasoning channel:** классификатор: короткие фразы вроде «как дела?» → `greeting_or_tiny` (canned); `ORCHESTRATOR_REQUEST_REASONING_EXCLUDE` + `ORCHESTRATOR_STRIP_REASONING_FROM_RESPONSE`; модуль [`reasoning_response_filter.py`](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/reasoning_response_filter.py); stream SSE — построчная фильтрация `data:` JSON. Тесты [`test_reasoning_filter.py`](versions_dep/v3/apps/orchestrator/tests/test_reasoning_filter.py). Доки: OPENWEBUI_ROLES, PROMPT_PRECEDENCE, compose / `.env.example`.

- **v3 orchestrator — CoT/UI leak v2:** `role_prompts.yaml` **v0.5.2** — только внешнее поведение (язык, длина, формат, тон), без never/do-not/constraint-мета; canned short-circuit для **`greeting_or_tiny`** без изображений по умолчанию (`greeting_canned.py`, `GREETING_CANNED_RESPONSE_ENABLED`, `GREETING_CANNED_MESSAGE`); trace `canned_response`; опционально **`ORCHESTRATOR_STRIP_KNOWN_COT_PREAMBLE`** — non-stream, известные преамбулы (`response_preamble_strip.py`). Доки: **Response Visibility Contract** в [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md), [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md) (Reasoning Tags + чеклист сырого payload), [versions_dep/v3/ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md), [versions_dep/v3/README.md](versions_dep/v3/README.md). Тесты: `test_greeting_canned.py`, `test_response_preamble_strip.py`.
- **v3 orchestrator — публичный фасад модели:** `ORCHESTRATOR_MODELS_CATALOG` (`single_public` \| `all`), `ORCHESTRATOR_PUBLIC_MODEL_ID` (default `gpt-hub`); [public_models.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/public_models.py); `GET /v1/models` отдаёт одну модель для Open WebUI; при `AUTO_ROUTE_MODEL=false` запрос с фасадом маппится на `default_text_model`. Compose/WebUI: `DEFAULT_MODELS` / `TASK_MODEL_EXTERNAL` → `gpt-hub`. Доки: README v3, OPENWEBUI_ROLES, DEMO_PROMPTS; тесты в [test_models_proxy.py](versions_dep/v3/apps/orchestrator/tests/test_models_proxy.py).
- **v3 orchestrator — UX / reasoning leak (MVP):** роль **`fast_text_chat`** и цепочка **`gpt-hub-fast` → `gpt-hub-fallback`** (без `gpt-hub-strong`); `task_type` **`greeting_or_tiny`** в [classifier.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/classifier.py); последующая эволюция — **v0.5.2** + canned + контракт видимости (см. пункт CoT/UI leak v2 выше). Compose: **`DEFAULT_MODELS`** и **`TASK_MODEL_EXTERNAL`** — фасад **`gpt-hub`**. Документация: [OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md), [PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md), [DEMO_PROMPTS.md](docs/DEMO_PROMPTS.md).
- **v3 orchestrator — session clock:** [clock_context.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/clock_context.py) подмешивает в system актуальные дату/время на запрос; настройки `INJECT_REQUEST_DATETIME`, `ORCHESTRATOR_CLOCK_TZ`; trace `server_clock_iso`; тесты [test_clock_context.py](versions_dep/v3/apps/orchestrator/tests/test_clock_context.py). Документация: [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md), [.env.example](versions_dep/v3/.env.example), [versions_dep/v3/README.md](versions_dep/v3/README.md).
- [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md) — регистрация, `DEFAULT_USER_ROLE`, один admin, `WEBUI_ADMIN_EMAIL`, правка `webui.db`, ссылки из README / TEAM_PUBLIC_ACCESS / v3 README / AGENTS.
- [docs/CLOUDFLARE_TUNNEL_HANDOFF.md](docs/CLOUDFLARE_TUNNEL_HANDOFF.md) — готовый текст задачи для специалиста / Cloudflare Community; шаблон [versions_dep/v3/deploy/cloudflared/config.example.yml](versions_dep/v3/deploy/cloudflared/config.example.yml).
- [AUTHORS.md](AUTHORS.md) — авторство (Aleksandr Mordvinov / [@FUYOH666](https://github.com/FUYOH666)); раздел в [README.md](README.md); поля `authors` / `[project.urls]` в [versions_dep/v3/apps/orchestrator/pyproject.toml](versions_dep/v3/apps/orchestrator/pyproject.toml).
- [docs/PRIVATE_REPO_SETUP.md](docs/PRIVATE_REPO_SETUP.md) — приватный репозиторий GitHub (`gh repo create` или веб + `git push`).
- [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) — публичный HTTPS для Open WebUI (VPS / туннель), `WEBUI_URL`, WebSocket/SSE, чеклист безопасности, ограничения RAG/ASR на VPS.
- [docs/AGENT_HANDOFF_EXTERNAL_REPO.md](docs/AGENT_HANDOFF_EXTERNAL_REPO.md) и корневой [AGENTS.md](AGENTS.md) — краткий handoff для агента другого репозитория.
- [versions_dep/v1_z/LEGACY.md](versions_dep/v1_z/LEGACY.md) — архив бывшего `readme.md` v1_z; актуальный стек описан в v3.
- **v3 orchestrator — фаза 0.5 (реализация):** [role_prompts.yaml](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/role_prompts.yaml), [role_prompts.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/role_prompts.py), [messages.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/messages.py); trace: `prompt_version`, `task_type`, `selected_model`, `fallback_used`, `classifier_source`, `attachments_detected`; `ROLE_PROMPTS_PATH`; валидация полноты ролей в [model_registry.py](versions_dep/v3/apps/orchestrator/gpthub_orchestrator/model_registry.py); тесты golden + trace; [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md), [docs/DEMO_PROMPTS.md](docs/DEMO_PROMPTS.md).

### Changed

- [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md) — контракт видимости: дефолтные `reasoning.exclude` и strip ответа; preamble strip как last-resort для CoT в `content`.
- [versions_dep/v3/apps/orchestrator/README.md](versions_dep/v3/apps/orchestrator/README.md) — canned / reasoning кратко и ссылка на PROMPT_PRECEDENCE.
- [versions_dep/v3/README.md](versions_dep/v3/README.md), [docs/DEMO_PROMPTS.md](docs/DEMO_PROMPTS.md) — canned small-talk («как дела?»), `reasoning.exclude` / strip полей, ссылка на OPENWEBUI при «Рассуждение» в UI.
- [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) — сервис `orchestrator`: `GREETING_CANNED_RESPONSE_ENABLED`, `GREETING_CANNED_MESSAGE`, `ORCHESTRATOR_STRIP_KNOWN_COT_PREAMBLE`.
- [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) — `ENABLE_WEB_SEARCH` по умолчанию `true`; сервис `orchestrator`: `INJECT_REQUEST_DATETIME`, `ORCHESTRATOR_CLOCK_TZ`.
- [docs/PROMPT_PRECEDENCE.md](docs/PROMPT_PRECEDENCE.md) — шаг **Session clock** в порядке system-сообщений; переменные `INJECT_REQUEST_DATETIME`, `ORCHESTRATOR_CLOCK_TZ`.
- [versions_dep/v3/README.md](versions_dep/v3/README.md) — ссылки на PROMPT_PRECEDENCE / DEMO_PROMPTS, `role_prompts.yaml`, расширенное описание trace, команда пересборки `orchestrator`; [AGENTS.md](AGENTS.md) — промпты и демо-доки.
- [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md) — фаза **0.5** (в т.ч. выполненные 0.5.1–0.5.4, приёмка), **«Адаптация под модели организатора»**, приоритет времени до конкурса, уточнение «Не делаем»; [versions_dep/v3/ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md) — config-driven role prompts; [versions_dep/v3/.env.example](versions_dep/v3/.env.example) — `ROLE_PROMPTS_PATH`; [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) — `MODEL_ROLES_PATH`, `ROLE_PROMPTS_PATH` у `orchestrator`; [README.md](README.md) — ссылки на PROMPT_PRECEDENCE / DEMO_PROMPTS.
- [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md), [versions_dep/v3/README.md](versions_dep/v3/README.md), [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md) — Tavily / веб-поиск: переменные в локальном `.env`, пересоздание `open-webui`.
- [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) — `BYPASS_MODEL_ACCESS_CONTROL` (по умолчанию `true`), чтобы у роли `user` не был пустой селектор моделей; [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md), [versions_dep/v3/.env.example](versions_dep/v3/.env.example).
- [versions_dep/v3/docker-compose.yml](versions_dep/v3/docker-compose.yml) — проброс `ENABLE_WEB_SEARCH`, `WEB_SEARCH_ENGINE`, `TAVILY_API_KEY` в `open-webui`; [versions_dep/v3/.env.example](versions_dep/v3/.env.example) — блок Tavily (ключ без кавычек, `ENABLE_WEB_SEARCH=true`).
- [docs/OPENWEBUI_ROLES.md](docs/OPENWEBUI_ROLES.md) — `ENABLE_PERSISTENT_CONFIG` и блок «Нет ссылки регистрации на странице входа» (UI vs env).
- [versions_dep/v3/.env.example](versions_dep/v3/.env.example), [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) — режим admin + саморегистрация с `DEFAULT_USER_ROLE=user` vs `pending`.
- [docs/CLOUDFLARE_TUNNEL_HANDOFF.md](docs/CLOUDFLARE_TUNNEL_HANDOFF.md) — раздел «Пошагово в Zero Trust»: Published application, Service URL `:3000`, CNAME, `WEBUI_URL`, 502/521.
- [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) — отсылка на чеклист после маршрута; ранее: Mac + туннель + Tailscale, VPS, канон; ссылки в README / AGENTS / AGENT_HANDOFF_EXTERNAL_REPO.
- [versions_dep/v3/.env.example](versions_dep/v3/.env.example) — `WEBUI_URL`, `OR_SITE_URL`, `ENABLE_SIGNUP`, Tailscale для ASR / instruct / опционально rerank.
- [README.md](README.md) — таблица документов, быстрый старт с **v3** первично; v2_c2 как эталон LiteLLM и заморозка.
- [versions_dep/v2_c2/ROADMAP.md](versions_dep/v2_c2/ROADMAP.md) — сокращён до отсылки на [versions_dep/v3/ROADMAP.md](versions_dep/v3/ROADMAP.md).
- [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md) — безопасность и роутинг приведены к фактической конфигурации (guardrail injection off, цепочка v3 через orchestrator).
- [CONSTRUCTOR.md](CONSTRUCTOR.md) — §6 маршрутизация: v3 vs v2, источник правды по алиасам в LiteLLM; §4 шаг UI → orchestrator для v3.
- [versions_dep/v2_c2/README.md](versions_dep/v2_c2/README.md) — ссылки на v3 ROADMAP и v1_z LEGACY.
- [.gitignore](.gitignore) — `.pytest_cache/`.
- `versions_dep/v2_c2/litellm/config.yaml` — убран **`detect_prompt_injection`**: иначе вставка текста из PDF/RAG даёт **400** и обрыв stream в Open WebUI (`TransferEncodingError` на клиенте). Включение обратно — см. комментарий в файле.
- **v3 orchestrator:** таймаут LiteLLM по умолчанию **600 c** (`LITELLM_TIMEOUT_SECONDS`); явный `httpx.Timeout(connect/pool/read/write)`; stream при **4xx** от upstream — SSE `data: {"error":...}` + `[DONE]` и лог `litellm_stream_upstream_error` вместо `raise_for_status` до первого чанка.
- `versions_dep/v2_c2/scripts/verify_stack.sh` — проверка injection не падает с exit 2 при отключённом guardrail.
- **v3:** автовыбор модели (**`AUTO_ROUTE_MODEL`**) по умолчанию **`true`**: `settings.py`, `docker-compose.yml`, `.env.example`; поведение «модель из UI» — явное `false`.
- **v3 orchestrator:** прокси **`GET /v1/models`** → LiteLLM (для списка моделей в Open WebUI).
- **v3 compose / `.env.example`:** **`DEFAULT_MODELS`**, **`DEFAULT_PINNED_MODELS`** — чтобы в UI не было пустого «Выберите модель» при первом запуске (см. PersistentConfig в доке Open WebUI).
- **v3 `embedding-shim`:** контейнер нормализует ответ hybrid BGE (`dense_embedding` → `embedding`) для Open WebUI RAG / PDF в чате; `RAG_OPENAI_API_BASE_URL` по умолчанию `http://embedding-shim:8000/v1`.

### Added

- **v3 orchestrator — OpenRouter free roles:** `gpthub_orchestrator/data/model_roles.yaml` (роли → цепочки LiteLLM-алиасов), `model_registry.py`, расширенный `router.py` и `classifier.py` (`summarization` / длинный текст → `doc_synthesis`). Настройки: `CODE_ROUTE_PREFERENCE`, `ORCHESTRATOR_LITELLM_FALLBACK`, `ORCHESTRATOR_FALLBACK_MAX_ATTEMPTS`, `MODEL_ROLES_PATH`. Non-stream: перебор алиасов при **429/503**; stream — заголовок trace + одна попытка.
- **CLI:** `python -m gpthub_orchestrator.tools.list_free_models` — список моделей OpenRouter с нулевым prompt+completion pricing (для обновления whitelist).
- **`versions_dep/v2_c2/litellm/config.yaml`:** алиасы `gpt-hub-fast`, `gpt-hub-doc`, `gpt-hub-reasoning-or`, `gpt-hub-fallback` (OpenRouter free) и расширенные `fallbacks`.

### Changed

- `versions_dep/v2_c2/litellm/config.yaml` — см. **Added** выше: алиасы strong / vision / turbo плюс **fast, doc, reasoning-or, fallback** (OpenRouter free) и матрица **fallbacks** для ролевого роутера v3; `TASK_MODEL_EXTERNAL` по умолчанию `gpt-hub-strong`.
- `versions_dep/v2_c2/README.md` — раздел **PDF и файлы в чате**; уточнена строка таблицы **gpt-hub-turbo** (text-only).
- `versions_dep/v2_c2/scripts/verify_stack.sh` — ручной смоук PDF в конце прогона.

### Changed

- `versions_dep/v3/ROADMAP.md` — детальный план реализации фаз 1–5: подзадачи, зависимости, матрица тестов, критерии приёмки; v2 зафиксирован как замороженный эталон для LiteLLM.

### Added

- `versions_dep/v3` — **GPTHub Workspace (скелет):** [ARCHITECTURE.md](versions_dep/v3/ARCHITECTURE.md), [ROADMAP.md](versions_dep/v3/ROADMAP.md), [README.md](versions_dep/v3/README.md), [CONTINUATION.md](versions_dep/v3/CONTINUATION.md) (handoff для нового чата); FastAPI **orchestrator** (`apps/orchestrator`, `uv` + `pytest`); [docker-compose.yml](versions_dep/v3/docker-compose.yml): WebUI → orchestrator (:8089) → LiteLLM; конфиг LiteLLM монтируется из `v2_c2/litellm/config.yaml`.

- `versions_dep/v2_c2` — **`LLM_INSTRUCT_API_BASE`** / **`LLM_INSTRUCT_API_KEY`** в `docker-compose.yml` (сервис `litellm`) и `.env.example`; README и ROADMAP — описание **gpt-hub-turbo** и различие портов **8002** vs **9002**; `scripts/verify_stack.sh` — при непустом `LLM_INSTRUCT_API_BASE` проверка `…/healthz` gateway и короткий completion на `gpt-hub-turbo`.
- `versions_dep/v2_c2/litellm/config.yaml` — callback **`detect_prompt_injection`** ([док](https://docs.litellm.ai/docs/proxy/guardrails/prompt_injection)); скрипт проверки [scripts/verify_stack.sh](versions_dep/v2_c2/scripts/verify_stack.sh).
- `versions_dep/v2_c2/docker-compose.yml` — env безопасности Open WebUI (`ENABLE_SIGNUP`, `DEFAULT_USER_ROLE`, `ENABLE_PERSISTENT_CONFIG`, `ENABLE_PASSWORD_VALIDATION`, `WEBUI_ADMIN_*`).
- `versions_dep/v2_c2/README.md` — разделы **Baseline snapshot**, **Безопасность**; [CONSTRUCTOR.md](CONSTRUCTOR.md) §12 — риск injection; [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md) — формулировка для жюри.
- `versions_dep/v2_c2/.env.example` — блок переменных безопасности Open WebUI.
- `versions_dep/v2_c2/docker-compose.yml` + `.env.example` — **ASR/STT**: `AUDIO_STT_ENGINE=openai`, база `host.docker.internal:8001/v1`, модель Whisper из скилла `remote-asr-service`; README и `verify_stack.sh` (опциональная проверка `:8001/healthz`).

- `versions_dep/v2_c2/litellm/config.yaml` — **`gpt-hub-vision`** (VL) + **`fallbacks`** с `gpt-hub-fast` / `gpt-hub-strong` на vision при ошибке (текст+картинка без смены модели в UI); `num_retries: 2`.
- `versions_dep/v2_c2` — RAG: embedding + rerank на хосте; `ENABLE_MEMORIES`, `TASK_MODEL_EXTERNAL`, `WEBUI_URL`; `extra_hosts` для Linux.

### Changed

- `versions_dep/v2_c2/ROADMAP.md` — **пауза до 10.04** и пошаговый **чеклист после публикации Задачи**; [versions_dep/v2_c2/README.md](versions_dep/v2_c2/README.md) «Переход на MWS» — отсылка к ROADMAP; корневой [README.md](README.md) — строка про паузу.
- `versions_dep/v2_c2` — ASR: `AUDIO_STT_SUPPORTED_CONTENT_TYPES` в compose; README (микрофон + вложения, UI, PersistentConfig, TailScale vs `host.docker.internal`); `verify_stack.sh` — база ASR из `LOCAL_AI_ASR_BASE_URL` / `AUDIO_STT_OPENAI_API_BASE_URL`; `.env.example` — плейсхолдеры и MIME/`AIOHTTP_CLIENT_TIMEOUT`.
- `versions_dep/v2_c2/docker-compose.yml` — Open WebUI **v0.6.20 → v0.8.12** ([releases](https://github.com/open-webui/open-webui/releases)); после `docker compose pull` возможны миграции данных в volume.
- `versions_dep/v2_c2/litellm/config.yaml` — явные OpenRouter free-slug’и (обход 502 у `openrouter/free` в LiteLLM); `gpt-hub-strong` временно совпадает с `gpt-hub-fast` до выбора отдельной «тяжёлой» free-модели.
- `versions_dep/v2_c2/ROADMAP.md` — таблица «текущее состояние», отмечены фазы 1–2.
- `versions_dep/v2_c2/README.md` — раздел «Статус стека», уточнения про OpenRouter и Free Router.
- `.gitignore` — `compose-setup.log`.
- Корневой `README.md` — строка про прогресс v2_c2 и ссылка на ROADMAP.

### Added

- `versions_dep/v2_c2/` — Docker Compose: LiteLLM Proxy (pin по digest) + Open WebUI, `litellm/config.yaml`, `.env.example`, README (OpenRouter), `ROADMAP.md`; в `litellm/config.yaml` закомментирован блок MWS; compose — `OPENROUTER_*`, `OR_*`.
- `CONSTRUCTOR.md` — карта сборки OSS, дедлайны True Tech Hack, мульти-бэкенд, риски.
- `docs/PITCH-DEMO.md` — питч, сценарий демо 60–90 с, чеклист сдачи и финала.
- `README.md` — входная точка и ссылки.
- `.env.example` — плейсхолдеры переменных окружения.
- `.gitignore` — исключение `.env` и секретов.
- `GPTHub-github-stack.md` сведён к отсылке на `CONSTRUCTOR.md`.
