# Staff review — GPT-hub multi-version portfolio (v3 + v2_c2 + v1_z)

Дата: 2026-04-02. Метод: staff-review-pipeline skill (полные фазы, уровень портфеля). Снимок дерева без привязки к `git diff` (репозиторий может быть без git).

## Scope

**Цель изменений (продукт):** единый чат (Open WebUI) с маршрутизацией через FastAPI-оркестратор, LiteLLM как gateway, trace (`X-GPTHub-Trace`), дальнейшее развитие perception/RAG по [versions_dep/v3/ROADMAP.md](../../versions_dep/v3/ROADMAP.md).

**Включено:**

- [versions_dep/v3](../../versions_dep/v3): `docker-compose.yml`, orchestrator (`apps/orchestrator`), `embedding_shim/`
- [versions_dep/v2_c2/litellm/config.yaml](../../versions_dep/v2_c2/litellm/config.yaml) — единый конфиг, монтируется в v3
- [versions_dep/v2_c2](../../versions_dep/v2_c2) как замороженный baseline
- [versions_dep/v1_z/LEGACY.md](../../versions_dep/v1_z/LEGACY.md)
- Корневой [README.md](../../README.md), [AGENTS.md](../../AGENTS.md), релевантные документы в [docs/](../) (публикация, роли WebUI)

**Исключено:** `.venv`, кэши, содержимое upstream-образов Open WebUI/LiteLLM (кроме точек интеграции).

**Допущения:** аудит по текущему состоянию файлов; секреты только в `.env` (не в отчёте).

---

## Correctness & logic

- **Orchestrator** ([main.py](../../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/main.py)): JSON body валидируется; `messages` — список; Bearer сверяется с `orchestrator_api_key`. Non-stream: цепочка fallback по 429/503 с логированием попыток и trace. Stream: одна попытка — явно отражено в trace (`stream_single_attempt`); ошибки upstream превращаются в SSE `error` + `[DONE]` — снижает «обрыв» в UI.
- **Роутер** ([router.py](../../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/router.py)): роли из реестра YAML; выбор local vs OpenRouter для code/deep через `code_route_preference`.
- **Классификатор** ([classifier.py](../../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/classifier.py)): эвристики + исключения для даты/времени (не canned), согласовано с clock injection в main.
- **Пробел:** фаза 1 ROADMAP (ingest PDF/image/audio → артефакты) **не реализована**; ARCHITECTURE описывает целевой пайплайн — текущий код в основном прокси + классификация + промпты по роли. Для вложений поведение по-прежнему опирается на WebUI/LiteLLM, не на оркестратор-центричный контракт из ROADMAP §1.

---

## Architecture fit

- **Единый источник алиасов LLM:** v3 монтирует `../v2_c2/litellm/config.yaml` — соответствует Charter и [README](../../README.md).
- **Слои:** WebUI → orchestrator → LiteLLM — чистое разделение; продуктовая логика в Python-пакете, конфиги YAML рядом с кодом.
- **Дублирование:** v2 и v3 не должны подниматься одновременно — задокументировано в README и CONTINUATION; портовый конфликт осознанный.
- **v1_z:** явно помечен как архив в LEGACY.md; корневой README отсылает к v3.

---

## Security & privacy

- [.gitignore](../../.gitignore): `.env`, ключи, `.venv` — ок.
- Grep по шаблонам секретов в отслеживаемых файлах: только плейсхолдеры в `.env.example` и тестовые `test-key` в pytest.
- TailScale IP **не** найдены в `*.md,yml,yaml,py,env.example` (хорошо для будущего push).
- [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md): канон по TLS, не светить :4000/:8089, `WEBUI_URL`, отключение signup для публичного демо — согласуется с compose-переменными.
- **Риск эксплуатации:** при публичном UI без hardening — слабые пароли/signup; документировано, не автоматизировано в compose (осознанно).

---

## Reliability & ops

- **Healthchecks:** LiteLLM liveliness, orchestrator `/healthz`, embedding-shim `/healthz` — заданы в [docker-compose.yml](../../versions_dep/v3/docker-compose.yml).
- **Зависимости:** `open-webui` ждёт healthy `embedding-shim`. Если BGE на хосте не запущен, **не поднимется весь WebUI**, даже для сценария без RAG — жёсткая связность (операционный риск).
- **Таймауты:** `LITELLM_TIMEOUT_SECONDS` до 3600 в settings; httpx connect capped 60s — разумно.
- **Логирование оркестратора:** `logging`, не `print`; trace в логах + заголовок.

---

## Performance

- **embedding_shim:** новый `httpx.AsyncClient` на каждый `POST /v1/embeddings` — при частых RAG-запросах лишние соединения; горячий путь, но вне scope если RAG умеренный.
- Остальное без явных N+1 в просмотренном коде прокси.

---

## Tests & verification

- Команда: `cd versions_dep/v3/apps/orchestrator && uv run pytest -q` — **65 passed** (2026-04-02).
- Покрытие: классификатор, роутер, trace, models proxy, fallback, reasoning strip, canned greeting и др.
- **CHANGELOG** в пакете orchestrator **не найден** — расхождение с типичным Definition of Done из charter для значимых релизов.

---

## Docs & DX

- [v3/README.md](../../versions_dep/v3/README.md), [CONTINUATION.md](../../versions_dep/v3/CONTINUATION.md), [ROADMAP.md](../../versions_dep/v3/ROADMAP.md), [ARCHITECTURE.md](../../versions_dep/v3/ARCHITECTURE.md) согласованы с compose (порты 3000/4000/8089, путь к LiteLLM config, `single_public` фасад `gpt-hub`).
- Troubleshooting (Tavily, PDF/stream, embedding shim) в README — сильная сторона.
- Фаза 1 ROADMAP явно перечисляет невыполненные чекбоксы — хороший единый бэклог.

---

## Findings

| ID | Severity | Location | Recommendation |
|----|----------|----------|----------------|
| F1 | should-fix | [embedding_shim/main.py](../../versions_dep/v3/embedding_shim/main.py) ~60 | Заменить голый `except Exception` при `r.json()` на `json.JSONDecodeError` + лог warning; не глотать неожиданные исключения без записи. |
| F2 | should-fix | [docker-compose.yml](../../versions_dep/v3/docker-compose.yml) `open-webui.depends_on` | Рассмотреть ослабление жёсткой зависимости WebUI от `embedding-shim` (профиль optional / health только для RAG) или явно задокументировать «BGE обязателен для старта стека». |
| F3 | nit | [main.py](../../versions_dep/v3/apps/orchestrator/gpthub_orchestrator/main.py) stream path | Поведение без orchestrator-fallback на stream задокументировано в trace; при необходимости — продуктовое решение (retry SSE) отдельной задачей. |
| F4 | nit | orchestrator `/healthz` | Не проверяет доступность LiteLLM (только liveness процесса); для k8s можно добавить optional readiness. |
| F5 | nit | [embedding_shim/main.py](../../versions_dep/v3/embedding_shim/main.py) | Переиспользовать AsyncClient (lifespan) при росте нагрузки RAG. |
| F6 | should-fix | `apps/orchestrator/` | Добавить `CHANGELOG.md` (или корневой фрагмент) при значимых изменениях оркестратора — выровнять с Engineering Charter DoD. |
| F7 | nit | Репозиторий | Инициализировать git и ревьюить диффы; не коммитить `.env` / локальные `.venv`. |

---

## Приоритизированный бэклог к «идеалу»

1. **Продукт (ARCHITECTURE ↔ код):** выполнить [ROADMAP фазу 1](../../versions_dep/v3/ROADMAP.md) (контракт payload WebUI, ingest, артефакты, интеграция в `main.py`) — главный разрыв между документом и рантаймом.
2. **Надёжность стека:** решение по F2 (optional embedding-shim или чёткий ops-runbook «сначала BGE»).
3. **Качество кода:** F1 в embedding_shim.
4. **Процесс:** F6 + F7.

---

## Verdict

**Нужны правки** для выравнивания с заявленной архитектурой perception/context artifacts и для смягчения ops-связности RAG; **к мержу как к хакатонному MVP-оркестратору** — при условии принятия текущего scope (фазы 0–0.5) и зелёных тестов — **условно готов**, с явным техдолгом по фазе 1.
