# Демо-запросы для жюри (GPTHub v3)

Готовые фразы для Open WebUI, подключённого к оркестратору. В селекторе модели — один публичный id **`gpt-hub`** (при `ORCHESTRATOR_MODELS_CATALOG=single_public`). После ответа декодируйте заголовок **`X-GPTHub-Trace`** (base64 → JSON) и проверьте `model_role`, `task_type`, `prompt_version` и фактический апстрим-модельный алиас.

| # | Сценарий | Пример запроса | Ожидаемая роль (`model_role`) |
|---|----------|----------------|-------------------------------|
| 1 | Приветствие / короткая реплика | «Привет», «как дела?», «Привет, как дела?» | `fast_text_chat` (`task_type`: `greeting_or_tiny`); при включённом canned ответ **без вызова LLM** — в trace `canned_response: true` |
| 1b | Обычный Q&A без приветствия | «Объясни в двух предложениях, что такое список в Python.» | `fast_text` |
| 2 | Документ / саммари | «Суммаризируй это письмо про дедлайн» | `doc_synthesis` |
| 3 | Код | «Traceback: NameError в async def foo() — что не так?» | `reasoning_code_local` (при `CODE_ROUTE_PREFERENCE=local`) |
| 4 | PDF / анализ текста | «Проанализируй PDF с архитектурой системы» | `doc_synthesis` |
| 5 | Картинка | Вложить скрин + «Что не так на этом скриншоте?» | `vision_general` |
| 6 | Мультимодал + отладка | Скрин + «debug this UI screenshot» | `vision_general` |

**Что сказать жюри:** один чат, разные типы запросов — система выбирает режим и модель; в trace видно классификацию и версию промптов.

Если в UI появляется блок «Рассуждение» на обычных ответах: оркестратор по умолчанию режет `reasoning*` в payload и шлёт `reasoning.exclude` upstream — см. [OPENWEBUI_ROLES.md](OPENWEBUI_ROLES.md) (Reasoning Tags, чеклист).

См. также: [PROMPT_PRECEDENCE.md](PROMPT_PRECEDENCE.md), [versions_dep/v3/ROADMAP.md](../versions_dep/v3/ROADMAP.md) фаза 0.5.
