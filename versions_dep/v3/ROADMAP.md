# GPTHub Workspace v3 — дорожная карта

Архитектурный рецепт: [ARCHITECTURE.md](ARCHITECTURE.md).  
**v2_c2** — заморожен как эталон LiteLLM/Open WebUI; активная разработка — **только v3**.

---

## Порядок выполнения фаз (зависимости)

```text
Фаза 0 (готово)
     ↓
Фаза 1 — Perception + Context Artifacts + вызов LLM
     ↓
Фаза 2 — Память (user + workspace) …┐
     ↓                               │ можно частично параллелить
Фаза 3 — RAG по workspace …………….┘   (но RAG осмысленнее после chunking из фазы 1)
     ↓
Фаза 4 — UX trace (контракт + демо-клиент / панель)
     ↓
Фаза 5 — Качество PDF/vision (Marker, OCR, кэш)
```

**Рекомендация по времени:** сначала закрыть **фазу 1** end-to-end (один PDF + одна картинка + опционально аудио), затем **фазу 4** в минимальном виде (видимый trace), чтобы демо было объяснимым; память и RAG — следующими слоями.

---

## Фаза 0 — Скелет (сделано)

- [x] Документы: ARCHITECTURE, ROADMAP, README
- [x] `docker-compose`: LiteLLM + Orchestrator + Open WebUI
- [x] FastAPI orchestrator: `/healthz`, `POST /v1/chat/completions` → LiteLLM, trace в логах / заголовок
- [x] Modality classifier + model router (эвристики)
- [x] `pytest` (health + classifier), Docker build orchestrator

---

## Фаза 1 — Perception (MVP «закинул всё — получил ответ»)

**Цель:** любой запрос из Open WebUI с вложениями проходит: **нормализация → артефакты → дополненные messages → LiteLLM**.

### 1.1 Контракт входа (обязательно первым)

- [ ] Зафиксировать фактический JSON `messages` от **Open WebUI v0.8.12** для: только текст; PDF; картинка; аудио (лог оркестратора или HAR).
- [ ] Описать в `docs/WEBUI-PAYLOAD.md` (или раздел README): где лежат `image_url`, `file`, base64, ссылки на файлы WebUI.

### 1.2 Модуль `ingest/` в orchestrator

- [ ] `gpthub_orchestrator/ingest/models.py` — Pydantic: `RawAttachment`, `NormalizedArtifact` (поля как в ARCHITECTURE).
- [ ] `extract_openai_parts(messages)` — разбор последнего user message на текст / image_url / (прочие типы по мере обнаружения).

### 1.3 PDF path

- [ ] Зависимость: `pypdf` или `pdfplumber` (через `uv add`).
- [ ] Функция `parse_pdf_bytes(data) -> str` с лимитом размера и таймаутом; пустой текст → маркер «нужен OCR» в артефакте (реализация OCR — фаза 5).
- [ ] Юнит-тест: маленький PDF fixture.

### 1.4 Image path

- [ ] Если есть `image_url` (http/data URL) — скачать или декодировать base64; сохранить **краткое описание** либо передать в финальный запрос как multimodal **только если** выбрана vision-модель (согласовать с router: при артефакте `image` → `gpt-hub-vision`).
- [ ] Опционально (флажок env): один вызов vision-модели «опиши изображение для контекста» → артефакт `image_observation` (текст), финальный запрос — текстовый strong/turbo (дороже по токенам — задокументировать).

### 1.5 Audio path

- [ ] Настройки: `ASR_BASE_URL`, `ASR_API_KEY`, `ASR_MODEL` (как `AUDIO_STT_*` в v2 — те же семантики).
- [ ] `transcribe_audio_bytes` → `httpx` POST `.../v1/audio/transcriptions`; артефакт `transcript`.
- [ ] Интеграционный тест: mock ASR или skip если нет сервиса.

### 1.6 Параллель + контекст + вызов

- [ ] `asyncio.gather` для независимых вложений одного сообщения.
- [ ] `build_context_messages(user_messages, artifacts) -> list[dict]` — system block с JSON/markdown артефактов + исходный user query.
- [ ] Встроить в `main.py` **до** `httpx.post` в LiteLLM; trace дополнить полями `artifacts`, `ingest_ms`.
- [ ] **Приёмка фазы 1:** вручную — PDF «что здесь?» с `AUTO_ROUTE_MODEL=true` и vision при картинке; в логах полный trace с непустыми `artifacts`.

---

## Фаза 2 — Память

**Цель:** два слоя — **user** и **workspace**; retrieval перед финальным LLM.

### 2.1 Хранилище

- [ ] Выбор: **SQLite** (файл в `data/`) для скорости хакатона или Postgres + pgvector (если уже есть инфра).
- [ ] Схема: таблицы `user_profile`, `user_memory_entries`, `workspace_meta`, `workspace_memory_entries` (id, user_id, workspace_id, content, created_at, embedding_id nullable).
- [ ] Миграции: `alembic` или простой `CREATE TABLE` при старте (явно залогировать).

### 2.2 Embeddings для памяти

- [ ] Переиспользовать BGE endpoint (`RAG_OPENAI_*` из compose) для `text-embedding-3`-совместимого вызова или ваш `BAAI/bge-m3`.
- [ ] Retrieval: top-k по косинусу (если pgvector/SQLite-vec) или пока **полнотекст + лимит** без векторов (MVP-упрощение — зафиксировать в README).

### 2.3 API / use-case

- [ ] `retrieve_memory(user_id, workspace_id, query) -> list[str]`
- [ ] `write_memory(...)` — вызов после ответа (async fire-and-forget или sync MVP) с **жёстким лимитом** длины.
- [ ] Идентификаторы `user_id` / `workspace_id`: из заголовков `X-GPTHub-User-Id` / `X-GPTHub-Workspace-Id` (опционально) или константы MVP + TODO.

### 2.4 Интеграция в pipeline

- [ ] После ingest, перед LLM: дописать в system контекст «релевантная память».
- [ ] **Приёмка:** два запроса подряд с одним workspace; второй видит факт из первого (e2e ручной).

---

## Фаза 3 — RAG по workspace

**Цель:** ответы с опорой на файлы workspace, не путать с RAG Open WebUI (он остаётся для Knowledge UI при желании).

### 3.1 Индексация

- [ ] Загрузка/привязка файлов к `workspace_id` (метаданные в БД, файлы на диск `data/uploads/`).
- [ ] Chunking: старт с фиксированного размера + overlap; layout-aware — после фазы 5.

### 3.2 Retrieval

- [ ] Embeddings через тот же BGE; хранение векторов (таблица `chunks`).
- [ ] `retrieve_for_query(query, workspace_id) -> chunks`

### 3.3 Ответ

- [ ] В system prompt: «используй только следующие фрагменты» + citations в ответе (опционально).
- [ ] **Приёмка:** вопрос по содержимому загруженного файла workspace без галлюцинаций вне чанков (smoke).

---

## Фаза 4 — UX trace

**Цель:** trace виден не только в логах.

### 4.1 Контракт

- [ ] `docs/TRACE-SCHEMA.md` — JSON Schema или Pydantic-модель `ExecutionTraceV1`.

### 4.2 Доставка

- [ ] Вариант A: `GET /api/v1/traces/{request_id}` после `chat/completions` (нужен `request_id` в ответе — custom header `X-GPTHub-Request-Id`).
- [ ] Вариант B: статическая страница `apps/orchestrator/static/demo.html` + poll по request_id.
- [ ] Stream: trace только в логах + final chunk metadata (если получится без ломки OpenAI клиентов).

### 4.3 Демо

- [ ] `docs/DEMO_SCRIPT.md` — шаги для жюри (как в ARCHITECTURE §17).
- [ ] **Приёмка:** показать trace на экране за < 2 минуты сценария.

---

## Фаза 5 — Качество PDF / vision

**Цель:** инженерные PDF и сканы без деградации качества.

- [ ] Marker (или pymupdf layout) — зависимость и отдельный worker/таймаут.
- [ ] OCR fallback: один выбранный стек (Surya / DocTR / cloud) — зафиксировать в README.
- [ ] Кэш: `sha256(content)` → путь к нормализованному markdown в `data/cache/`.
- [ ] **Приёмка:** один сканированный PDF и один spec-PDF — читаемые заголовки/таблицы в артефакте (субъективно + чеклист).

---

## Не делаем (напоминание)

Multi-agent zoo, learned router, browser automation, billing, org RBAC — вне scope v3 MVP.

---

## Матрица тестирования

| Уровень | Что | Когда |
|---------|-----|--------|
| Unit | classifier, router, ingest PDF text, artifact builder | каждый PR / локально `uv run pytest` |
| Integration | orchestrator → LiteLLM (mock или реальный :4000), ASR mock | CI или вручную |
| E2E ручной | WebUI → PDF/картинка/голос → осмысленный ответ + trace | перед демо |
| Регрессия | `docker compose up`, health всех трёх сервисов | перед сдачей |

**Скрипт (запланировать):** `versions_dep/v3/scripts/verify_v3.sh` — curl health orchestrator + litellm + один non-stream completion с декодированием `X-GPTHub-Trace`.

---

## Критерии успеха

| Веха | Условие |
|------|---------|
| Фаза 1 закрыта | Текст + PDF + изображение (минимум два из трёх) дают ответ без «сырой» ошибки multimodal; trace содержит `artifacts`. |
| MVP продукт | Фаза 1 + фаза 4 (минимум); память или RAG — хотя бы один слой работает в демо. |
| Демо жюри | PDF + скрин + голос + текст; trace показывает этапы и модель; рассказ ≤ 2 мин. |

---

## Статус чеклиста (копия верхнего уровня)

### Фаза 1 — Perception

- [ ] PDF path (текст)
- [ ] Image path
- [ ] Audio path (ASR)
- [ ] Параллельный ingest
- [ ] Context Artifacts → prompt

### Фаза 2 — Память

- [ ] Схема + хранилище
- [ ] Retrieval + write
- [ ] Включение в pipeline

### Фаза 3 — RAG workspace

- [ ] Chunking + embeddings + retrieval + ответ

### Фаза 4 — UX trace

- [ ] Контракт + доставка + DEMO_SCRIPT

### Фаза 5 — Качество

- [ ] Marker/OCR/кэш
