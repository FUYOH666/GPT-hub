"""Tests for catalog probe demotion."""

from __future__ import annotations

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.openrouter.catalog_probe import (
    apply_probe_demotions,
    demote_slug_in_chain,
)


def test_demote_slug_moves_to_tail():
    chain = ["a:free", "b:free", "c:free"]
    assert demote_slug_in_chain(chain, "a:free") == ["b:free", "c:free", "a:free"]


def test_apply_probe_demotions_on_failure():
    catalog = FreeModelsCatalog.model_validate(
        {
            "version": 1,
            "generated_at": "t",
            "text_fast": ["bad:free", "good:free"],
            "text_code": ["b:free"],
            "text_doc": ["c:free"],
            "vision": ["v:free"],
            "fallback": ["bad:free"],
        }
    )
    results = [{"section": "text_fast", "slug": "bad:free", "ok": False, "status_code": 429}]
    updated = apply_probe_demotions(catalog, results)
    assert updated.text_fast == ["good:free", "bad:free"]
    assert updated.fallback == ["good:free"]
