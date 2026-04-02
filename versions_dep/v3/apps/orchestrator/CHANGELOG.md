# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Ingest pipeline (phase 1): PDF из `file` + data URL, аудио через ASR (`ORCHESTRATOR_ASR_*`), `asyncio.gather`, trace `ingest_ms` / `artifacts`.
- `GET /readyz` — проверка `GET …/health/liveliness` у LiteLLM.
- Зависимость `pypdf`.

### Changed

- Docker v3: `embedding-shim` в профиле `rag`; WebUI не ждёт shim без профиля.

### Notes

- Stream: fallback цепочки оркестратора по-прежнему только non-stream (LiteLLM fallbacks на stream).

## [0.1.0] — 2026-04-02

### Added

- FastAPI оркестратор: прокси `GET /v1/models`, `POST /v1/chat/completions`, Bearer auth, trace `X-GPTHub-Trace`.
- Эвристический классификатор и роутер по `model_roles.yaml` / `role_prompts.yaml`.
- Fallback по цепочке алиасов (non-stream), обработка stream и reasoning strip.
