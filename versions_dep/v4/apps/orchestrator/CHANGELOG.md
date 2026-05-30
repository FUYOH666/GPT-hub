# gpthub-orchestrator v4

## Unreleased — auto catalog control loop

- Role-specific scoring (`role_scorer`) — differentiated `text_fast` / `text_code` / `text_doc` / `vision`
- Catalog pipeline: diff, coordinator lock, probe-on-refresh (default ON), bandit EMA resort
- Curator overlay merge after refresh; admin API: `catalog_diff`, `probe_results`, `bandit_stats`
- 104 pytest; ops_simulator mock 17/17

## 0.4.0 — OpenRouter Free Survival Engine

- Direct OpenRouter API client (no LiteLLM)
- Key pool: multi-key rotation, RPM throttle, cooldown
- Live catalog refresh on startup + optional periodic refresh
- Stream fallback chain; runtime model health ban after 429
- Optional async LLM Model Curator → `RoutingManifest`
- `/trace` page; `/v1/admin/catalog`
- RU user message for `openrouter_exhausted`
- Trace: `routing_source`, `manifest_version`, `model_attempts`, `quota_remaining`
