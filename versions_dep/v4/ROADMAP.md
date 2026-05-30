# GPTHub v4 — дорожная карта продукта

**Активная линия:** Open WebUI → оркестратор → OpenRouter free (Survival Engine).  
Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md). Быстрый старт: [README.md](README.md). Нулевой вход: [docs/ZERO_ENTRY.md](../../docs/ZERO_ENTRY.md).

Legacy v1–v3: [versions_dep/LEGACY.md](../LEGACY.md) — не удаляем, помечаем архивом.

---

## Статус (2026-05)

| Область | Статус |
|---------|--------|
| Live catalog refresh при старте | ✅ |
| Role-specific catalog chains (scorer) | ✅ |
| Catalog coordinator lock (refresh/curator/bandit) | ✅ |
| Micro-probe on refresh (default ON) | ✅ |
| Bandit EMA resort | ✅ |
| Model/key fallback (non-stream + stream) | ✅ |
| Runtime health ban после 429 | ✅ |
| Async LLM Model Curator (opt-in) | ✅ |
| Trace header + `/trace` decoder | ✅ |
| Admin `/v1/admin/catalog` | ✅ |
| ZERO_ENTRY docs + product README | ✅ |
| Память / RAG workspace | 📋 backlog |
| Публичный деплй (Cloudflare Tunnel) | 📋 после стабилизации |

---

## Фаза 0 — Smoke и ключ (готово)

- [x] Docker compose: orchestrator + Open WebUI
- [x] `GET /readyz` — OpenRouter live + `catalog_refresh.source: openrouter_live`
- [x] `POST /v1/chat/completions` model `gpt-hub` + `X-GPTHub-Trace`
- [x] `scripts/verify_v4.sh`

---

## Фаза 1 — Продуктовый фундамент (готово)

### Документация «нулевой вход»

- [x] [docs/ZERO_ENTRY.md](../../docs/ZERO_ENTRY.md)
- [x] Root README — product narrative
- [x] v4 README — quickstart RU, troubleshooting 429

### Человеческие ошибки

- [x] `503 openrouter_exhausted` — сообщение RU + hint в JSON
- [x] WebUI banner + ссылка на OPENWEBUI_ROLES

### Надёжность runtime

- [x] Stream fallback (2–3 model retry в SSE)
- [x] Health scoring: ban slug после N×429 (in-memory TTL)
- [x] Periodic refresh: `OPENROUTER_CATALOG_REFRESH_INTERVAL_HOURS`

---

## Фаза 2 — LLM Model Curator (готово, opt-in)

После эвристического catalog оркестратор **в фоне** (не блокирует `/readyz`):

1. Digest top-N free models (metadata only)
2. Один запрос к capable free-модели → strict JSON `RoutingManifest`
3. Валидация Pydantic; invalid → остаёмся на эвристике

Env:

```bash
OPENROUTER_CURATOR_ENABLED=true
OPENROUTER_CURATOR_MODEL=google/gemma-4-26b-a4b-it:free
OPENROUTER_CURATOR_MERGE_MODE=overlay
OPENROUTER_CURATOR_TIMEOUT=60
```

Trace: `routing_source: heuristic | curator | bandit`, `manifest_version`.

---

## Фаза 3 — UX и ops (MVP готово)

- [x] `/trace` — декодер `X-GPTHub-Trace`
- [x] `/v1/admin/catalog` — catalog, curator, bans, quota
- [ ] Onboarding banner в WebUI (расширить WEBUI_BANNERS)
- [ ] Memory (из v3 roadmap) — optional
- [ ] RAG profile `rag` — optional, BGE не обязателен

---

## Фаза 4 — GitHub и repo hygiene

- [x] v4 как main line в README
- [x] LEGACY.md v1→v4
- [x] CI на v4 pytest
- [ ] Screenshot/GIF в README (placeholder)

---

## Фаза 5 — Публичный деплой

- [docs/TEAM_PUBLIC_ACCESS.md](../../docs/TEAM_PUBLIC_ACCESS.md)
- Cloudflare Tunnel → WebUI `:3000` only
- Не публиковать orchestrator `:8089` напрямую

---

## Осознанно НЕ делаем

- Полный rewrite без v4 base
- LiteLLM как runtime v4
- Slug `openrouter/free` auto-router
- Blocking startup на LLM-кураторе
- Paid models без явного opt-in

---

## Definition of Done (MVP)

- [x] Non-tech: ключ → `.env` → `docker compose up` → chat works
- [x] Catalog при старте + curator улучшает routing в фоне (opt-in)
- [x] 429 не ломает UX — fallback + понятная ошибка
- [x] Trace объясняет выбор модели
- [x] 90+ pytest, CI green
- [x] Ops simulator mock в CI + live playbook

---

## Post-validation backlog (2026-05-30)

Источники: [Staff Review](../../docs/reviews/2026-05-30-v4-staff-review.md), первый прогон `ops_simulator` (mock + live).

| ID | Pri | Effort | Задача | Источник |
|----|-----|--------|--------|----------|
| P1 | P0 | 0.5d | Catalog refresh + curator: async lock (F2) | Staff | ✅ |
| P2 | P0 | 1d | Vision fallback: retry chain on 400/422, не только 429/5xx | Live sim |
| P3 | P1 | 0.5d | Отдельный admin key в ZERO_ENTRY / prod checklist (F1) | Staff |
| P4 | P1 | 0.5d | Удалить или реализовать `ingest_image_fetch_timeout` (F6) | Staff |
| P5 | P1 | 1d | Prometheus `/metrics`: fallback_rate, exhausted_total | F9 |
| P6 | P2 | 1d | Curator A/B report в ops_simulator (heuristic vs curator) | R7 |
| P7 | P2 | 2d | WebUI Playwright E2E | F10 |
| P8 | P2 | 0.5d | README screenshot/GIF | Фаза 4 |
| P9 | P3 | 0.5d | Onboarding banner WebUI | Фаза 3 |

**Simulator (готово):** `bash scripts/run_ops_simulator.sh mock|live` — см. [README.md](README.md) Validation.

**Validation sprint (закрыто 2026-05-30):** R1 golden/invariants без hardcoded slug · R2 DEMO_PROMPTS v4 · R3 ops_simulator mock в CI · control loop (role_scorer, probe, bandit, lock).

**Live note:** при rate limit OpenRouter live-проход засчитывает **routing OK (degraded)**, если trace содержит верные `model_role` / `task_type`, даже при HTTP 503.
