import os

import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "or-test-key")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "k")

from gpthub_orchestrator.model_registry import load_model_roles
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings


def _settings(**kwargs):
    base = {
        "openrouter_api_key": "or-test-key",
        "orchestrator_api_key": "k",
    }
    base.update(kwargs)
    return Settings(**base)


def test_router_vision_role():
    s = _settings()
    out = choose_model({"modalities": ["text", "image"], "task_type": "image_analysis"}, s)
    assert out["model_role"] == "vision_general"
    assert out["model_name"] == "qwen/qwen3.6-plus:free"
    assert "google/gemma-3-4b-it:free" in out["fallback_aliases"]


def test_router_doc_role():
    s = _settings()
    out = choose_model({"modalities": ["text"], "task_type": "summarization"}, s)
    assert out["model_role"] == "doc_synthesis"
    assert out["model_name"] == "google/gemma-3-12b-it:free"


def test_router_code_local_preference():
    s = _settings(code_route_preference="local")
    out = choose_model({"modalities": ["text"], "task_type": "code_help"}, s)
    assert out["model_role"] == "reasoning_code_local"
    assert out["model_name"] == "qwen/qwen3-4b:free"


def test_router_code_openrouter_preference():
    s = _settings(code_route_preference="openrouter")
    out = choose_model({"modalities": ["text"], "task_type": "code_help"}, s)
    assert out["model_role"] == "reasoning_code_openrouter"
    assert out["model_name"] == "qwen/qwen3-4b:free"


def test_router_fast_text():
    s = _settings()
    out = choose_model({"modalities": ["text"], "task_type": "simple_chat"}, s)
    assert out["model_role"] == "fast_text"
    assert out["model_name"] == "google/gemma-3-4b-it:free"


def test_router_greeting_or_tiny():
    s = _settings()
    out = choose_model({"modalities": ["text"], "task_type": "greeting_or_tiny"}, s)
    assert out["model_role"] == "fast_text_chat"
    assert out["model_name"] == "google/gemma-3-4b-it:free"
