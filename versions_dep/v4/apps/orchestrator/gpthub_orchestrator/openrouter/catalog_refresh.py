"""Fetch live free models from OpenRouter and build runtime catalog."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from gpthub_orchestrator.openrouter.catalog import (
    FreeModelsCatalog,
    build_catalog_from_rows,
    install_runtime_catalog,
)
from gpthub_orchestrator.tools.list_free_models import (
    filter_free,
    is_excluded_from_text_suggest,
    is_excluded_from_vision_suggest,
    order_free_text_rows,
    order_free_vision_rows,
    simplify,
)

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


def build_catalog_from_api_models(
    models: list[dict[str, Any]],
    *,
    text_limit: int = 4,
    vision_limit: int = 5,
) -> FreeModelsCatalog:
    text_rows = order_free_text_rows(
        [simplify(m) for m in filter_free(models, vision_only=False, text_only=True)]
    )
    text_rows = [r for r in text_rows if not is_excluded_from_text_suggest(str(r.get("id") or ""))]
    vision_rows = order_free_vision_rows([simplify(m) for m in filter_free(models, vision_only=True)])
    vision_rows = [r for r in vision_rows if not is_excluded_from_vision_suggest(str(r.get("id") or ""))]
    text_rows = text_rows[: max(1, text_limit)]
    vision_rows = vision_rows[: max(1, vision_limit)]
    if not text_rows or not vision_rows:
        raise CatalogRefreshError("no free text or vision models after filtering")
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    payload = build_catalog_from_rows(
        text_rows=text_rows,
        vision_rows=vision_rows,
        generated_at=generated_at,
    )
    return FreeModelsCatalog.model_validate(payload)


async def refresh_catalog_from_openrouter(
    http: httpx.AsyncClient,
    *,
    api_key: str,
    api_base: str,
    text_limit: int = 4,
    vision_limit: int = 5,
    persist_path: Path | None = None,
) -> FreeModelsCatalog:
    """Pull current free models from OpenRouter and activate as runtime catalog."""
    if not api_key.strip():
        raise CatalogRefreshError("OPENROUTER_API_KEY is empty")
    models = await fetch_models_async(http, api_base=api_base, api_key=api_key)
    catalog = build_catalog_from_api_models(models, text_limit=text_limit, vision_limit=vision_limit)
    install_runtime_catalog(catalog)
    if persist_path is not None:
        persist_path.parent.mkdir(parents=True, exist_ok=True)
        persist_path.write_text(
            yaml.safe_dump(catalog.model_dump(), allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        logger.info("catalog_persisted path=%s", persist_path)
    logger.info(
        "catalog_refreshed generated_at=%s text_fast=%s vision=%s",
        catalog.generated_at,
        catalog.text_fast,
        catalog.vision,
    )
    return catalog
