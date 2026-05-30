"""Admin catalog endpoint and trace page."""

import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENROUTER_API_KEY"] = "or-test-key"
os.environ["ORCHESTRATOR_API_KEY"] = "test-key"
os.environ["ORCHESTRATOR_ADMIN_API_KEY"] = "admin-key"

from gpthub_orchestrator.main import app  # noqa: E402
from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.settings import Settings  # noqa: E402


@pytest.mark.asyncio
async def test_admin_catalog_requires_admin_key():
    settings = Settings(
        openrouter_api_key="or-test-key",
        orchestrator_api_key="test-key",
        orchestrator_admin_api_key="admin-key",
    )
    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"data": []})))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.state.settings = settings
            app.state.http = mock_inner
            app.state.openrouter = OpenRouterClient(mock_inner, settings)
            app.state.catalog_refresh = {"ok": True, "source": "test"}
            app.state.curator = {"status": "disabled"}
            r_user = await ac.get("/v1/admin/catalog", headers={"Authorization": "Bearer test-key"})
            r_admin = await ac.get("/v1/admin/catalog", headers={"Authorization": "Bearer admin-key"})
        assert r_user.status_code == 401
        assert r_admin.status_code == 200
        body = r_admin.json()
        assert body["routing_source"] in ("heuristic", "curator")
        assert "model_health" in body
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_trace_page_served():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/trace")
    assert r.status_code == 200
    assert "Trace decoder" in r.text
