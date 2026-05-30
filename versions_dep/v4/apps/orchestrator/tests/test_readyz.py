import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENROUTER_API_KEY"] = "or-test-key"
os.environ["ORCHESTRATOR_API_KEY"] = "test-key"

from gpthub_orchestrator.main import app  # noqa: E402
from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.settings import Settings  # noqa: E402


@pytest.mark.asyncio
async def test_readyz_ok_when_openrouter_alive():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": []})
        return httpx.Response(404)

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    settings = Settings(openrouter_api_key="or-test-key", orchestrator_api_key="test-key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        app.state.settings = settings
        app.state.http = mock_inner
        app.state.openrouter = OpenRouterClient(mock_inner, settings)
        r = await ac.get("/readyz")
    await mock_inner.aclose()
    assert r.status_code == 200
    assert r.json()["openrouter"] == "ok"


@pytest.mark.asyncio
async def test_readyz_503_when_openrouter_down():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    settings = Settings(openrouter_api_key="or-test-key", orchestrator_api_key="test-key")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        app.state.settings = settings
        app.state.http = mock_inner
        app.state.openrouter = OpenRouterClient(mock_inner, settings)
        r = await ac.get("/readyz")
    await mock_inner.aclose()
    assert r.status_code == 503
