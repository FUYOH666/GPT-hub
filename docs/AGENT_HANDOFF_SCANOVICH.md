# Handoff: агент проекта Scanovich (или другой репо) → GPT-hub

Скопируйте блок ниже в начало чата, если нужно «переключиться» с разработки [app.scanovich.ai](https://app.scanovich.ai/) (или иного проекта) на этот репозиторий.

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

**Публичный URL для команды (HTTPS):** [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md) — **канон GPT-hub** по деплою WebUI (прокси, таймауты, env, безопасность). В репо **website-scanovich.ai** — витрина, редиректы и путь вида `scanovich.ai/…`; исполнение стека — по этому файлу в GPT-hub.

**Связь с Scanovich:** Streamlit и Open WebUI — разные процессы; на лендинге — ссылка на поддомен чата. Встраивание WebUI в Streamlit — только по отдельному ТЗ.

**Секреты:** не коммитить `.env`, Tailscale IP, токены; в git только `.env.example` с плейсхолдерами.

---

Конец блока для копирования.
