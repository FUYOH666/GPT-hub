import json
import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("LITELLM_BASE_URL", "http://litellm.test:4000")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-key")

from gpthub_orchestrator.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_v1_models_proxies_to_litellm(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/v1/models"):
            return httpx.Response(
                200,
                json={"object": "list", "data": [{"id": "gpt-hub-strong", "object": "model"}]},
            )
        return httpx.Response(404)

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.state.settings = __import__(
                "gpthub_orchestrator.settings",
                fromlist=["Settings"],
            ).Settings(
                litellm_base_url="http://litellm.test:4000",
                orchestrator_api_key="test-key",
            )
            app.state.http = mock_inner
            r = await ac.get("/v1/models", headers={"Authorization": "Bearer test-key"})
        assert r.status_code == 200
        body = r.json()
        assert body["data"][0]["id"] == "gpt-hub-strong"
    finally:
        await mock_inner.aclose()
