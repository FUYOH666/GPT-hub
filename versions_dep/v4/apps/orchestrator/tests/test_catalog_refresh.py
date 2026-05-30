import json

import httpx
import pytest

from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.openrouter.catalog_refresh import (
    build_catalog_from_api_models,
    refresh_catalog_from_openrouter,
)


def test_build_catalog_from_api_models():
    models = [
        {
            "id": "google/gemma-3-4b-it:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text"]},
            "context_length": 8192,
        },
        {
            "id": "qwen/qwen3.6-plus:free",
            "pricing": {"prompt": "0", "completion": "0"},
            "architecture": {"input_modalities": ["text", "image"]},
            "context_length": 32000,
        },
    ]
    cat = build_catalog_from_api_models(models, text_limit=2, vision_limit=1)
    assert "google/gemma-3-4b-it:free" in cat.text_fast
    assert cat.vision == ["qwen/qwen3.6-plus:free"]


@pytest.mark.asyncio
async def test_refresh_catalog_from_openrouter_mock():
    payload = {
        "data": [
            {
                "id": "google/gemma-3-4b-it:free",
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {"input_modalities": ["text"]},
            },
            {
                "id": "qwen/qwen3.6-plus:free",
                "pricing": {"prompt": "0", "completion": "0"},
                "architecture": {"input_modalities": ["text", "image"]},
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0) as client:
        cat = await refresh_catalog_from_openrouter(
            client,
            api_key="or-test",
            api_base="https://openrouter.ai/api/v1",
        )
    active = load_free_models_catalog()
    assert active.text_fast == cat.text_fast
    assert active.generated_at == cat.generated_at
