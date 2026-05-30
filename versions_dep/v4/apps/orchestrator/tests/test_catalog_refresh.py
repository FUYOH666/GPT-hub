import json

import httpx
import pytest

from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.openrouter.catalog_pipeline import build_catalog_from_api_models
from gpthub_orchestrator.openrouter.catalog_refresh import (
    fetch_models_async,
    refresh_catalog_from_openrouter,
)


def test_build_catalog_from_api_models():
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
    cat = build_catalog_from_api_models(models, text_limit=2, vision_limit=1)
    assert cat.text_fast[0] == "liquid/lfm-2.5-1.2b-instruct:free"
    assert cat.text_code[0] == "qwen/qwen3-coder:free"
    assert cat.text_doc[0] == "deepseek/deepseek-v4-flash:free"
    assert cat.vision == ["google/gemma-4-31b-it:free"]
    assert cat.text_fast != cat.text_code


@pytest.mark.asyncio
async def test_refresh_catalog_from_openrouter_mock():
    payload = {
        "data": [
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
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json=payload)
        return httpx.Response(404)

    from gpthub_orchestrator.settings import Settings

    settings = Settings(
        openrouter_api_key="or-test",
        openrouter_api_base="https://openrouter.ai/api/v1",
        orchestrator_api_key="test",
        openrouter_probe_on_refresh=False,
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0) as client:
        cat = await refresh_catalog_from_openrouter(
            client,
            api_key="or-test",
            api_base="https://openrouter.ai/api/v1",
            settings=settings,
        )
    active = load_free_models_catalog()
    assert active.text_fast == cat.text_fast
    assert active.text_code == cat.text_code
    assert active.generated_at == cat.generated_at
