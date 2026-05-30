"""Curator-produced routing manifest (strict JSON / Pydantic)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, install_runtime_catalog

logger = logging.getLogger(__name__)

_PACKAGE_SCHEMA = Path(__file__).resolve().parent.parent / "data" / "routing_manifest.schema.json"

_curator_manifest: RoutingManifest | None = None
_routing_source: str = "heuristic"

MergeMode = Literal["overlay", "replace"]


class RoutingManifestRoles(BaseModel):
    fast_text: list[str] = Field(min_length=1)
    text_code: list[str] = Field(min_length=1)
    text_doc: list[str] = Field(min_length=1)
    vision: list[str] = Field(min_length=1)


class RoutingManifest(BaseModel):
    version: int = Field(ge=1)
    roles: RoutingManifestRoles
    rationale_short: str | None = None

    @field_validator("roles", mode="before")
    @classmethod
    def strip_role_slugs(cls, v: object) -> object:
        if not isinstance(v, dict):
            return v
        cleaned: dict[str, list[str]] = {}
        for key, slugs in v.items():
            if isinstance(slugs, list):
                cleaned[key] = [str(s).strip() for s in slugs if str(s).strip()]
            else:
                cleaned[key] = slugs  # type: ignore[assignment]
        return cleaned


def parse_curator_json(raw: str | dict[str, Any]) -> RoutingManifest:
    data = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(data, dict):
        raise ValueError("curator output must be a JSON object")
    return RoutingManifest.model_validate(data)


def set_routing_source(source: str) -> None:
    global _routing_source
    if source in ("heuristic", "curator", "bandit"):
        _routing_source = source


def routing_source() -> str:
    return _routing_source


def curator_manifest() -> RoutingManifest | None:
    return _curator_manifest


def _merge_overlay(
    heuristic: list[str],
    curator: list[str],
    *,
    allowed_pool: set[str],
) -> list[str]:
    """Curator reorder within pool; unknown slugs appended if in allowed_pool."""
    pool = [s for s in heuristic if s in allowed_pool]
    if not pool:
        pool = list(heuristic)
    ordered: list[str] = []
    for slug in curator:
        if slug in allowed_pool and slug not in ordered:
            ordered.append(slug)
    for slug in pool:
        if slug not in ordered:
            ordered.append(slug)
    return ordered or list(heuristic)


def apply_curator_manifest(
    manifest: RoutingManifest,
    *,
    base_catalog: FreeModelsCatalog,
    merge_mode: MergeMode = "overlay",
    allowed_pool: set[str] | None = None,
) -> FreeModelsCatalog:
    """Overlay or replace curator role chains onto runtime catalog."""
    global _curator_manifest, _routing_source
    roles = manifest.roles
    pool = allowed_pool or set(
        base_catalog.text_fast
        + base_catalog.text_code
        + base_catalog.text_doc
        + base_catalog.vision
    )

    if merge_mode == "replace":
        updated = base_catalog.model_copy(
            update={
                "text_fast": roles.fast_text,
                "text_code": roles.text_code,
                "text_doc": roles.text_doc,
                "vision": roles.vision,
                "fallback": roles.fast_text[:1],
            }
        )
    else:
        updated = base_catalog.model_copy(
            update={
                "text_fast": _merge_overlay(base_catalog.text_fast, roles.fast_text, allowed_pool=pool),
                "text_code": _merge_overlay(base_catalog.text_code, roles.text_code, allowed_pool=pool),
                "text_doc": _merge_overlay(base_catalog.text_doc, roles.text_doc, allowed_pool=pool),
                "vision": _merge_overlay(base_catalog.vision, roles.vision, allowed_pool=pool),
                "fallback": _merge_overlay(
                    base_catalog.text_fast, roles.fast_text, allowed_pool=pool
                )[:1],
            }
        )
    install_runtime_catalog(updated)
    _curator_manifest = manifest
    _routing_source = "curator"
    logger.info(
        "curator_manifest_applied mode=%s version=%s text_fast=%s vision=%s",
        merge_mode,
        manifest.version,
        updated.text_fast,
        updated.vision,
    )
    return updated


def reset_curator_state() -> None:
    global _curator_manifest, _routing_source
    _curator_manifest = None
    _routing_source = "heuristic"


def schema_json() -> dict[str, Any]:
    if _PACKAGE_SCHEMA.is_file():
        return json.loads(_PACKAGE_SCHEMA.read_text(encoding="utf-8"))
    return RoutingManifest.model_json_schema()
