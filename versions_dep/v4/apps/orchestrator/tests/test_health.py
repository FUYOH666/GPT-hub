import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("OPENROUTER_API_KEY", "or-test-key")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-key")

from gpthub_orchestrator.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_healthz():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body.get("backend") == "openrouter"
