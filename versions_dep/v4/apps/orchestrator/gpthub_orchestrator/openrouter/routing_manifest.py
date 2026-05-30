"""Curator-produced routing manifest (strict JSON / Pydantic)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, install_runtime_catalog

logger = logging.getLogger(__name__)

_PACKAGE_SCHEMA = Path(__file__).resolve().parent.parent / "data" / "routing_manifest.schema.json"

_curator_manifest: RoutingManifest | None = None
_routing_source: str = "heuristic"


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


def routing_source() -> str:
    return _routing_source


def curator_manifest() -> RoutingManifest | None:
    return _curator_manifest


def apply_curator_manifest(manifest: RoutingManifest, *, base_catalog: FreeModelsCatalog) -> FreeModelsCatalog:
    """Overlay curator role chains onto runtime catalog."""
    global _curator_manifest, _routing_source
    roles = manifest.roles
    updated = base_catalog.model_copy(
        update={
            "text_fast": roles.fast_text,
            "text_code": roles.text_code,
            "text_doc": roles.text_doc,
            "vision": roles.vision,
            "fallback": roles.fast_text[:1],
        }
    )
    install_runtime_catalog(updated)
    _curator_manifest = manifest
    _routing_source = "curator"
    logger.info(
        "curator_manifest_applied version=%s text_fast=%s vision=%s",
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
