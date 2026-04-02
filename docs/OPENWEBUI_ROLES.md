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

После правок: `docker compose up -d --force-recreate open-webui` (из каталога `versions_dep/v3`).

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
