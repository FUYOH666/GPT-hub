# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **`GREETING_CANNED_RESPONSE_ENABLED`** по умолчанию **`false`**: приветствия и короткий small-talk снова идут в LiteLLM; canned включается явно через env / compose.
- **`orchestrator_asr_model`** по умолчанию **`whisper-1`** (нейтральный id для публичного репо; свой id ASR — в `.env`).
- **`vision_general`:** цепочка алиасов расширена под LiteLLM `gpt-hub-vision` … `gpt-hub-vision-4` + `gpt-hub-fallback` (stream: перебор на стороне оркестратора при ошибках).

### Added

- **`list_free_models`:** флаги `--suggest-vision-chain`, `--limit`; функции ранжирования free+image для ручного обновления `litellm/config.yaml`; тесты `tests/test_list_free_models.py`.
- Ingest pipeline (phase 1): PDF из `file` + data URL, аудио через ASR (`ORCHESTRATOR_ASR_*`), `asyncio.gather`, trace `ingest_ms` / `artifacts`.
- `GET /readyz` — проверка `GET …/health/liveliness` у LiteLLM.
- Зависимость `pypdf`.

### Changed

- Docker v3: `embedding-shim` в профиле `rag`; WebUI не ждёт shim без профиля.
- Маршрутизация «мало OpenRouter»: все текстовые роли — `gpt-hub-turbo` → `gpt-hub-fallback`; в `litellm/config.yaml` алиасы `fast`/`strong`/`doc`/`reasoning-or` указывают на тот же локальный instruct, что и `turbo`. OpenRouter free остаётся для `gpt-hub-vision` и общего `gpt-hub-fallback`. `default_text_model` по умолчанию — `gpt-hub-turbo`.

### Notes

- Stream: fallback цепочки оркестратора по-прежнему только non-stream (LiteLLM fallbacks на stream).

## [0.1.0] — 2026-04-02

### Added

- FastAPI оркестратор: прокси `GET /v1/models`, `POST /v1/chat/completions`, Bearer auth, trace `X-GPTHub-Trace`.
- Эвристический классификатор и роутер по `model_roles.yaml` / `role_prompts.yaml`.
- Fallback по цепочке алиасов (non-stream), обработка stream и reasoning strip.
