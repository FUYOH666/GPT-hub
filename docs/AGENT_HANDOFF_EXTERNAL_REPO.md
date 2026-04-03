# Handoff: другой репозиторий / витрина → GPT-hub

Скопируйте блок ниже в начало чата, если нужно переключиться с разработки **отдельного сайта или приложения** на этот репозиторий.

---

**Репозиторий:** GPT-hub (True Tech Hack 2026, кейс MWS GPT).

**Активная сборка:** `versions_dep/v3` — Open WebUI → **FastAPI orchestrator** → **LiteLLM**. Не путать с замороженным `versions_dep/v2_c2` (WebUI → LiteLLM напрямую).

**Запуск:**

```bash
cd versions_dep/v3
cp .env.example .env   # при необходимости
docker compose up -d --build
```

Open WebUI: `http://localhost:3000`. **Не поднимать v2_c2 и v3 одновременно** (конфликт портов 3000 и 4000).

**Где править модели и провайдеров:** один файл **`versions_dep/v2_c2/litellm/config.yaml`** (монтируется в контейнер LiteLLM v3). Роли автомаршрутизации v3: `versions_dep/v3/apps/orchestrator/gpthub_orchestrator/data/model_roles.yaml`.

**Документация:** корневая карта — [README.md](../README.md); запуск и PDF/RAG — [versions_dep/v3/README.md](../versions_dep/v3/README.md); архитектура — [versions_dep/v3/ARCHITECTURE.md](../versions_dep/v3/ARCHITECTURE.md).

**Публичный HTTPS для команды:** [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md) — канон по прокси/туннелю, `WEBUI_URL`, таймаутам и безопасности. Лендинг, редиректы и «красивый URL» обычно живут в **другом репозитории**; этот репо — только стек Docker и интеграция.

**Связь витрина ↔ чат:** клиентский UI лендинга и Open WebUI — разные сервисы; на лендинге — ссылка на URL чата (из `.env`: `WEBUI_URL`). Встраивание WebUI в другой фронт — только по отдельному ТЗ.

**Секреты:** не коммитить `.env`, внутренние IP, токены; в git только `.env.example` с плейсхолдерами.

---

Конец блока для копирования.
