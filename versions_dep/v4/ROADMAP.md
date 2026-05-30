# GPTHub v4 — дорожная карта продукта

**Активная линия:** Open WebUI → оркестратор → OpenRouter free (Survival Engine).  
Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md). Быстрый старт: [README.md](README.md). Нулевой вход: [docs/ZERO_ENTRY.md](../../docs/ZERO_ENTRY.md).

Legacy v1–v3: [versions_dep/LEGACY.md](../LEGACY.md) — не удаляем, помечаем архивом.

---

## Статус (2026-05)

| Область | Статус |
|---------|--------|
| Live catalog refresh при старте | ✅ |
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
OPENROUTER_CURATOR_MODEL=google/gemma-3-12b-it:free
OPENROUTER_CURATOR_TIMEOUT=60
```

Trace: `routing_source: heuristic | curator`, `manifest_version`.

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
