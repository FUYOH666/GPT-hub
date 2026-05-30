# Передача контекста: продолжение разработки v3 (новый чат)

Скопируйте этот файл или раздел **«Промпт для нового чата»** в начало следующей сессии. Репозиторий: **GPT-hub** (True Tech Hack 2026, кейс MWS GPT).

---

## Где мы сейчас

| Ветка работы | Статус |
|--------------|--------|
| **v2_c2** (`versions_dep/v2_c2`) | **Заморозка.** Протестированный стек Open WebUI + LiteLLM напрямую. Конфиг алиасов LLM: `v2_c2/litellm/config.yaml` — **v3 монтирует этот же файл** (не дублировать правки в двух местах). |
| **v3** (`versions_dep/v3`) | **Активная разработка.** GPTHub Workspace: Open WebUI → **FastAPI orchestrator** → LiteLLM. Документы: [ARCHITECTURE.md](ARCHITECTURE.md), детальный план: [ROADMAP.md](ROADMAP.md). |

**Следующая работа по плану:** [ROADMAP.md](ROADMAP.md) — **Фаза 1** (Perception: разбор payload WebUI, ingest PDF/image/audio, Context Artifacts, интеграция в `main.py`).

---

## Docker: остановить v2, не конфликтовать с v3

Оба стека по умолчанию занимают **порты 3000** (WebUI) и **4000** (LiteLLM). Одновременно не поднимать.

### Контейнеры v2_c2 (старые имена)

- `gpthub-litellm`
- `gpthub-open-webui`

Остановка из каталога v2:

```bash
cd versions_dep/v2_c2
docker compose down
```

### Контейнеры v3

- `gpthub-v3-litellm`
- `gpthub-v3-orchestrator`
- `gpthub-v3-open-webui`
- `gpthub-v3-embedding-shim` — только с профилем **`rag`** (нужен BGE на хосте :9001)

Запуск:

```bash
cd versions_dep/v3
cp .env.example .env   # если ещё нет
docker compose up -d --build
# С RAG (embedding-shim): docker compose --profile rag up -d --build
```

Остановка v3:

```bash
cd versions_dep/v3
docker compose down
```

### Очистка (опционально)

- Только остановить: `docker compose down` (volumes по умолчанию **сохраняются** — данные WebUI останутся).
- Удалить volume WebUI **v2**: в `v2_c2` в compose volume назывался `open-webui-data` — при `docker compose down -v` **сотрётся история чатов v2** (осознанно).
- Удалить volume WebUI **v3**: в v3 volume `open-webui-v3-data`; `docker compose down -v` в каталоге v3.
- Образы неиспользуемые: `docker image prune` (осторожно, глобально по хосту).

Проверка, что ничего не слушает 3000/4000:

```bash
lsof -i :3000 -i :4000
# или
docker ps --format '{{.Names}}\t{{.Ports}}'
```

---

## Цепочка запросов v3

```text
Браузер → Open WebUI :3000
  → OPENAI_API_BASE_URL=http://orchestrator:8000/v1
  → gpthub-v3-orchestrator :8089 (с хоста) — прокси **GET /v1/models** и **POST /v1/chat/completions**
  → http://litellm:4000/v1/…
  → OpenRouter / MWS / свой :8002 (как в config.yaml)
```

- Ключ для WebUI и проверки оркестратора: **`LITELLM_MASTER_KEY`** (тот же Bearer).
- Оркестратор: `GET http://localhost:8089/healthz`
- Trace: логи контейнера `gpthub-v3-orchestrator`, заголовок ответа **`X-GPTHub-Trace`** (base64 JSON) для не-stream запросов.
- PDF+RAG: `embedding-shim` + BGE :9001; в LiteLLM **без** `detect_prompt_injection` (ложные 400 на длинный документ). При `TransferEncodingError` в UI — см. [README.md](README.md) (`LITELLM_TIMEOUT_SECONDS`, логи `litellm_stream_upstream_error`).
- Автовыбор модели: **по умолчанию включён** (`AUTO_ROUTE_MODEL=true` в compose и оркестраторе); выключить — `false` в `.env` и перезапуск orchestrator (см. [README.md](README.md)).

---

## Локальная разработка orchestrator (без полного compose)

```bash
cd versions_dep/v3/apps/orchestrator
uv sync
export LITELLM_BASE_URL=http://127.0.0.1:4000
export ORCHESTRATOR_API_KEY=<тот же что LITELLM_MASTER_KEY>
uv run pytest -q
uv run uvicorn gpthub_orchestrator.main:app --reload --port 8089
```

Нужен запущенный LiteLLM (например из `docker compose up litellm` в v3 или v2 — только один на :4000).

---

## Внешние сервисы (MacBook + TailScale)

В **docker-compose v3** Open WebUI по умолчанию ходит на хост:

- **BGE embeddings:** `host.docker.internal:9001`
- **Reranker:** `host.docker.internal:9002`
- **ASR (STT):** `host.docker.internal:8001`

На практике в `.env` часто ставят **TailScale IP** GPU-сервера для ASR (и при необходимости тот же хост для :8002 instruct в LiteLLM). **Не коммитить** реальные IP — только `.env.example` с плейсхолдерами.

Полезные **Cursor skills** (если включены у пользователя):

- `remote-llm-service` — instruct :8002, thinking :8005
- `remote-asr-service` — Whisper :8001
- `remote-embedding-service`, `remote-reranker-service` — BGE :9001 / :9002
- `tailscale-networking` — диагностика сети

---

## Инженерные правила репозитория

- Python: **`uv`** (`pyproject.toml`, `uv.lock` в `apps/orchestrator`).
- Логи: `logging`, не `print`.
- Секреты: только `.env`, в git — [`.env.example`](.env.example).
- Корневой **[CONSTRUCTOR.md](../../CONSTRUCTOR.md)** — общая карта хакатона; **[CHANGELOG.md](../../CHANGELOG.md)** — фиксировать значимые изменения.

---

## Промпт для нового чата (скопировать)

```
Продолжаем GPTHub versions_dep/v3 (GPTHub Workspace). v2_c2 заморожен; LiteLLM config общий: versions_dep/v2_c2/litellm/config.yaml.

Прочитай для контекста:
- versions_dep/v3/CONTINUATION.md
- versions_dep/v3/ROADMAP.md (следующая работа — Фаза 1 Perception)
- versions_dep/v3/ARCHITECTURE.md

Стек: Open WebUI → FastAPI orchestrator (apps/orchestrator, uv) → LiteLLM. Порты v3: 3000 WebUI, 4000 LiteLLM, 8089 orchestrator. Перед запуском v3 останови v2: cd versions_dep/v2_c2 && docker compose down.

Задача: реализовать следующий пункт из ROADMAP (Фаза 1).
```

---

## Файлы по смыслу

| Файл | Назначение |
|------|------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Рецепт: perception → context → LLM, что не делаем |
| [ROADMAP.md](ROADMAP.md) | Пошаговая реализация фаз 1–5, тесты, приёмка |
| [README.md](README.md) | Быстрый старт, env |
| [docker-compose.yml](docker-compose.yml) | Сервисы и сети |
| `apps/orchestrator/gpthub_orchestrator/` | Код оркестратора |
