# GPTHub — конструктор сборки (True Tech Hack 2026, кейс MWS GPT)

Документ — **единая карта**: что брать готовым из OSS, в каком порядке собирать, где тонкий кастом, какие риски и дедлайны. Исходная таблица репозиториев перенесена сюда из `GPTHub-github-stack.md` (тот файл оставлен как отсылка).

---

## 1. Календарь и сдача (из Положения)

| Событие | Срок (МСК) |
|--------|------------|
| Публикация **Задачи и критериев** на [Платформе](https://truetecharena.ru/) | **10.04.2026 12:00** |
| Вступление в команду на Платформе | до **10.04.2026 11:00** |
| Сдача: презентация **≤10 слайдов**, ссылка на код, **работающий продукт** | до **15.04.2026 10:00** |
| Кейс **MWS GPT**: дополнительно **демо-видео** | та же сдача |
| Список финалистов | до **18.04.2026 18:00** |
| Очный финал (Москва): презентация + вопросы | **24.04.2026**, **5 + 5 мин** |

**Важно:** это Положение не задаёт технический стек. Ограничения партнёра (только MWS API, обязательный Open WebUI и т.д.) — только в тексте **Задачи** после 10.04; после публикации сверить и обновить этот документ и `.env.example`.

---

## 2. Принцип Парето (80 / 20)

- **~80%:** поднять готовые слои (Docker Compose, Open WebUI, LiteLLM, MWS как провайдер), минимальная конфигурация.
- **~20%:** политика маршрутизации, один сценарий демо, питч, опционально препроцессинг (ASR / PDF) тонким сервисом, trace в ответе.

Не писать чат с нуля. Форк UI — только если не хватает конфигом.

---

## 3. Целевой MVP (не больше пяти пунктов)

1. **Единый чат** — один UX для текста и вложений.
2. **Маршрутизация моделей** — через **один** gateway (LiteLLM Proxy), без второго «мозга» на FastAPI.
3. **Файлы + голос + изображения** — в рамках возможностей выбранной модели и UI; препроцессинг (ASR, извлечение текста) — отдельные вызовы **до** или **вокруг** chat, не дублируя выбор модели.
4. **Память / RAG (минимум)** — встроенный RAG Open WebUI **или** черновик Mem0 / своих embed + retrieval.
5. **Видимость контекста** — см. §8: по умолчанию **trace в ответе** (collapsible markdown) или отдельный блок «что учли».

---

## 4. Порядок интеграции

1. `docker compose`: **LiteLLM Proxy** + **Open WebUI** (или выбранный UI).
2. Подключить **MWS GPT** в LiteLLM (`model_list`, ключи через env).
3. В UI указать **один** `OPENAI_API_BASE_URL` → LiteLLM (v2) **или** → orchestrator (v3); см. [versions_dep/v3/README.md](versions_dep/v3/README.md).
4. Несколько алиасов в LiteLLM (например текст / vision / свой instruct на GPU) + **явные** правила routing / fallback ([auto routing](https://docs.litellm.ai/docs/proxy/auto_routing)); каркас v2_c2: см. `versions_dep/v2_c2/README.md`.
5. Проверить: текст → файл → изображение (если модель мультимодальная).
6. STT/TTS или внешний ASR (OpenAI-compatible endpoint в настройках UI или препроцессинг).
7. Прототип памяти (RAG в UI или Mem0 / свой слой).
8. **Заморозка демо:** публичный URL (§10), прогон без таймаутов, запасной сценарий.

---

## 5. Матрица build vs buy

| Компонент | Buy (OSS / сервис) | Build (тонко) |
|-----------|-------------------|---------------|
| Чат UI | Open WebUI (default), опционально LibreChat | брендинг, функции, не форк без нужды |
| Маршрутизация LLM | **LiteLLM Proxy** | `config.yaml`, policies, заголовки |
| Основной LLM | **MWS GPT** (после Задачи 10.04) | — |
| Доп. LLM / vision | OpenRouter, другие API через LiteLLM | только конфиг |
| ASR / TTS | свой ASR, облако, совместимый API | обёртка FastAPI: файл → текст |
| PDF / OCR | библиотеки, готовые парсеры, multimodal в модель | пайплайн вызовов |
| Embeddings / rerank | свои сервисы или MWS/OpenAI-compatible | интеграция URL в RAG |
| Память | Mem0, RAG Open WebUI, LlamaIndex | промпты, post-hooks |

---

## 6. Маршрутизация

- **Источник правды по провайдерам и алиасам моделей — LiteLLM** (`versions_dep/v2_c2/litellm/config.yaml`, тот же файл монтируется в **v3**).
- **v3 (активная сборка):** Open WebUI → **orchestrator (FastAPI)** → LiteLLM. Автовыбор роли/модели и trace — в оркестраторе; он вызывает уже настроенные в LiteLLM имена (`gpt-hub-*`).
- **v2_c2 (заморозка):** Open WebUI → LiteLLM **напрямую**.
- Отдельный **FastAPI** для препроцессинга (ASR, PDF → текст, embed/rerank) — **без** второго дублирующего слоя выбора LLM поверх LiteLLM.

«Автовыбор модели» в v3 = **policy** в orchestrator + алиасы в LiteLLM; для жюри — формулировка из [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md).

---

## 7. Мульти-бэкенд (опционально)

| Провайдер | Роль | Tier для демо |
|-----------|------|----------------|
| MWS GPT | Основной chat / инструкция (по Задаче) | **Tier-1** |
| LiteLLM | Единая точка входа | **Tier-1** |
| Свой ASR | Голос → текст | Tier-1 или Tier-2 — решить по стабильности публичного деплоя |
| Свой embedding / reranker | RAG | Tier-1 или Tier-2 |
| OpenRouter / OSS multimodal | Картинки, PDF, если MWS не покрывает | Tier-2 с **fallback** на MWS |

**Публичный деплой:** всё, что вызывается **с VPS** в проде демо, должно быть **доступно с этого хоста**. Сервисы только за Tailscale (`100.x`) без Tailscale на VPS — не попадут в цепочку. Варианты: те же сервисы в compose на VPS; Tailscale на VPS; туннель (осторожно с секретами); режим env **fallback** (только MWS + публичные API).

---

## 8. Context / «Context Composer»

Open WebUI **не гарантирует** отдельную правую панель «что вошло в контекст» без форка.

**Рекомендация для MVP:** структурированный **trace в ответе** (свернутый блок): модель, источники RAG, факт вызова ASR, краткий список файлов. Альтернатива: минимальная внешняя оболочка; форк UI — последний вариант.

---

## 9. Слот дифференциатора (выбрать один)

Зафиксировать в [docs/PITCH-DEMO.md](docs/PITCH-DEMO.md):

- **Вертикаль** — один B2B-сценарий (звонок + КП + переписка).
- **Прозрачность** — пошаговый trace без тяжёлого агента.
- **Modality-first** — углубление в голос **или** в документы.
- **Judge** — вторая короткая проверка ответа против источников.
- **LibreChat** — MCP/агенты, если хватает времени на DevOps.

---

## 10. Рекомендуемая сборка (слои)

| Слой | Первый выбор | Примечание |
|------|----------------|------------|
| Ядро UI | Open WebUI | Чат, файлы, картинки, голос, RAG, self-host |
| Прокси / роутинг | LiteLLM Proxy | `/v1/chat/completions` для MWS и др. |
| Память (опционально) | Mem0 или RAG в Open WebUI | Mem0 — профиль/сессии; LlamaIndex — документы + поиск |
| Голос | ASR/TTS через OpenAI-compatible API | Свой ASR в настройках UI или препроцессинг |

---

## 11. Кандидаты (GitHub)

Перед финальным выбором перепроверьте на GitHub активность и файл `LICENSE`.

| Репозиторий | Роль | Лицензия¹ | Зрелость | Стыковка с MWS GPT |
|-------------|------|-----------|----------|---------------------|
| [open-webui/open-webui](https://github.com/open-webui/open-webui) | Основной UI | BSD-3-Clause + брендинг (см. риски) | Очень высокая | `OPENAI_API_BASE_URL` → прокси или MWS |
| [danny-avila/LibreChat](https://github.com/danny-avila/LibreChat) | Альтернатива UI | MIT | Высокая | `librechat.yaml` |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | Прокси, [auto routing](https://docs.litellm.ai/docs/proxy/auto_routing) | MIT | Высокая | За прокси — MWS |
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | Долгосрочная память | Apache-2.0 | Высокая | Self-host + middleware |
| [run-llama/llama_index](https://github.com/run-llama/llama_index) | RAG | MIT | Высокая | Embeddings через совместимый API |
| [letta-ai/letta](https://github.com/letta-ai/letta) | Память / агенты | Apache-2.0 | Высокая | Опция вместо/рядом с Mem0 |
| [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) | Автономный агент | MIT | Высокая | Тяжёлая опция |
| [agentscope-ai/CoPaw](https://github.com/agentscope-ai/CoPaw) | Оболочка / оркестрация | Apache-2.0 | Высокая | Сырьё |
| [HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace) | Идеи агентов | MIT | Средняя | Не ядро MVP |
| [thushan/olla](https://github.com/thushan/olla) | Go gateway | Уточнить¹ | Средняя | Альтернатива LiteLLM |
| [Inebrio/Routerly](https://github.com/Inebrio/Routerly), [ReRout/ReRout](https://github.com/ReRout/ReRout) | Экспериментальные роутеры | Уточнить¹ | Низкая | Идеи, не прод без тестов |

¹ Перепроверьте `LICENSE` в репозитории на момент использования.

---

## 12. Риски и прагматика

- **Open WebUI:** [лицензия/брендинг](https://docs.openwebui.com/license); для демо обычно хватает стандартного UI + LiteLLM.
- **LibreChat:** MongoDB и т.д. — больше времени на подъём.
- **LiteLLM:** без правил в конфиге автомаршрутизации не будет — заложить время на `config`.
- **MWS-only:** если Задача потребует изоляции — отключить лишние провайдеры в UI, один `api_base`.
- **Секреты:** не в git; только `.env.example` с плейсхолдерами.
- **TypingMind** и др. — проверить лицензию под хакатон.
- **OpenRouter free tier:** нестабильно; для финала — закрепить модель и fallback.
- **Prompt injection / мультимодальность:** в LiteLLM `detect_prompt_injection` по умолчанию **выключен** (ложные срабатывания на RAG/PDF); не замена модерации. Публичное демо — закрыть signup, сильные секреты, см. v2_c2 README.

---

## 13. Чеклист «1–2 дня» (интеграция)

1. Compose: Open WebUI + LiteLLM; UI → URL LiteLLM.
2. Минимум две модели в LiteLLM + routing / fallback.
3. Один чат: текст, файл, изображение (если модель позволяет).
4. STT/TTS или внешний ASR.
5. Черновик памяти: RAG в UI или Mem0.

---

## 14. Переменные окружения (обзор)

См. корневой `.env.example`. Реальные ключи и внутренние URL только локально / в CI secrets.

---

## 15. Ссылки

- Платформа хакатона: [truetecharena.ru](https://truetecharena.ru/)
- Сайт: [truetechhack.ru](https://truetechhack.ru/)
