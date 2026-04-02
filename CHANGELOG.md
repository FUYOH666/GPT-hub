# Changelog

## [Unreleased]

### Added

- [docs/CLOUDFLARE_TUNNEL_HANDOFF.md](docs/CLOUDFLARE_TUNNEL_HANDOFF.md) — готовый текст задачи для специалиста / Cloudflare Community; шаблон [versions_dep/v3/deploy/cloudflared/config.example.yml](versions_dep/v3/deploy/cloudflared/config.example.yml).
- [AUTHORS.md](AUTHORS.md) — авторство (Aleksandr Mordvinov / [@FUYOH666](https://github.com/FUYOH666)); раздел в [README.md](README.md); поля `authors` / `[project.urls]` в [versions_dep/v3/apps/orchestrator/pyproject.toml](versions_dep/v3/apps/orchestrator/pyproject.toml).
- [docs/PRIVATE_REPO_SETUP.md](docs/PRIVATE_REPO_SETUP.md) — приватный репозиторий GitHub (`gh repo create` или веб + `git push`).
- [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) — публичный HTTPS для Open WebUI (VPS / туннель), `WEBUI_URL`, WebSocket/SSE, чеклист безопасности, ограничения RAG/ASR на VPS.
- [docs/AGENT_HANDOFF_SCANOVICH.md](docs/AGENT_HANDOFF_SCANOVICH.md) и корневой [AGENTS.md](AGENTS.md) — краткий handoff для агента другого репозитория.
- [versions_dep/v1_z/LEGACY.md](versions_dep/v1_z/LEGACY.md) — архив бывшего `readme.md` v1_z; актуальный стек описан в v3.

### Changed

- [docs/TEAM_PUBLIC_ACCESS.md](docs/TEAM_PUBLIC_ACCESS.md) — переструктурировано: сценарий Mac + Docker + туннель + Tailscale к GPU; сценарий VPS; канон деплоя; витрина отдельно от стека. [README.md](README.md), [AGENTS.md](AGENTS.md), [docs/AGENT_HANDOFF_SCANOVICH.md](docs/AGENT_HANDOFF_SCANOVICH.md) — ссылки обновлены.
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
