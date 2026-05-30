"""Tests for curator routing manifest parsing and apply."""

import json

import pytest

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, clear_runtime_catalog, install_runtime_catalog
from gpthub_orchestrator.openrouter.routing_manifest import (
    RoutingManifest,
    apply_curator_manifest,
    parse_curator_json,
    reset_curator_state,
    routing_source,
)


@pytest.fixture(autouse=True)
def _reset_catalog_state():
    reset_curator_state()
    clear_runtime_catalog()
    yield
    reset_curator_state()
    clear_runtime_catalog()


def test_parse_curator_json_valid():
    raw = {
        "version": 1,
        "roles": {
            "fast_text": ["a:free", "b:free"],
            "text_code": ["c:free"],
            "text_doc": ["d:free"],
            "vision": ["v:free"],
        },
        "rationale_short": "test",
    }
    m = parse_curator_json(raw)
    assert m.version == 1
    assert m.roles.fast_text[0] == "a:free"


def test_apply_curator_manifest_overrides_runtime():
    base = FreeModelsCatalog(
        text_fast=["old:free"],
        text_code=["old:free"],
        text_doc=["old:free"],
        vision=["old-v:free"],
        fallback=["old:free"],
    )
    install_runtime_catalog(base)
    manifest = RoutingManifest.model_validate(
        {
            "version": 2,
            "roles": {
                "fast_text": ["new:free"],
                "text_code": ["new-code:free"],
                "text_doc": ["new-doc:free"],
                "vision": ["new-v:free"],
            },
        }
    )
    apply_curator_manifest(manifest, base_catalog=base)
    assert routing_source() == "curator"
    from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog

    cat = load_free_models_catalog()
    assert cat.text_fast == ["new:free"]
    assert cat.vision == ["new-v:free"]


def test_parse_curator_json_from_string():
    raw = json.dumps(
        {
            "version": 1,
            "roles": {
                "fast_text": ["x:free"],
                "text_code": ["x:free"],
                "text_doc": ["x:free"],
                "vision": ["y:free"],
            },
        }
    )
    m = parse_curator_json(raw)
    assert m.roles.vision == ["y:free"]
