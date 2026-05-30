# GPTHub

**OpenRouter free за 3 команды** — один ключ, Docker, чат в браузере. Оркестратор сам выбирает бесплатную модель, переключается при 429 и показывает trace «кто ответил».

Пошагово для всех: **[docs/ZERO_ENTRY.md](docs/ZERO_ENTRY.md)**.

## Quick start (v4)

```bash
cd versions_dep/v4
cp .env.example .env   # ORCHESTRATOR_API_KEY, OPENROUTER_API_KEY, WEBUI_SECRET_KEY
docker compose up -d --build
```

- Open WebUI: http://localhost:3000  
- Trace decoder: http://localhost:8089/trace  
- Подробности: [docs/ZERO_ENTRY.md](docs/ZERO_ENTRY.md)

## Status

**Active line — v4** (OpenRouter Free Survival Engine): Open WebUI → orchestrator → OpenRouter free models. See [versions_dep/v4/README.md](versions_dep/v4/README.md).

**Legacy — v1–v3** (LiteLLM hybrid, frozen): [versions_dep/LEGACY.md](versions_dep/LEGACY.md).

## Documentation

Full map: **[docs/README.md](docs/README.md)** — product, ops, reviews, archive (≤2 clicks from here).

## Contributing · License · Authors

- [CONTRIBUTING.md](CONTRIBUTING.md) · [LICENSE](LICENSE) (MIT) · [AUTHORS.md](AUTHORS.md)
- Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) · Security: [SECURITY.md](SECURITY.md)

## Acknowledgments

Stars and issues welcome. Maintainer: [**@FUYOH666**](https://github.com/FUYOH666).

This repo started as a hackathon learning project; background: [docs/archive/hackathon/ORIGIN.md](docs/archive/hackathon/ORIGIN.md).

Third-party OSS (Open WebUI, etc.) — under their respective licenses.
