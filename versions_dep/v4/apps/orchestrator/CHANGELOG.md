# gpthub-orchestrator v4

## 0.4.0 — OpenRouter Free Survival Engine

- Direct OpenRouter API client (no LiteLLM)
- Key pool: multi-key rotation, RPM throttle, cooldown
- Live catalog refresh on startup + optional periodic refresh
- Stream fallback chain; runtime model health ban after 429
- Optional async LLM Model Curator → `RoutingManifest`
- `/trace` page; `/v1/admin/catalog`
- RU user message for `openrouter_exhausted`
- Trace: `routing_source`, `manifest_version`, `model_attempts`, `quota_remaining`
