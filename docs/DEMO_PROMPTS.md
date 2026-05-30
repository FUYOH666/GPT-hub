# GPTHub v4 — демо-запросы и operational validation

Готовые фразы для Open WebUI или curl к оркестратору v4. Модель в UI: **`gpt-hub`**.  
После ответа декодируйте **`X-GPTHub-Trace`** (http://localhost:8089/trace) — `model_role`, `task_type`, `openrouter_model`, `fallback_used`, `routing_source`.

## Автоматическая проверка (simulator)

```bash
cd versions_dep/v4
# Mock (CI-safe, без OpenRouter)
bash scripts/run_ops_simulator.sh mock

# Live (нужны ORCHESTRATOR_API_KEY + OPENROUTER_API_KEY, orchestrator запущен)
docker compose up -d --build   # или uvicorn локально
bash scripts/run_ops_simulator.sh live
```

Отчёт: `versions_dep/v4/reports/ops-mock.json` (+ `.md` summary).

## Сценарии для ручного демо

| # | Сценарий | Пример запроса | Ожидаемая роль (`model_role`) |
|---|----------|----------------|-------------------------------|
| 1 | Приветствие | «Привет, как дела?» | `fast_text_chat` (`greeting_or_tiny`) |
| 2 | Обычный Q&A | «Объясни в двух предложениях, что такое список в Python.» | `fast_text` |
| 3 | Документ / саммари | «Суммаризируй это письмо про дедлайн» | `doc_synthesis` |
| 4 | Код | «Traceback: NameError…» | `reasoning_code_openrouter` (при `CODE_ROUTE_PREFERENCE=openrouter`) |
| 5 | Картинка | Скрин + «Что не так на этом скриншоте?» | `vision_general` |
| 6 | Stream | Тот же запрос с `"stream": true` | trace: `stream_fallback`, возможен `fallback_used` |

## Ops endpoints

| Endpoint | Назначение |
|----------|------------|
| `GET /readyz` | OpenRouter + live catalog meta |
| `GET /trace` | Декодер trace (не публиковать наружу) |
| `GET /v1/admin/catalog` | Bearer admin — catalog, diff, probe, bandit, bans, quota, curator |

### Admin catalog (`GET /v1/admin/catalog`)

Поля после control loop (2026-05):

| Поле | Смысл |
|------|--------|
| `active_catalog.text_fast` / `text_code` / `text_doc` / `vision` | Разные цепочки slug по ролям |
| `catalog_diff.sections.*.added/removed/reordered` | Что изменилось при последнем refresh |
| `probe_results[]` | Micro-probe при refresh: `{section, slug, ok, status_code}` |
| `bandit_stats.by_section` | EMA success/latency/429 по slug; resort каждые ~30 мин |
| `routing_source` | `heuristic` \| `curator` \| `bandit` |
| `model_health.banned` | Slug временно исключены после N×429 |

```bash
curl -s -H "Authorization: Bearer $ORCHESTRATOR_API_KEY" \
  http://localhost:8089/v1/admin/catalog | jq '.routing_source, .probe_results, .active_catalog.text_fast, .active_catalog.text_code'
```

## Fault scenarios (только mock simulator)

- **429 на первой модели** → `fallback_used: true`
- **429 на всех** → `503 openrouter_exhausted` + `message_ru`
- **Health ban** → slug в `model_health.banned` (admin)

См.: [versions_dep/v4/README.md](../versions_dep/v4/README.md), [ZERO_ENTRY.md](ZERO_ENTRY.md), Staff review [reviews/2026-05-30-v4-staff-review.md](reviews/2026-05-30-v4-staff-review.md).
