"""Capability-based model routing: roles → OpenRouter slug chains."""

from __future__ import annotations

import logging
from typing import Any

from gpthub_orchestrator.model_registry import (
    ROLE_DOC,
    ROLE_FAST_TEXT,
    ROLE_FAST_TEXT_CHAT,
    ROLE_REASONING_LOCAL,
    ROLE_REASONING_OPENROUTER,
    ROLE_VISION,
    aliases_for_role,
    load_model_roles,
)
from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.openrouter.routing_manifest import curator_manifest, routing_source
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

_ROLE_CATALOG_SECTION: dict[str, str] = {
    ROLE_FAST_TEXT_CHAT: "text_fast",
    ROLE_FAST_TEXT: "text_fast",
    ROLE_REASONING_LOCAL: "text_code",
    ROLE_REASONING_OPENROUTER: "text_code",
    ROLE_DOC: "text_doc",
    ROLE_VISION: "vision",
}


def choose_model(classification: dict[str, Any], settings: Settings) -> dict[str, Any]:
    modalities = classification.get("modalities") or ["text"]
    task_type = classification.get("task_type") or "simple_chat"
    has_image = "image" in modalities

    registry = load_model_roles(settings.model_roles_path)
    catalog = load_free_models_catalog(settings.free_models_catalog_path)

    if has_image:
        role_key = ROLE_VISION
        reason = "vision_multimodal_content"
    elif task_type in ("summarization", "file_analysis"):
        role_key = ROLE_DOC
        reason = "document_or_summary_heuristic"
    elif task_type in ("code_help", "multimodal_workflow"):
        if settings.code_route_preference == "openrouter":
            role_key = ROLE_REASONING_OPENROUTER
            reason = "code_or_deep_analysis_openrouter"
        else:
            role_key = ROLE_REASONING_LOCAL
            reason = "code_or_deep_analysis_local_first"
    elif task_type == "greeting_or_tiny":
        role_key = ROLE_FAST_TEXT_CHAT
        reason = "greeting_or_tiny_chat"
    else:
        role_key = ROLE_FAST_TEXT
        reason = "default_text_chat"

    chain = aliases_for_role(registry, role_key, catalog_path=settings.free_models_catalog_path)
    meta = {
        "model_name": chain[0],
        "model_role": role_key,
        "catalog_section": _ROLE_CATALOG_SECTION.get(role_key, "text_fast"),
        "fallback_aliases": chain,
        "openrouter_chain": chain,
        "catalog_version": catalog.version,
        "catalog_generated_at": catalog.generated_at,
        "routing_source": routing_source(),
        "manifest_version": (curator_manifest().version if curator_manifest() else None),
        "reason": reason,
        "task_type": task_type,
    }
    logger.info("model_router_choice %s", meta)
    return meta
