# GPTHub v4 — нулевой вход (OpenRouter free)

Пошаговая инструкция для **не-технического** пользователя: один ключ OpenRouter → чат в браузере.

## Что вы получите

- Один интерфейс чата (Open WebUI) с моделью **`gpt-hub`**
- Оркестратор сам выбирает **бесплатную** модель OpenRouter под задачу (текст, код, документ, картинка)
- При занятости free-моделей (429) — **автоматический fallback** на другую модель/ключ
- В ответе — заголовок **`X-GPTHub-Trace`**: какая модель ответила и почему

## Шаг 1 — Ключ OpenRouter

1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai/)
2. Создайте API key в настройках аккаунта
3. Убедитесь, что используете **free**-модели (`*:free`) — GPTHub v4 настроен только на них

## Шаг 2 — Файл `.env`

```bash
cd versions_dep/v4
cp .env.example .env
```

Заполните минимум три значения:

| Переменная | Что поставить |
|------------|----------------|
| `ORCHESTRATOR_API_KEY` | Длинная случайная строка (пароль для Open WebUI → оркестратор) |
| `OPENROUTER_API_KEY` | Ваш ключ OpenRouter |
| `WEBUI_SECRET_KEY` | Случайная строка для сессий Open WebUI |

**Не коммитьте `.env` в git.**

## Шаг 3 — Запуск

```bash
docker compose up -d --build
```

Подождите 1–2 минуты (первый build дольше).

## Шаг 4 — Первый чат

1. Откройте http://localhost:3000
2. Создайте аккаунт администратора (первый пользователь)
3. В настройках подключения OpenAI API укажите:
   - **Base URL:** `http://orchestrator:8089/v1` (внутри Docker) или `http://host.docker.internal:8089/v1` при ручной настройке с хоста
   - **API Key:** значение `ORCHESTRATOR_API_KEY` из `.env`
4. Выберите модель **`gpt-hub`** и отправьте сообщение

## Проверка без WebUI (curl)

```bash
# из каталога versions_dep/v4, подставьте свой ORCHESTRATOR_API_KEY
bash scripts/verify_v4.sh
```

Ожидается: `v4 smoke OK` и в `/readyz` — `"source": "openrouter_live"`.

## Trace — «какая модель ответила»

- Декодер: http://localhost:8089/trace (вставьте base64 из `X-GPTHub-Trace`)
- Или: `curl -D - ... | grep X-GPTHub-Trace` и base64-decode

## Частые проблемы

| Симптом | Что делать |
|---------|------------|
| `503 openrouter_exhausted` | Все free-модели заняты; подождите или добавьте второй ключ в `OPENROUTER_KEYS` |
| `readyz` 503 | Проверьте `OPENROUTER_API_KEY`, интернет, блокировку openrouter.ai |
| WebUI не видит оркестратор | Проверьте `docker compose ps`, логи `orchestrator` |
| 429 часто | Норма для free tier; fallback включён (`ORCHESTRATOR_OPENROUTER_FALLBACK=true`) |

## Семья / команда

- Один admin в Open WebUI; для приглашения других см. [OPENWEBUI_ROLES.md](OPENWEBUI_ROLES.md)
- Публичный доступ — только через HTTPS-туннель, не открывайте `:8089` наружу: [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md)

## Опционально

- **LLM-куратор** (умнее маршрутизация в фоне): `OPENROUTER_CURATOR_ENABLED=true` в `.env`
- **Периодическое обновление каталога:** `OPENROUTER_CATALOG_REFRESH_INTERVAL_HOURS=6`
- **Admin ops:** `GET /v1/admin/catalog` с Bearer `ORCHESTRATOR_ADMIN_API_KEY` (по умолчанию = `ORCHESTRATOR_API_KEY`)

Подробнее: [versions_dep/v4/README.md](../versions_dep/v4/README.md), [versions_dep/v4/ROADMAP.md](../versions_dep/v4/ROADMAP.md).
