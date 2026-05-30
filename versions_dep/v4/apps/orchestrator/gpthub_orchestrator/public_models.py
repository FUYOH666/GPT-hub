"""Public model catalog for Open WebUI (single facade vs catalog list)."""

from __future__ import annotations

import copy
import logging
from typing import Any

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)


def build_models_list(settings: Settings, catalog: FreeModelsCatalog | None = None) -> dict[str, Any]:
    if settings.orchestrator_models_catalog == "all" and catalog is not None:
        seen: set[str] = set()
        data: list[dict[str, Any]] = []
        for section in ("text_fast", "text_code", "text_doc", "vision", "fallback"):
            for mid in getattr(catalog, section, []) or []:
                if mid in seen:
                    continue
                seen.add(mid)
                data.append({"object": "model", "id": mid, "owned_by": "openrouter"})
        return {"object": "list", "data": data}

    public_id = settings.orchestrator_public_model_id
    return {
        "object": "list",
        "data": [{"object": "model", "id": public_id, "owned_by": "gpthub"}],
    }


def apply_models_catalog(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    return copy.deepcopy(payload)


def map_facade_model_to_backend(body: dict[str, Any], settings: Settings) -> None:
    """When auto-routing is off, map public facade id to default text slug."""
    if settings.auto_route_model:
        return
    mid = body.get("model")
    if not isinstance(mid, str):
        return
    if mid.strip() != settings.orchestrator_public_model_id:
        return
    body["model"] = settings.default_text_model
    logger.info(
        "facade_model_mapped facade=%s openrouter_slug=%s",
        settings.orchestrator_public_model_id,
        settings.default_text_model,
    )
