import base64
import json
import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENROUTER_API_KEY"] = "or-test-key"
os.environ["ORCHESTRATOR_API_KEY"] = "test-key"
os.environ["AUTO_ROUTE_MODEL"] = "true"
os.environ["ORCHESTRATOR_OPENROUTER_FALLBACK"] = "true"

from gpthub_orchestrator.main import app  # noqa: E402
from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.settings import Settings  # noqa: E402


@pytest.mark.asyncio
async def test_non_stream_retries_on_429_then_200():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/chat/completions" in request.url.path
        body = json.loads(request.content.decode())
        model = str(body.get("model"))
        calls.append(model)
        if model == "google/gemma-3-4b-it:free":
            return httpx.Response(429, json={"error": "rate_limited"})
        return httpx.Response(
            200,
            json={
                "id": "1",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}
                ],
            },
        )

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    settings = Settings(
        openrouter_api_key="or-test-key",
        orchestrator_api_key="test-key",
        auto_route_model=True,
        orchestrator_openrouter_fallback=True,
        orchestrator_fallback_max_attempts=8,
    )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            app.state.settings = settings
            app.state.http = mock_inner
            app.state.openrouter = OpenRouterClient(mock_inner, settings)
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={
                    "model": "ignored-when-auto",
                    "messages": [
                        {"role": "user", "content": "What is a Python list in one sentence?"}
                    ],
                },
            )
        assert r.status_code == 200
        assert calls[0] == "google/gemma-3-4b-it:free"
        assert len(calls) >= 2
        trace_hdr = r.headers.get("X-GPTHub-Trace")
        assert trace_hdr
        trace = json.loads(base64.b64decode(trace_hdr).decode("utf-8"))
        assert trace["fallback_used"] is True
        assert trace.get("openrouter_model")
        assert trace.get("model_attempts")
    finally:
        await mock_inner.aclose()
