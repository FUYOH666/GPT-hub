# Open WebUI: регистрация и роли (v3)

Данные пользователей хранятся в SQLite внутри Docker volume **`open-webui-v3-data`**, файл **`webui.db`**, таблица **`user`** (поля `email`, `role` и др.).

## Переменные в `.env` (сервис `open-webui` в compose)

| Переменная | Смысл |
|------------|--------|
| `ENABLE_SIGNUP` | `true` — форма регистрации доступна; `false` — только созданные админом пользователи |
| `DEFAULT_USER_ROLE` | `user` — после регистрации сразу обычный пользователь; `pending` — до одобрения в админке |
| `WEBUI_ADMIN_EMAIL` | Почта «закреплённого» админа при **первом** развёртывании (см. ниже) |
| `WEBUI_ADMIN_PASSWORD` | Пароль для bootstrap админа (только если используете механизм первичного создания; не коммитить) |
| `WEBUI_URL` | Должен совпадать с URL в браузере (особенно при Cloudflare Tunnel), иначе куки и редиректы |
| `OR_SITE_URL` | Для OpenRouter и т.п. обычно тот же базовый URL, что и публичный UI |
| `ENABLE_PERSISTENT_CONFIG` | `true` (по умолчанию в compose) — настройки из UI/БД **перекрывают** env; из‑за этого на экране входа может **не быть** регистрации, даже при `ENABLE_SIGNUP=true` в `.env` |
| `ENABLE_WEB_SEARCH` | `true` — доступен веб-поиск в чате (если задан движок и ключ) |
| `WEB_SEARCH_ENGINE` | Например `tavily` — см. официальную доку Open WebUI |
| `TAVILY_API_KEY` | Ключ Tavily; только в локальном `.env`, не в git |
| `BYPASS_MODEL_ACCESS_CONTROL` | `true` — все пользователи видят все модели из API (рекомендуется для команды); `false` — только RBAC/группы |

После правок: `docker compose up -d --force-recreate open-webui` (из каталога `versions_dep/v3`).

### У пользователя с ролью `user` пустой селектор моделей («Выберите модель»)

Админы в Open WebUI по умолчанию **обходят** контроль доступа к моделям; обычные пользователи — **нет**: список моделей фильтруется по группам/RBAC, и без явных прав селектор **пустой**, хотя API оркестратора и LiteLLM в порядке.

1. В compose для v3 задано **`BYPASS_MODEL_ACCESS_CONTROL=true`** (можно переопределить в `.env`). После смены: `docker compose up -d --force-recreate open-webui`.
2. Если **`ENABLE_PERSISTENT_CONFIG=true`**, в БД мог сохраниться старый флаг — проверьте **Admin Panel → Settings** (разделы про модели / доступ) или временно отключите persistent config.
3. Альтернатива без bypass: **Admin → Groups** — выдать группе `user` доступ к нужным моделям (или сделать пресеты публичными).

### Нет ссылки «Регистрация» на странице входа

1. Зайдите под **admin** → **Admin Panel** → **Settings** (разделы вроде **General** / **Authentication**) и включите **регистрацию новых пользователей** (название пункта зависит от версии Open WebUI), затем сохраните.
2. Проверьте в контейнере: `docker compose exec open-webui printenv ENABLE_SIGNUP ENABLE_PERSISTENT_CONFIG` — убедитесь, что `ENABLE_SIGNUP=true`.
3. Крайний вариант: в `.env` выставить `ENABLE_PERSISTENT_CONFIG=false` и пересоздать `open-webui` — тогда приоритет у env, но часть настроек из UI может перестать применяться как раньше; делайте осознанно.

## Режим «один админ, остальные регистрируются сами»

1. В `.env`: `ENABLE_SIGNUP=true`, `DEFAULT_USER_ROLE=user`.
2. Задайте **`WEBUI_ADMIN_EMAIL`** на нужный адрес — это помогает при **новом** инстансе; на **уже заполненной** базе роли правятся в UI или вручную в БД.
3. В интерфейсе: **Admin → Users** — ровно у одного пользователя **Role = admin**, у остальных **user**.

**Важно:** переменная `WEBUI_ADMIN_EMAIL` **сама по себе не снимает** роль `admin` с уже существующих пользователей. Если кто-то стал admin раньше, понизьте его в **Users** или через SQL (с бэкапом volume).

## Пример принудительной правки ролей (осторожно)

Только если понимаете риск; сделайте бэкап volume или файла `webui.db`.

Замените `admin@example.com` на вашу почту админа:

```bash
docker compose exec -T open-webui python3 -c "
import sqlite3
email = 'admin@example.com'
conn = sqlite3.connect('/app/backend/data/webui.db')
cur = conn.cursor()
cur.execute(\"UPDATE user SET role='user' WHERE lower(email) != lower(?)\", (email,))
cur.execute(\"UPDATE user SET role='admin' WHERE lower(email) = lower(?)\", (email,))
conn.commit()
print('ok')
"
```

## Аналитика и учёт запросов

Счёт пользователей — **Admin → Users**. Объём запросов к LLM — логи **LiteLLM**, опционально Langfuse и т.д. (см. документацию LiteLLM); в этом репозитории отдельный дашборд не встроен.

См. также: [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md), [versions_dep/v3/.env.example](../versions_dep/v3/.env.example).
