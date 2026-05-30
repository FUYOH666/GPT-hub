# Staff review — GPTHub v4 (OpenRouter Survival Engine)

**Scope:** `versions_dep/v4/` orchestrator, docker-compose, v4 docs, CI workflows; root docs `ZERO_ENTRY.md`, `DEMO_PROMPTS.md`.  
**Excluded:** legacy v1–v3 runtime, vendored Open WebUI image internals, lock-file-only diffs.  
**Date:** 2026-05-30  
**Mode:** full pipeline

---

## Scope

**Goal:** v4 as zero-entry product — Open WebUI → orchestrator → OpenRouter free with routing, fallback, trace, optional curator.

**Modules:** `gpthub_orchestrator/main.py`, `openrouter/*`, `classifier.py`, `router.py`, `ingest/*`, `trace.py`, Docker, `.github/workflows/ci.yml`.

**Assumption:** single-tenant / family deploy; not multi-tenant SaaS.

---

## Correctness & logic

- **Classifier → router → chain** is deterministic and well-tested offline (`test_routing_golden.py`), but golden tests **hardcode catalog slugs** — breaks when live refresh reorder chains (fixed in this validation sprint via invariants).
- **Stream fallback** (`client.chat_completions_stream`) retries before bytes are sent — correct; once stream starts, no mid-stream retry (documented behavior).
- **Curator + periodic refresh** both mutate runtime catalog **under `CatalogCoordinator` lock** — resolved 2026-05-30 (control loop sprint).
- **`ingest_image_fetch_timeout`** in `settings.py` has **no consumer** — image URLs pass through to OpenRouter unchanged; dead config.
- **Health ban** is in-memory only — lost on restart; acceptable for MVP, document clearly.

---

## Architecture fit

- Clear layers: classifier / router / OpenRouterClient / catalog — good separation.
- **Survival Engine** (model-first, key rotation) is cohesive and testable.
- Duplication: catalog refresh logic in lifespan and `_refresh_catalog_task` — minor, acceptable.
- Curator as async overlay on heuristics matches product intent; trace exposes `routing_source`.

---

## Security & privacy

- **Admin API key defaults to `ORCHESTRATOR_API_KEY`** — same bearer for chat and `/v1/admin/catalog`. Should use separate `ORCHESTRATOR_ADMIN_API_KEY` in production (supported but not enforced in docs).
- **`GET /trace`** is **unauthenticated** — fine for localhost; must not be exposed on public ingress (same as orchestrator `:8089`).
- **Ingest** handles base64/data-URL files only; no HTTP fetch for arbitrary URLs in ingest path — SSRF risk low for current code.
- **Secrets:** `.env` gitignored; docker-compose passes env — OK.
- **Open WebUI** `ENABLE_SIGNUP=true` default — document single-admin hardening (`OPENWEBUI_ROLES.md`).

---

## Reliability & ops

- `/healthz`, `/readyz` present; readyz includes catalog meta — good.
- **OpenRouter exhausted** returns RU message + trace — good UX.
- **Packaged vs runtime catalog:** refresh writes `free_models_catalog.runtime.yaml`, not packaged YAML — good fix.
- Logging structured via `logging`; execution trace JSON in logs — ops-friendly.
- **No metrics endpoint** (Prometheus) — backlog item.

---

## Performance

- Single-process FastAPI; key pool RPM throttle — adequate for free tier.
- Curator one-shot LLM call on startup — bounded by `OPENROUTER_CURATOR_TIMEOUT`.
- No hot-path concerns for MVP scale.

---

## Tests & verification

- **92 pytest** with mocks — strong unit/integration base.
- **Gap:** no E2E routing matrix against real HTTP stack before this sprint (`verify_v4.sh` = 1 scenario).
- **Gap:** no automated fault-injection suite (429 cascade, exhausted).
- **Gap:** stream scenarios not in smoke scripts.
- CI runs pytest only — ops simulator (mock) addresses E2E gap.

---

## Docs & DX

- `ZERO_ENTRY.md`, v4 README, ROADMAP — good product narrative.
- **`DEMO_PROMPTS.md` still v3-branded** — should-fix (addressed in validation sprint).
- `.env.example` documents new flags — good.
- Validation playbook missing until ops simulator landed.

---

## Findings

| ID | Severity | Location | Recommendation |
|----|----------|----------|----------------|
| F1 | should-fix | `settings.py` default admin key = orchestrator key | Document separate admin key for prod; consider distinct default in `.env.example` |
| F2 | should-fix | `main.py` curator + `_periodic_catalog_refresh` | Serialize catalog mutations (async lock) or skip refresh while curator running |
| F3 | should-fix | `test_routing_golden.py`, `test_router.py` | Assert role + chain invariants, not fixed slugs |
| F4 | should-fix | `docs/DEMO_PROMPTS.md` | Update for v4 trace fields, stream, admin, simulator |
| F5 | should-fix | CI `.github/workflows/ci.yml` | Add mock ops simulator job |
| F6 | should-fix | `settings.py` `ingest_image_fetch_timeout` | Implement or remove dead setting |
| F7 | nit | `main.py` `/trace` | Add note in README: do not expose publicly |
| F8 | nit | `verify_v4.sh` | Extend or delegate to ops simulator |
| F9 | backlog | — | Prometheus metrics: fallback rate, exhausted count |
| F10 | backlog | — | WebUI Playwright E2E |
| F11 | backlog | — | Curator A/B report (heuristic vs curator on same scenarios) |

---

## Verdict

**Needs targeted fixes before calling v4 “validation-complete”** — no blockers for local/family use; address F1–F5 in validation sprint. Architecture is sound for stated MVP; main risks are **test brittleness**, **missing E2E fault coverage**, and **catalog race** under curator + periodic refresh.

After ops simulator mock CI green + live report: **ready for wider beta** with documented ops constraints (free tier, no public `:8089`).
