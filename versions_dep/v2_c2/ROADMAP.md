# Дорожная карта v2_c2

**Стек заморожен:** новые фичи не ведём. Активный бэклог и фазы — **[versions_dep/v3/ROADMAP.md](../v3/ROADMAP.md)**.

**Зачем оставили v2_c2:** эталон **Docker Compose** «Open WebUI → LiteLLM» без оркестратора и единый файл **[litellm/config.yaml](litellm/config.yaml)** (его же монтирует v3). Запуск и переменные: [README.md](README.md).

После публикации **Задачи** на [truetecharena.ru](https://truetecharena.ru/) (10.04.2026 12:00 МСК) — правки провайдеров и `model_list` в `litellm/config.yaml` и `.env` по тексту Задачи; смок: `./scripts/verify_stack.sh` и [../../docs/PITCH-DEMO.md](../../docs/PITCH-DEMO.md).
