"""Unified catalog refresh pipeline: score, probe, diff, lock."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from gpthub_orchestrator.openrouter.catalog import (
    FreeModelsCatalog,
    install_runtime_catalog,
    load_free_models_catalog,
)
from gpthub_orchestrator.openrouter.catalog_probe import run_catalog_probes
from gpthub_orchestrator.openrouter.catalog_refresh import (
    CatalogRefreshError,
    fetch_models_async,
)
from gpthub_orchestrator.openrouter.model_stats import CATALOG_SECTIONS, get_model_stats
from gpthub_orchestrator.openrouter.role_scorer import build_role_chains_from_models
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

PIPELINE_VERSION = 1


@dataclass
class CatalogCoordinator:
    """Serializes catalog mutations (refresh, curator, bandit)."""

    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    last_diff: dict[str, Any] | None = None
    last_probe_results: list[dict[str, Any]] = field(default_factory=list)
    previous_generated_at: str | None = None

    async def run_locked(self, coro_factory: Any) -> Any:
        async with self.lock:
            return await coro_factory()


def compute_catalog_diff(
    old: FreeModelsCatalog | None,
    new: FreeModelsCatalog,
) -> dict[str, Any]:
    diff: dict[str, dict[str, list[str]]] = {}
    if old is None:
        for section in CATALOG_SECTIONS:
            diff[section] = {
                "added": list(getattr(new, section)),
                "removed": [],
                "reordered": [],
            }
        return {"sections": diff, "generated_at": new.generated_at}

    for section in CATALOG_SECTIONS:
        old_chain = list(getattr(old, section))
        new_chain = list(getattr(new, section))
        old_set = set(old_chain)
        new_set = set(new_chain)
        added = [s for s in new_chain if s not in old_set]
        removed = [s for s in old_chain if s not in new_set]
        reordered: list[str] = []
        if old_chain != new_chain and not added and not removed:
            reordered = new_chain
        diff[section] = {"added": added, "removed": removed, "reordered": reordered}
    return {
        "sections": diff,
        "previous_generated_at": old.generated_at,
        "generated_at": new.generated_at,
    }


def build_catalog_from_scored_chains(chains: dict[str, list[str]]) -> FreeModelsCatalog:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = {
        "version": 1,
        "generated_at": generated_at,
        "text_fast": chains["text_fast"],
        "text_code": chains["text_code"],
        "text_doc": chains["text_doc"],
        "vision": chains["vision"],
        "fallback": chains.get("fallback") or chains["text_fast"][:1],
    }
    return FreeModelsCatalog.model_validate(payload)


def build_catalog_from_api_models(
    models: list[dict[str, Any]],
    *,
    text_limit: int = 4,
    vision_limit: int = 5,
    extra_denylist: frozenset[str] | None = None,
) -> FreeModelsCatalog:
    chains = build_role_chains_from_models(
        models,
        text_limit=text_limit,
        vision_limit=vision_limit,
        extra_denylist=extra_denylist,
    )
    return build_catalog_from_scored_chains(chains)


async def run_catalog_refresh_pipeline(
    http: httpx.AsyncClient,
    settings: Settings,
    coordinator: CatalogCoordinator,
    *,
    persist_path: Path | None = None,
    key_pool: Any = None,
    run_probes: bool | None = None,
) -> tuple[FreeModelsCatalog, dict[str, Any]]:
    """Fetch, score, probe, diff, install runtime catalog."""
    if not settings.openrouter_api_key.strip():
        raise CatalogRefreshError("OPENROUTER_API_KEY is empty")

    models = await fetch_models_async(
        http,
        api_base=settings.openrouter_api_base,
        api_key=settings.openrouter_api_key,
    )
    deny = frozenset(settings.openrouter_catalog_denylist_list())
    catalog = build_catalog_from_api_models(
        models,
        text_limit=settings.openrouter_catalog_text_limit,
        vision_limit=settings.openrouter_catalog_vision_limit,
        extra_denylist=deny,
    )

    do_probes = settings.openrouter_probe_on_refresh if run_probes is None else run_probes
    probe_results: list[dict[str, Any]] = []
    if do_probes:
        catalog, probe_results = await run_catalog_probes(
            http, settings, catalog, key_pool=key_pool
        )
        coordinator.last_probe_results = probe_results

    old = load_free_models_catalog(settings.free_models_catalog_path)
    diff = compute_catalog_diff(old, catalog)
    coordinator.last_diff = diff
    coordinator.previous_generated_at = old.generated_at

    install_runtime_catalog(catalog)
    stats = get_model_stats()
    for section in CATALOG_SECTIONS:
        stats.set_heuristic_prior(section, list(getattr(catalog, section)))

    if persist_path is not None:
        persist_path.parent.mkdir(parents=True, exist_ok=True)
        persist_path.write_text(
            yaml.safe_dump(catalog.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("catalog_persisted path=%s", persist_path)

    logger.info(
        "catalog_pipeline_ok version=%s text_fast=%s text_code=%s vision=%s",
        PIPELINE_VERSION,
        catalog.text_fast,
        catalog.text_code,
        catalog.vision,
    )
    return catalog, diff


_coordinator: CatalogCoordinator | None = None


def get_catalog_coordinator() -> CatalogCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = CatalogCoordinator()
    return _coordinator


def reset_catalog_coordinator() -> None:
    global _coordinator
    _coordinator = None
