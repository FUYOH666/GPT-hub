"""Tests for catalog diff and coordinator lock."""

from __future__ import annotations

import asyncio

import pytest

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.openrouter.catalog_pipeline import (
    CatalogCoordinator,
    compute_catalog_diff,
    reset_catalog_coordinator,
)


@pytest.fixture(autouse=True)
def _reset_coordinator():
    reset_catalog_coordinator()
    yield
    reset_catalog_coordinator()


def _cat(**sections: list[str]) -> FreeModelsCatalog:
    base = {
        "version": 1,
        "generated_at": "2026-01-01T00:00:00Z",
        "text_fast": ["a:free"],
        "text_code": ["b:free"],
        "text_doc": ["c:free"],
        "vision": ["v:free"],
        "fallback": ["a:free"],
    }
    base.update(sections)
    return FreeModelsCatalog.model_validate(base)


def test_compute_catalog_diff_added_removed():
    old = _cat()
    new = _cat(text_fast=["x:free", "a:free"], vision=["w:free"])
    diff = compute_catalog_diff(old, new)
    assert "x:free" in diff["sections"]["text_fast"]["added"]
    assert "v:free" in diff["sections"]["vision"]["removed"]


@pytest.mark.asyncio
async def test_coordinator_lock_serializes():
    coord = CatalogCoordinator()
    order: list[str] = []

    async def job(name: str, delay: float) -> None:
        async with coord.lock:
            order.append(f"{name}_start")
            await asyncio.sleep(delay)
            order.append(f"{name}_end")

    await asyncio.gather(job("a", 0.05), job("b", 0.01))
    assert order.index("a_start") < order.index("a_end")
    assert order.index("b_start") < order.index("b_end")
    # one job fully inside the other
    assert (order[0].endswith("_start") and order[1].endswith("_start")) is False
