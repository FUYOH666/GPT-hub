# Задача для человека с доступом к Cloudflare (Tunnel → Open WebUI)

Это **обобщённая** инструкция (примерные hostname `*.example.com`, localhost). Фактический публичный URL задаётся только в **`WEBUI_URL`** в `.env` (файл не коммитить). Токены туннеля и UUID не хранить в репозитории.

Скопируйте блок ниже целиком в тикет / чат коллеге или в [Cloudflare Community](https://community.cloudflare.com/) (раздел **Zero Trust** / **Tunnels**), подставив свои имена хостов. Локальный стек уже слушает **Open WebUI на порту 3000** на машине, где крутится Docker (`http://127.0.0.1:3000`).

---

**Контекст:** нужен публичный **HTTPS** до внутреннего веб-интерфейса на домашнем/офисном Mac. Сервис — **Open WebUI** (Docker), порт **3000** на localhost. Наружу не выставляем другие порты.

**Просьба:**

1. В аккаунте **Cloudflare Zero Trust** создать **Cloudflare Tunnel** (или выдать инструкцию), чтобы трафик с выбранного поддомена шёл на **`http://127.0.0.1:3000`** на машине, где запущен `cloudflared`.
2. Выбрать hostname вида **`chat.<наша-зона>.com`** (или тот, что договоримся) и настроить DNS-запись через туннель (CNAME на `…cfargotunnel.com` или как рекомендует Cloudflare для вашего типа туннеля).
3. Подтвердить, что включены **WebSocket** и длинные ответы (**SSE**) — для чата со стримингом; при проблемах указать, какие опции в панели Cloudflare трогать (не режем Upgrade / не кэшировать HTML API путей WebUI).
4. (Опционально) Выдать **`TUNNEL_TOKEN`** для запуска `cloudflared tunnel run --token …` как службы на Mac, либо дать пошагово: `cloudflared tunnel login` → создание туннеля → содержимое **`config.yml`** и путь к **`credentials.json`**.

**Ограничения:** токены и UUID туннеля **не** класть в git; хранить в менеджере секретов / только на машине с Docker.

**После готовности туннеля** владелец стека задаёт в `versions_dep/v3/.env`: `WEBUI_URL=https://chat.<зона>.com` и пересоздаёт контейнер `open-webui` (`docker compose up -d --force-recreate open-webui`).

---

## Пример `config.yml` (шаблон, без реальных имён)

Замените `TUNNEL_UUID`, путь к credentials и hostname.

```yaml
tunnel: TUNNEL_UUID
credentials-file: /Users/YOU/.cloudflared/TUNNEL_UUID.json

ingress:
  - hostname: chat.example.com
    service: http://127.0.0.1:3000
  - service: http_status:404
```

Запуск вручную для проверки:

```bash
cloudflared tunnel --config /path/to/config.yml run
```

Официальные доки: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), [Private web application](https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/).

См. также общий гайд: [TEAM_PUBLIC_ACCESS.md](TEAM_PUBLIC_ACCESS.md).

---

## Пошагово в Zero Trust (после установки `cloudflared`)

1. **Networks → Tunnels →** ваш туннель: статус **Healthy** (реплика `darwin_arm64` и т.д.).
2. **Routes → Add route** (или **Add published application**): публичный поддомен на зоне в Cloudflare (например `gpthub.example.com`).
3. **Service URL (обязательно):** `http://127.0.0.1:3000` — не `https://`, не порт `8080`, пока Open WebUI в Docker слушает **3000** на этом Mac.
4. После сохранения Cloudflare создаст **CNAME** на `….cfargotunnel.com`. Имя в DNS часто в **нижнем регистре**; откройте в браузере тот URL, который реально открывается (проверка с другой сети или LTE).
5. Локально в [versions_dep/v3/.env](../versions_dep/v3/.env): **`WEBUI_URL=https://<тот-же-хост>`** (как в адресной строке), опционально **`OR_SITE_URL`**. Затем:  
   `docker compose up -d --force-recreate open-webui`
6. **Токен** туннеля не светить в чатах и скриншотах; при утечке — перевыпустить в Zero Trust.

Ошибки **502 / 521**: туннель не достучался до origin — проверьте, что контейнер WebUI запущен и маршрут указывает на `127.0.0.1:3000`.
