# Демо-запросы для жюри (GPTHub v3)

Готовые фразы для Open WebUI, подключённого к оркестратору. После ответа декодируйте заголовок **`X-GPTHub-Trace`** (base64 → JSON) и проверьте `model_role`, `task_type`, `prompt_version`.

| # | Сценарий | Пример запроса | Ожидаемая роль (`model_role`) |
|---|----------|----------------|-------------------------------|
| 1 | Быстрый текст | «Привет, как дела?» | `fast_text` |
| 2 | Документ / саммари | «Суммаризируй это письмо про дедлайн» | `doc_synthesis` |
| 3 | Код | «Traceback: NameError в async def foo() — что не так?» | `reasoning_code_local` (при `CODE_ROUTE_PREFERENCE=local`) |
| 4 | PDF / анализ текста | «Проанализируй PDF с архитектурой системы» | `doc_synthesis` |
| 5 | Картинка | Вложить скрин + «Что не так на этом скриншоте?» | `vision_general` |
| 6 | Мультимодал + отладка | Скрин + «debug this UI screenshot» | `vision_general` |

**Что сказать жюри:** один чат, разные типы запросов — система выбирает режим и модель; в trace видно классификацию и версию промптов.

См. также: [PROMPT_PRECEDENCE.md](PROMPT_PRECEDENCE.md), [versions_dep/v3/ROADMAP.md](../versions_dep/v3/ROADMAP.md) фаза 0.5.
