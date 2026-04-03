"""Unit tests for OpenRouter free-model listing helpers."""

from __future__ import annotations

from gpthub_orchestrator.tools.list_free_models import (
    build_litellm_vision_snippet,
    is_excluded_from_vision_suggest,
    order_free_vision_rows,
    vision_model_sort_key,
)


def test_vision_model_sort_key_google_after_non_google() -> None:
    a = {"id": "qwen/foo:free", "context_length": 1000, "input_modalities": ["text", "image"]}
    b = {"id": "google/gemma-3-27b-it:free", "context_length": 100000, "input_modalities": ["text", "image"]}
    assert vision_model_sort_key(a) < vision_model_sort_key(b)


def test_vision_model_sort_key_larger_context_first_within_provider_group() -> None:
    a = {"id": "qwen/small:free", "context_length": 1000, "input_modalities": ["image"]}
    b = {"id": "qwen/big:free", "context_length": 50000, "input_modalities": ["image"]}
    assert vision_model_sort_key(b) < vision_model_sort_key(a)


def test_order_free_vision_rows_stable_by_id() -> None:
    rows = [
        {"id": "z/z:free", "context_length": 100, "input_modalities": ["image"]},
        {"id": "a/a:free", "context_length": 100, "input_modalities": ["image"]},
    ]
    out = order_free_vision_rows(rows)
    assert [r["id"] for r in out] == ["a/a:free", "z/z:free"]


def test_vision_suggest_excludes_unstable_free_router_slug() -> None:
    assert is_excluded_from_vision_suggest("openrouter/free")
    assert not is_excluded_from_vision_suggest("qwen/x:free")


def test_vision_suggest_excludes_lyria_prefix() -> None:
    assert is_excluded_from_vision_suggest("google/lyria-3-pro-preview")


def test_build_litellm_vision_snippet_contains_openrouter_prefix() -> None:
    text = build_litellm_vision_snippet(["qwen/qwen3.6-plus:free", "nvidia/nemotron-nano-12b-v2-vl:free"])
    assert "gpt-hub-vision" in text
    assert "openrouter/qwen/qwen3.6-plus:free" in text
    assert "gpt-hub-turbo" not in text
