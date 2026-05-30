"""Load and resolve free OpenRouter model catalog."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PACKAGE_CATALOG = Path(__file__).resolve().parent.parent / "data" / "free_models_catalog.yaml"

_runtime_catalog: FreeModelsCatalog | None = None


class FreeModelsCatalog(BaseModel):
    version: int = 1
    generated_at: str | None = None
    text_fast: list[str] = Field(default_factory=list, min_length=1)
    text_code: list[str] = Field(default_factory=list, min_length=1)
    text_doc: list[str] = Field(default_factory=list, min_length=1)
    vision: list[str] = Field(default_factory=list, min_length=1)
    fallback: list[str] = Field(default_factory=list, min_length=1)

    def resolve_chain(self, ref: str) -> list[str]:
        """Resolve ``catalog.text_fast`` or bare model slug."""
        ref = ref.strip()
        if ref.startswith("catalog."):
            section = ref.removeprefix("catalog.")
            if not hasattr(self, section):
                raise KeyError(f"unknown catalog section: {section}")
            chain = getattr(self, section)
            if not isinstance(chain, list) or not chain:
                raise ValueError(f"catalog section empty: {section}")
            return list(chain)
        return [ref]


def install_runtime_catalog(catalog: FreeModelsCatalog) -> None:
    """Use live catalog from OpenRouter refresh (overrides on-disk until process exit)."""
    global _runtime_catalog
    _runtime_catalog = catalog
    _load_free_models_catalog_from_disk.cache_clear()
    logger.info(
        "runtime_catalog_installed generated_at=%s text=%d vision=%d",
        catalog.generated_at,
        len(catalog.text_fast),
        len(catalog.vision),
    )


def clear_runtime_catalog() -> None:
    global _runtime_catalog
    _runtime_catalog = None
    _load_free_models_catalog_from_disk.cache_clear()


@lru_cache(maxsize=1)
def _load_free_models_catalog_from_disk(path: str | None = None) -> FreeModelsCatalog:
    p = Path(path) if path else _PACKAGE_CATALOG
    if not p.is_file():
        raise FileNotFoundError(f"free models catalog not found: {p}")
    raw = p.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise ValueError("free_models_catalog.yaml must parse to a mapping")
    parsed = FreeModelsCatalog.model_validate(data)
    logger.info(
        "free_models_catalog_loaded path=%s version=%s generated_at=%s",
        p,
        parsed.version,
        parsed.generated_at,
    )
    return parsed


def load_free_models_catalog(path: str | None = None) -> FreeModelsCatalog:
    if _runtime_catalog is not None:
        return _runtime_catalog
    return _load_free_models_catalog_from_disk(path)


def build_catalog_from_rows(
    *,
    text_rows: list[dict[str, Any]],
    vision_rows: list[dict[str, Any]],
    generated_at: str,
    text_code_rows: list[dict[str, Any]] | None = None,
    text_doc_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Legacy helper; prefer build_catalog_from_api_models / role_scorer pipeline."""
    text_ids = [str(r["id"]) for r in text_rows if r.get("id")]
    code_ids = [str(r["id"]) for r in (text_code_rows or text_rows) if r.get("id")]
    doc_ids = [str(r["id"]) for r in (text_doc_rows or text_rows) if r.get("id")]
    vision_ids = [str(r["id"]) for r in vision_rows if r.get("id")]
    if not text_ids:
        raise ValueError("no text models for catalog")
    if not vision_ids:
        raise ValueError("no vision models for catalog")
    fallback = text_ids[:1]
    return {
        "version": 1,
        "generated_at": generated_at,
        "text_fast": text_ids[:4],
        "text_code": code_ids[:4],
        "text_doc": doc_ids[:4],
        "vision": vision_ids[:5],
        "fallback": fallback,
    }
