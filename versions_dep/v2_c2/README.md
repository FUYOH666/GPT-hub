# GPTHub v2_c2 — Open WebUI + LiteLLM

Каркас под [CONSTRUCTOR.md](../../CONSTRUCTOR.md) и [docs/PITCH-DEMO.md](../../docs/PITCH-DEMO.md). Архив старого описания: [../v1_z/LEGACY.md](../v1_z/LEGACY.md).

## Статус стека

После `docker compose up -d`: **LiteLLM** — http://localhost:4000 (`/health/liveliness` → «I'm alive!»), **Open WebUI** — http://localhost:3000 (HTTP 200). Проверка completion: `POST /v1/chat/completions` на :4000 с заголовком `Authorization: Bearer <LITELLM_MASTER_KEY>` и телом `{"model":"gpt-hub-strong","messages":[...]}`.

Актуальные slug’и OpenRouter в [litellm/config.yaml](litellm/config.yaml) (free-модели меняются — сверяйте с [openrouter.ai/models?pricing=free](https://openrouter.ai/models?pricing=free)). **Open WebUI** в compose зафиксирован тегом **`v0.8.12`** ([релизы](https://github.com/open-webui/open-webui/releases)); обновление: `docker compose pull && docker compose up -d`. Заморозка и шаги после Задачи: [ROADMAP.md](ROADMAP.md). Детальный бэклог разработки: [../v3/ROADMAP.md](../v3/ROADMAP.md).

## Baseline snapshot

Зафиксированное состояние каркаса (для отката/сдачи; обновляйте при смене образов):

| Параметр | Значение |
|----------|----------|
| Дата | 2026-04-02 |
| Open WebUI | `ghcr.io/open-webui/open-webui:v0.8.12` |
| LiteLLM | digest в [docker-compose.yml](docker-compose.yml) (`ghcr.io/berriai/litellm@sha256:…`) |
| Guardrails | По умолчанию **выключено** (`detect_prompt_injection` убран) — иначе RAG/PDF ловят 400 «prompt injection»; включить см. комментарий в [litellm/config.yaml](litellm/config.yaml) |
| LLM | OpenRouter free: `gpt-hub-strong`, `gpt-hub-vision`; свой GPU instruct :8002: **`gpt-hub-turbo`** (`LLM_INSTRUCT_API_*`, модель в config под `GET /v1/models`) |

После **10.04** сверьте [CONSTRUCTOR.md](../../CONSTRUCTOR.md) с текстом Задачи и при необходимости обновите `model_list` / env.

## Безопасность

**LiteLLM:** опциональный callback [`detect_prompt_injection`](https://docs.litellm.ai/docs/proxy/guardrails/prompt_injection) — в общем [config.yaml](litellm/config.yaml) **отключён**, потому что длинный текст из PDF/RAG часто даёт ложный **HTTP 400** и обрыв stream в Open WebUI. Включайте осознанно для публичного API без RAG.

**Open WebUI:** в [docker-compose.yml](docker-compose.yml) проброшены переменные из [.env.example](.env.example): `ENABLE_SIGNUP`, `DEFAULT_USER_ROLE`, `ENABLE_PERSISTENT_CONFIG`, `ENABLE_PASSWORD_VALIDATION`, опционально `WEBUI_ADMIN_*` для первого админа на пустой БД. Для публичного демо задайте в `.env` как минимум `ENABLE_SIGNUP=false` и сильные `WEBUI_SECRET_KEY` / `LITELLM_MASTER_KEY`. Учтите [PersistentConfig](https://github.com/open-webui/docs/blob/main/docs/reference/env-configuration.mdx): при расхождении с БД используйте `ENABLE_PERSISTENT_CONFIG=false` или правку в админке.

**Проверка:** при запущенном compose из каталога `versions_dep/v2_c2`:

```bash
./scripts/verify_stack.sh
```

Скрипт проверяет health, успешный completion и отклонение строки вида «Ignore previous instructions…». Если injection проходит с **HTTP 200**, пересоздайте прокси: `docker compose up -d --force-recreate litellm`. После смены env безопасности WebUI: `docker compose up -d --force-recreate open-webui`.

## Быстрый старт

```bash
cd versions_dep/v2_c2
cp .env.example .env
# В .env вставьте OPENROUTER_API_KEY; для RAG поднимите BGE embedding :9001 и reranker :9002 на хосте (или поправьте URL в .env).
docker compose up -d
```

- **Open WebUI:** http://localhost:3000  
- **LiteLLM Proxy:** http://localhost:4000  

В Open WebUI подключение к «OpenAI» уже задаётся compose (`OPENAI_API_BASE_URL` → LiteLLM, ключ = `LITELLM_MASTER_KEY`). Модели в [litellm/config.yaml](litellm/config.yaml):

| Имя в UI | Назначение |
|----------|------------|
| **gpt-hub-strong** | Текст: **Qwen3.6 Plus Preview (free)** через OpenRouter. При ошибке на запросе **с картинкой** LiteLLM делает **fallback** на **gpt-hub-vision** ([reliability / fallbacks](https://docs.litellm.ai/docs/proxy/reliability)). |
| **gpt-hub-vision** | Картинка+текст: **Google Gemma 3 27B IT (free)** — отдельный выбор или автоматически после fallback. |
| **gpt-hub-turbo** | Свой **instruct** на GPU (**порт 8002**). **Только текст** (текущая модель не multimodal): для **PDF, картинок и сканов** в чате выбирайте **gpt-hub-vision**. При мультимодальном запросе LiteLLM уходит в vision, затем при **429** на OpenRouter — в **gpt-hub-strong** (см. `fallbacks` в [litellm/config.yaml](litellm/config.yaml); чисто мультимодальный запрос strong может не принять). Скилл: `remote-llm-service`. |

**Порты:** чат через LiteLLM — **4000**; ASR (STT) — **8001**; instruct для **turbo** — **8002**; BGE эмбеддинги на Mac — **9001**, rerank — **9002** (не путать с 8002).

### PDF и файлы в чате

- **Почему растёт нагрузка GPU на Mac при PDF:** Open WebUI при вложении часто **извлекает текст и индексирует** чанки → вызовы **`POST /v1/embeddings`** (и при включённом rerank — **`/v1/rerank`**) на **хост** `:9001` / `:9002` (BGE на MPS). Это **не** LiteLLM и не модель на :8002.
- **Какую модель выбрать:** PDF / изображение в сообщении — **gpt-hub-vision**. **gpt-hub-turbo** — код и обычный текст без вложений-медиа.
- Сообщение вроде «Источники не найдены» означает, что RAG-поиск по контексту вложения не нашёл релевантных чанков; нагрузка на BGE при этом всё равно могла быть.

### Память и RAG (BGE на хосте)

- **Memories** — в compose включено `ENABLE_MEMORIES=true` (фича [долгосрочной памяти](https://github.com/open-webui/docs/blob/main/docs/reference/env-configuration.mdx) Open WebUI). Управление в UI: настройки чата / память.
- **RAG (Knowledge)** — `RAG_EMBEDDING_ENGINE=openai` и `RAG_OPENAI_*` указывают на **OpenAI-совместимый** сервис эмбеддингов (`POST /v1/embeddings`). По умолчанию **host.docker.internal:9001** — ваш BGE-M3 на Mac (см. скилл `remote-embedding-service`); на Linux `extra_hosts: host-gateway` уже в compose.
- **Rerank** — `RAG_RERANKING_ENGINE=external`, `RAG_EXTERNAL_RERANKER_URL` = полный URL до **`/v1/rerank`** (по умолчанию порт **9002**, скилл `remote-reranker-service`). Отключить rerank: в `.env` задайте пустой `RAG_RERANKING_ENGINE=` и перезапустите `open-webui`.
- **Фоновые задачи** (заголовки чатов и т.д.): `TASK_MODEL_EXTERNAL=gpt-hub-strong` — тот же LiteLLM.

Переменные см. [.env.example](.env.example). Официальный список env: [env-configuration](https://github.com/open-webui/docs/blob/main/docs/reference/env-configuration.mdx).

**Проверка сервисов на хосте:** `curl -sS http://127.0.0.1:9001/healthz` и `:9002/healthz` → `status: ok`. Из контейнера: `docker exec gpthub-open-webui curl -sS http://host.docker.internal:9001/healthz`.

**Совместимость с BGE:** ваш сервис требует `input` в виде **JSON-массива** строк. В **Open WebUI v0.8.x** путь RAG для OpenAI-совместимых эмбеддингов формирует запрос как `{'input': texts, 'model': ...}`, где `texts` — список (в т.ч. батч из одного чанка), см. [`retrieval/utils.py`](https://github.com/open-webui/open-webui/blob/v0.8.12/backend/open_webui/retrieval/utils.py) (`agenerate_openai_batch_embeddings`). Поэтому связка **стабильна** для индексации Knowledge; при сбоях смотрите логи `gpthub-open-webui` и ответ upstream на `/v1/embeddings`.

### ASR / голос (порт 8001)

Open WebUI шлёт аудио на **OpenAI-compatible** endpoint `POST …/v1/audio/transcriptions` (тот же формат, что в скилле `remote-asr-service`). В [docker-compose.yml](docker-compose.yml) это задано **отдельно** от чата с LLM (`OPENAI_API_*` → LiteLLM).

**Что попадает на ваш ASR**

- **Иконка микрофона** — после сохранения записи бэкенд WebUI вызывает транскрипцию с тем же движком, что и для файлов (см. `transcription_handler` в [audio.py v0.8.12](https://github.com/open-webui/open-webui/blob/v0.8.12/backend/open_webui/routers/audio.py)).
- **Вложения аудио** (wav, mp3, webm и т.д.) — при поддерживаемом MIME запрос идёт в тот же пайплайн → тот же URL ASR.

**Переменные (см. [.env.example](.env.example))**

| Переменная | Назначение |
|------------|------------|
| `AUDIO_STT_ENGINE` | `openai` — внешний Whisper-совместимый endpoint |
| `AUDIO_STT_OPENAI_API_BASE_URL` | База с **`/v1`**, по умолчанию `http://host.docker.internal:8001/v1` |
| `AUDIO_STT_OPENAI_API_KEY` | Заголовок `Authorization` (если ASR без auth — оставьте `local-asr`) |
| `AUDIO_STT_MODEL` | Имя модели на стороне ASR, по умолчанию `cstr/whisper-large-v3-turbo-int8_float32` |
| `AUDIO_STT_SUPPORTED_CONTENT_TYPES` | По умолчанию в compose: `audio/*,video/webm` (как дефолт Open WebUI при пустом списке) |

**Сеть:** с контейнера должен открываться **тот же хост:порт**, что в `AUDIO_STT_OPENAI_API_BASE_URL`. На многих машинах с Tailscale контейнер Open WebUI **достучится до TailScale IP** GPU-сервера — тогда в **локальном** `.env` задайте `LOCAL_AI_ASR_BASE_URL` и `AUDIO_STT_OPENAI_API_BASE_URL=…/v1` (хост из скилла `remote-asr-service`, без коммита в git). Если из контейнера 100.x недоступен, используйте проброс `ssh -L 8001:127.0.0.1:8001 …` и вариант `host.docker.internal:8001/v1` из compose по умолчанию.

**UI (обязательно проверить)**

1. **Пользователь:** Settings → Audio → Speech-to-Text — режим **Default** (не **Web API** браузера), иначе микрофон **не** пойдёт на сервер :8001.  
2. **Админ:** Admin → Settings → Audio — движок **OpenAI**, URL/ключ совпадают с env или задайте те же значения вручную.  
3. Если в админке уже сохранялись другие значения, сработает **PersistentConfig**: либо выставьте в `.env` `ENABLE_PERSISTENT_CONFIG=false` и пересоздайте контейнер, либо поправьте Audio в UI.

**Проверка:** `./scripts/verify_stack.sh` — подставляет базу ASR из `LOCAL_AI_ASR_BASE_URL` или `AUDIO_STT_OPENAI_API_BASE_URL` в `.env` и проверяет `/healthz` **с хоста и из контейнера**. Документация env: [env-configuration](https://github.com/open-webui/docs/blob/main/docs/reference/env-configuration.mdx), STT: [stt-config](https://docs.openwebui.com/features/media-generation/audio/speech-to-text/stt-config/).

### Бесплатные модели и Free Models Router

[Free Models Router](https://openrouter.ai/docs/guides/routing/routers/free-models-router) (`openrouter/free`) на стороне OpenRouter подбирает free-модель под запрос. В связке **LiteLLM Proxy + `openrouter/free`** у нас встречались ответы **502** (провайдер Stealth / `Invalid URL`), поэтому в конфиге заданы **явные** `openrouter/…:free` slug’и.

В `litellm/config.yaml` заданы **два** алиаса под [free-модели OpenRouter](https://openrouter.ai/models?pricing=free); slug’и меняются — при 404/502 проверьте актуальные id. У **Qwen3.6 Plus (free)** в карточке модели указан сбор данных промптов для обучения — учитывайте для чувствительных данных.

## OpenRouter (локальный тест)

1. Ключ: [openrouter.ai/keys](https://openrouter.ai/keys).  
2. В `.env`: `OPENROUTER_API_KEY`; при желании поправьте `OR_SITE_URL` / `OR_APP_NAME` (для OpenRouter stats).

## Переход на MWS

До **10.04** стек можно не трогать: см. **«Пауза до 10.04»** и полный **чеклист после Задачи** в [ROADMAP.md](ROADMAP.md).

1. Текст **Задачи** на [truetecharena.ru](https://truetecharena.ru/) (10.04.2026 12:00 МСК).  
2. В [litellm/config.yaml](litellm/config.yaml) замените активный `model_list` на блок MWS из комментария в том же файле; укажите реальные `REPLACE_WITH_MWS_MODEL_ID_*`.  
3. В `.env` задайте `MWS_GPT_API_BASE` и `MWS_GPT_API_KEY`.  
4. Пересоздайте контейнеры и прогоните `./scripts/verify_stack.sh` — см. ROADMAP.

## LiteLLM: безопасность версий

- **CVE-2025-0330** (утечка ключей Langfuse в прокси): не использовать затронутые версии; см. [GitLab advisory](https://advisories.gitlab.com/pkg/pypi/litellm/CVE-2025-0330).
- **Март 2026 (supply chain PyPI):** скомпрометированы **`litellm` 1.82.7 и 1.82.8** на PyPI. Не ставить эти версии через pip без pin. Официальный пост: [Security Update March 2026](https://docs.litellm.ai/blog/security-update-march-2026).
- В этом compose образ **зафиксирован по digest** (снимок `ghcr.io/berriai/litellm:main-stable` на момент сборки каркаса). Перед продакшеном/демо перепроверьте блог безопасности и при необходимости обновите образ и digest. Тег **`v1.83.0` на GHCR может отсутствовать** — ориентируйтесь на официальные релизы и verified builds.

Для зависимостей через **pip/uv** в своём коде всегда фиксируйте версию `litellm` в lock-файле.

## Дорожная карта

Заморозка v2 и пост-Задача: [ROADMAP.md](ROADMAP.md). Активные фазы: [../v3/ROADMAP.md](../v3/ROADMAP.md).
