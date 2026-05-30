"""Tests for role-specific model scoring."""

from __future__ import annotations

from gpthub_orchestrator.openrouter.role_scorer import (
    build_role_chains_from_models,
    score_fast_text,
    score_text_code,
    score_text_doc,
    score_vision,
)
from gpthub_orchestrator.tools.list_free_models import simplify


def _row(slug: str, *, ctx: int = 131072, modalities: list[str] | None = None) -> dict:
    return simplify(
        {
            "id": slug,
            "name": slug,
            "context_length": ctx,
            "architecture": {"input_modalities": modalities or ["text"]},
            "pricing": {"prompt": "0", "completion": "0"},
        }
    )


def test_fast_text_prefers_small_models():
    rows = [
        _row("liquid/lfm-2.5-1.2b-instruct:free", ctx=32768),
        _row("meta-llama/llama-3.3-70b-instruct:free"),
        _row("qwen/qwen3-coder:free", ctx=1048576),
    ]
    assert score_fast_text(rows[0]) > score_fast_text(rows[1])
    assert score_fast_text(rows[0]) > score_fast_text(rows[2])


def test_code_prefers_coder_slug():
    rows = [
        _row("meta-llama/llama-3.2-3b-instruct:free"),
        _row("qwen/qwen3-coder:free", ctx=1048576),
    ]
    assert score_text_code(rows[1]) > score_text_code(rows[0])


def test_doc_prefers_large_context():
    rows = [
        _row("liquid/lfm-2.5-1.2b-instruct:free", ctx=32768),
        _row("deepseek/deepseek-v4-flash:free", ctx=1048576),
    ]
    assert score_text_doc(rows[1]) > score_text_doc(rows[0])


def test_vision_requires_image_modality():
    text_only = _row("meta-llama/llama-3.2-3b-instruct:free")
    vision = _row("google/gemma-4-31b-it:free", modalities=["text", "image"])
    assert score_vision(text_only) < 0
    assert score_vision(vision) > 0


def test_build_role_chains_differentiated():
    models = [
        {
            "id": "liquid/lfm-2.5-1.2b-instruct:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"]},
            "context_length": 32768,
        },
        {
            "id": "qwen/qwen3-coder:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"]},
            "context_length": 1048576,
        },
        {
            "id": "deepseek/deepseek-v4-flash:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"]},
            "context_length": 1048576,
        },
        {
            "id": "google/gemma-4-31b-it:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text", "image"]},
            "context_length": 262144,
        },
    ]
    chains = build_role_chains_from_models(models, text_limit=2, vision_limit=1)
    assert chains["text_fast"][0] == "liquid/lfm-2.5-1.2b-instruct:free"
    assert chains["text_code"][0] == "qwen/qwen3-coder:free"
    assert chains["text_doc"][0] == "deepseek/deepseek-v4-flash:free"
    assert chains["vision"] == ["google/gemma-4-31b-it:free"]
    assert chains["text_fast"] != chains["text_code"]
