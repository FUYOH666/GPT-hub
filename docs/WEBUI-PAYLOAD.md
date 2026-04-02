# Open WebUI v0.8.12 — контракт `messages` для оркестратора

Документ для **фазы 1** ingest: что ожидать в теле `POST /v1/chat/completions` от Open WebUI к API (оркестратор как `OPENAI_API_BASE_URL`).

## Общая форма

- `messages`: массив объектов `{ "role": "system" | "user" | "assistant", "content": ... }`.
- `content` у **user** может быть:
  - **строка** — только текст;
  - **массив частей** — мультимодальный OpenAI-совместимый формат.

## Текст

```json
{ "role": "user", "content": "Привет, что умеешь?" }
```

## Изображение (`image_url`)

Часто встречается часть:

```json
{
  "type": "image_url",
  "image_url": { "url": "data:image/png;base64,..." }
}
```

или HTTP(S) URL. Оркестратор **не вырезает** такие части: они уходят в LiteLLM; классификатор помечает модальность `image`, роутер выбирает vision-алиас.

## Файл в чате (PDF и др.)

Open WebUI может отправить вложение как часть типа **`file`** с полем **`file_data`** — data URL:

```json
{
  "type": "file",
  "file": {
    "filename": "report.pdf",
    "file_data": "data:application/pdf;base64,JVBERi0xLjQK..."
  }
}
```

Оркестратор **ingest** (если `INGEST_ENABLED=true`):

- для `application/pdf` извлекает текст (`pypdf`), кладёт артефакт `document_text`, добавляет system-блок с контекстом и убирает соответствующую часть из user `content`;
- см. [versions_dep/v3/apps/orchestrator/gpthub_orchestrator/ingest/parts.py](../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/ingest/parts.py).

Другие MIME через тот же механизм `file` пока не обрабатываются отдельно (расширение — по ROADMAP).

## Аудио

Возможны части с типом **`input_audio`** / **`audio`** и base64 или data URL (зависит от клиента). При настроенном **`ORCHESTRATOR_ASR_*`** оркестратор вызывает OpenAI-совместимый **`POST /v1/audio/transcriptions`** и добавляет артефакт `transcript`.

## Уточнение по факту

Точная форма может меняться с версией WebUI. Для спорных кейсов сохраняйте **лог тела запроса** (без секретов) или HAR и дополняйте этот файл.
