import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("OPENROUTER_API_KEY", "or-test-key")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-key")

from gpthub_orchestrator.main import app  # noqa: E402
from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.settings import Settings  # noqa: E402


@pytest.mark.asyncio
async def test_v1_models_catalog_all_lists_catalog_slugs():
    settings = Settings(
        openrouter_api_key="or-test-key",
        orchestrator_api_key="test-key",
        orchestrator_models_catalog="all",
    )
    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.state.settings = settings
            app.state.http = mock_inner
            app.state.openrouter = OpenRouterClient(mock_inner, settings)
            r = await ac.get("/v1/models", headers={"Authorization": "Bearer test-key"})
        assert r.status_code == 200
        body = r.json()
        ids = {m["id"] for m in body["data"]}
        assert "google/gemma-3-4b-it:free" in ids
        assert "qwen/qwen3.6-plus:free" in ids
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_v1_models_single_public_facade():
    settings = Settings(
        openrouter_api_key="or-test-key",
        orchestrator_api_key="test-key",
        orchestrator_models_catalog="single_public",
        orchestrator_public_model_id="gpt-hub",
    )
    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(404)), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.state.settings = settings
            app.state.http = mock_inner
            app.state.openrouter = OpenRouterClient(mock_inner, settings)
            r = await ac.get("/v1/models", headers={"Authorization": "Bearer test-key"})
        assert r.status_code == 200
        body = r.json()
        assert len(body["data"]) == 1
        assert body["data"][0]["id"] == "gpt-hub"
    finally:
        await mock_inner.aclose()
