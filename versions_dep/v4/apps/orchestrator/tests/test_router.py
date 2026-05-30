import os

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "or-test-key")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "k")

from gpthub_orchestrator.model_registry import load_model_roles
from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.ops.routing_invariants import ScenarioExpect, assert_router_suggestion_invariants
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings


def _settings(**kwargs):
    base = {
        "openrouter_api_key": "or-test-key",
        "orchestrator_api_key": "k",
    }
    base.update(kwargs)
    return Settings(**base)


def _assert_chain_invariants(out: dict) -> None:
    chain = list(out.get("fallback_aliases") or [])
    assert chain, "empty fallback_aliases"
    head = str(out.get("model_name") or "")
    assert head == chain[0]
    assert head in chain


def test_router_vision_role():
    s = _settings()
    out = choose_model({"modalities": ["text", "image"], "task_type": "image_analysis"}, s)
    assert out["model_role"] == "vision_general"
    _assert_chain_invariants(out)
    catalog = load_free_models_catalog()
    assert out["model_name"] in catalog.vision


def test_router_doc_role():
    s = _settings()
    out = choose_model({"modalities": ["text"], "task_type": "summarization"}, s)
    assert out["model_role"] == "doc_synthesis"
    _assert_chain_invariants(out)
    catalog = load_free_models_catalog()
    assert out["model_name"] in catalog.text_doc


def test_router_code_local_preference():
    s = _settings(code_route_preference="local")
    out = choose_model({"modalities": ["text"], "task_type": "code_help"}, s)
    assert out["model_role"] == "reasoning_code_local"
    _assert_chain_invariants(out)
    catalog = load_free_models_catalog()
    assert out["model_name"] in catalog.text_code


def test_router_code_openrouter_preference():
    s = _settings(code_route_preference="openrouter")
    out = choose_model({"modalities": ["text"], "task_type": "code_help"}, s)
    assert out["model_role"] == "reasoning_code_openrouter"
    _assert_chain_invariants(out)


def test_router_fast_text():
    s = _settings()
    msgs = [{"role": "user", "content": "Explain Python lists briefly."}]
    assert_router_suggestion_invariants(
        messages=msgs,
        settings=s,
        expect=ScenarioExpect(task_type="simple_chat", model_role="fast_text"),
    )


def test_router_greeting_or_tiny():
    s = _settings()
    msgs = [{"role": "user", "content": "Привет!"}]
    assert_router_suggestion_invariants(
        messages=msgs,
        settings=s,
        expect=ScenarioExpect(task_type="greeting_or_tiny", model_role="fast_text_chat"),
    )
