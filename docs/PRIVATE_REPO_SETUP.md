# Приватный репозиторий на GitHub

Кратко: **создать пустой приватный репо** на GitHub, затем **привязать remote** и **push**. Из этого каталога репозиторий нельзя создать без вашей авторизации в GitHub.

## Перед первым коммитом

- Убедитесь, что **нет** `.env` с ключами в индексе: `git status` и при необходимости `git check-ignore -v .env`.
- Реальные IP (Tailscale и т.д.) не должны попадать в коммиты — см. правила проекта.

## Вариант A: GitHub CLI (`gh`)

```bash
cd /path/to/GPT-hub
gh auth login
gh repo create GPT-hub --private --source=. --remote=origin --push
```

Имя репозитория замените на нужное (например `gpthub-hackathon-private`). Если репо уже создано вручную:

```bash
git remote add origin https://github.com/FUYOH666/ИМЯ-РЕПО.git
git branch -M main
git push -u origin main
```

## Вариант B: веб-интерфейс GitHub

1. [github.com/new](https://github.com/new) → **Private** → создать без README (если локально уже есть история).
2. В каталоге проекта:

```bash
git init
git add .
git commit -m "Initial commit: GPT-hub monorepo"
git remote add origin https://github.com/FUYOH666/ИМЯ-РЕПО.git
git branch -M main
git push -u origin main
```

## Авторство

См. корневой [AUTHORS.md](../AUTHORS.md) и раздел в [README.md](../README.md).
