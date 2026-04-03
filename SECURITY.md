# Security

Report **undisclosed** security issues privately to the maintainer listed in [AUTHORS.md](AUTHORS.md) (e.g. via GitHub security advisory or direct contact). Do not open a public issue for active vulnerabilities.

**Scope:** This repository contains integration code (orchestrator, Docker, docs). Deployments also use third-party images and services (Open WebUI, LiteLLM, optional cloud APIs, tunnels). Review their security guidance and keep secrets in `.env`, never committed.

**Secrets:** If a key or token was ever committed, rotate it immediately; history may retain it until rewritten.
