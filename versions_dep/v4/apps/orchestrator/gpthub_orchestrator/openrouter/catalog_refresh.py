"""Fetch live free models from OpenRouter and build runtime catalog."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)


class CatalogRefreshError(Exception):
    """OpenRouter models API failed or returned no usable free models."""


async def fetch_models_async(
    http: httpx.AsyncClient,
    *,
    api_base: str,
    api_key: str,
) -> list[dict[str, Any]]:
    url = f"{api_base.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {api_key.strip()}"}
    resp = await http.get(url, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    raw = data.get("data")
    if not isinstance(raw, list):
        raise CatalogRefreshError("OpenRouter response missing data array")
    return raw


async def refresh_catalog_from_openrouter(
    http: httpx.AsyncClient,
    *,
    api_key: str,
    api_base: str,
    text_limit: int = 4,
    vision_limit: int = 5,
    persist_path: Path | None = None,
    settings: Settings | None = None,
    key_pool: Any = None,
) -> FreeModelsCatalog:
    """Pull current free models from OpenRouter and activate as runtime catalog."""
    if not api_key.strip():
        raise CatalogRefreshError("OPENROUTER_API_KEY is empty")

    from gpthub_orchestrator.openrouter.catalog_pipeline import (
        get_catalog_coordinator,
        run_catalog_refresh_pipeline,
    )

    coordinator = get_catalog_coordinator()
    if settings is None:
        settings = Settings(
            openrouter_api_key=api_key,
            openrouter_api_base=api_base,
            openrouter_catalog_text_limit=text_limit,
            openrouter_catalog_vision_limit=vision_limit,
            orchestrator_api_key="refresh-internal",
        )

    async def _run() -> FreeModelsCatalog:
        catalog, _diff = await run_catalog_refresh_pipeline(
            http,
            settings,
            coordinator,
            persist_path=persist_path,
            key_pool=key_pool,
        )
        return catalog

    return await coordinator.run_locked(_run)
