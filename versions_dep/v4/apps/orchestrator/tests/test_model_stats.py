"""Tests for bandit EMA stats and resort."""

from __future__ import annotations

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, clear_runtime_catalog, install_runtime_catalog
from gpthub_orchestrator.openrouter.model_stats import ModelStatsTracker, reset_model_stats
from gpthub_orchestrator.openrouter.routing_manifest import reset_curator_state, routing_source


def _catalog() -> FreeModelsCatalog:
    return FreeModelsCatalog.model_validate(
        {
            "version": 1,
            "generated_at": "t",
            "text_fast": ["slow:free", "fast:free"],
            "text_code": ["b:free"],
            "text_doc": ["c:free"],
            "vision": ["v:free"],
            "fallback": ["slow:free"],
        }
    )


def test_bandit_resort_swaps_head_after_samples():
    reset_model_stats()
    reset_curator_state()
    clear_runtime_catalog()
    tracker = ModelStatsTracker(min_samples_for_resort=3)
    tracker.set_heuristic_prior("text_fast", ["slow:free", "fast:free"])
    for _ in range(5):
        tracker.record_attempt(
            section="text_fast",
            slug="fast:free",
            success=True,
            status_code=200,
            latency_ms=100.0,
        )
        tracker.record_attempt(
            section="text_fast",
            slug="slow:free",
            success=False,
            status_code=429,
            latency_ms=5000.0,
        )
    cat = _catalog()
    install_runtime_catalog(cat)
    updated = tracker.resort_catalog(cat)
    assert updated is not None
    assert updated.text_fast[0] == "fast:free"
    assert routing_source() == "bandit"
