# GPTHub Workspace v3 — архитектура (итоговый рецепт)

Цель: **не «чат с вложениями в одну VLM»**, а **orchestration runtime** с понятным пайплайном и trace.

Связь с [README.md](README.md) и [ROADMAP.md](ROADMAP.md). Предыдущий стек без оркестратора: [../v2_c2/README.md](../v2_c2/README.md).

---

## Принцип (зацементировать в продукте)

**Perception stack → Context construction → Final LLM**

Большая модель получает **уже подготовленный смысловой контекст** (артефакты), а не «сырой мир» целиком.

---

## Что берём из исследования

| Идея | В продукте |
|------|------------|
| Interfaze-style | Modality classifier + perception paths + тонкий контроллер (orchestrator) |
| Cost-aware routing | **Rule-based router v1** (эвристики по модальностям и ключевым словам), без learned router |
| Kimi / «swarm» | Только **параллельный preprocessing** (PDF / image / audio одновременно), без multi-agent театра |
| LiteLLM / gateway | Один **LLM gateway** за оркестратором: алиасы, fallback, единый вызов |
| Политики по роли | **System-промпты по роли маршрутизатора** (config-driven YAML), см. ROADMAP фаза 0.5 |
| Portkey-подобное | На MVP: **fallback** (уже в LiteLLM) + идея **кэша** позже |
| Marker / Surya / layout | PDF: text extract → OCR fallback → layout-aware chunking — **по фазам** (см. ROADMAP) |
| CLIP + YOLO + … | **Не в MVP** — vision v1: VLM или OCR + краткий артефакт |

---

## Что явно не делаем в MVP

- Learned / ML router **как замена** эвристическому роутеру; опциональный LLM-классификатор — только за явным флагом и приёмкой (см. ROADMAP 0.5.5)
- Complexity estimator «как в статье»
- Agent swarm, planner/critic/retrieval агенты
- CV-zoo отдельно от «инженерного скрина/PDF»
- Дублирование Portkey-level AI infra platform

---

## Целевая схема

```text
[ Open WebUI ]
      |
      v
[ GPTHub Orchestrator ]
      |
      +--> Modality Classifier
      |
      +--> Perception Stack (parallel where possible)
      |       ├── Text path
      |       ├── PDF path
      |       ├── Image path
      |       └── Audio path (STT)
      |
      +--> Context Construction (Context Artifacts)
      |
      +--> Memory Retrieval (user + workspace)  [фаза 2+]
      |
      +--> Model Router (rules v1)
      |
      +--> Final LLM (через LiteLLM gateway)
      |
      +--> Answer + Execution Trace
```

---

## Context Artifact (обязательная абстракция)

Не передаём в финальный LLM сырые байты без необходимости. Промежуточный вид:

```json
{
  "artifacts": [
    {
      "type": "document_text",
      "title": "Spec.pdf",
      "content": "…"
    },
    {
      "type": "image_observation",
      "title": "Screenshot",
      "content": "…"
    },
    {
      "type": "transcript",
      "title": "Voice note",
      "content": "…"
    }
  ]
}
```

Финальный LLM = **reasoning / synthesis** над артефактами + user query.

---

## Репозиторий (целевая структура, эволюция)

Сейчас в `versions_dep/v3` реализован **скелет**; пакеты можно вынести в `packages/*` без смены контрактов:

```text
versions_dep/v3/
├── apps/orchestrator/          # FastAPI, сейчас ядро MVP
├── docs/                       # этот файл + ROADMAP при желании дублировать в корень gpthub
├── docker-compose.yml
└── ...
```

Дальнейший рост (из исходного ТЗ): `packages/router`, `packages/memory`, `packages/tools`, `packages/rag`, `packages/ingest`, `packages/traces`.

---

## Интеграция Open WebUI

- **Фаза A (текущий скелет):** WebUI шлёт OpenAI-compatible запросы на **orchestrator**; оркестратор проксирует в **LiteLLM**, параллельно строит **trace** (лог + заголовок для отладки).
- **Фаза B:** расширенный ответ или side-channel для отображения trace в UI (кастомный клиент / hooks / отдельная панель).

Переменные WebUI: `OPENAI_API_BASE_URL=http://orchestrator:8000/v1`, ключ совместим с проверкой на стороне оркестратора.

---

## Наблюдаемость

- Структурированные логи: этап, `task_type`, выбранная модель, список tools/артефактов (когда появятся).
- Trace JSON сериализуется в лог и опционально в HTTP-заголовок ответа (не часть OpenAI schema).

---

## Безопасность и конфиг

- Секреты только из env; в git — [.env.example](.env.example).
- Жёсткий отказ при отсутствии обязательных переменных для вызова LiteLLM (см. orchestrator settings).
