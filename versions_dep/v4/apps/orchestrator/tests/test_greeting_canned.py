"""Canned greeting short-circuit: no OpenRouter call, trace canned_response."""

from __future__ import annotations

import base64
import json
import os

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

os.environ["OPENROUTER_API_KEY"] = "or-test-key"
os.environ["ORCHESTRATOR_API_KEY"] = "test-key"

from gpthub_orchestrator.main import app  # noqa: E402
from gpthub_orchestrator.response_preamble_strip import assistant_content_has_leak_substrings  # noqa: E402
from tests._helpers import wire_app_state  # noqa: E402


@pytest.mark.asyncio
async def test_greeting_canned_skips_openrouter_non_stream():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(500, json={"error": "upstream should not be called"})

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            wire_app_state(
                app,
                mock_inner,
                greeting_canned_response_enabled=True,
                greeting_canned_message="Hi canned",
            )
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={"model": "gpt-hub", "messages": [{"role": "user", "content": "привет"}]},
            )
        assert r.status_code == 200
        assert calls == []
        data = r.json()
        assert data["choices"][0]["message"]["content"] == "Hi canned"
        trace = json.loads(base64.b64decode(r.headers["X-GPTHub-Trace"]).decode("utf-8"))
        assert trace.get("canned_response") is True
        assert assistant_content_has_leak_substrings(data["choices"][0]["message"]["content"]) == []
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_greeting_canned_disabled_calls_openrouter():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        body = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "id": "1",
                "object": "chat.completion",
                "created": 0,
                "model": body.get("model"),
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "from-upstream"}, "finish_reason": "stop"}
                ],
            },
        )

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            wire_app_state(app, mock_inner, greeting_canned_response_enabled=False)
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={"model": "gpt-hub", "messages": [{"role": "user", "content": "привет"}]},
            )
        assert r.status_code == 200
        assert len(calls) == 1
        assert "/chat/completions" in calls[0]
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_greeting_canned_stream_sse():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(500)

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            wire_app_state(
                app,
                mock_inner,
                greeting_canned_response_enabled=True,
                greeting_canned_message="stream-hi",
            )
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={
                    "model": "gpt-hub",
                    "messages": [{"role": "user", "content": "Hello"}],
                    "stream": True,
                },
            )
        assert r.status_code == 200
        assert calls == []
        assert "stream-hi" in r.text
        trace = json.loads(base64.b64decode(r.headers["X-GPTHub-Trace"]).decode("utf-8"))
        assert trace.get("canned_response") is True
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_greeting_plus_date_question_calls_openrouter_not_canned():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        body = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "id": "1",
                "object": "chat.completion",
                "created": 0,
                "model": body.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "from-upstream"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            wire_app_state(
                app,
                mock_inner,
                greeting_canned_response_enabled=True,
                greeting_canned_message="Hi canned",
            )
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={
                    "model": "gpt-hub",
                    "messages": [{"role": "user", "content": "Привет, какой сегодня день?"}],
                },
            )
        assert r.status_code == 200
        assert len(calls) == 1
        trace = json.loads(base64.b64decode(r.headers["X-GPTHub-Trace"]).decode("utf-8"))
        assert trace.get("canned_response") is not True
    finally:
        await mock_inner.aclose()


@pytest.mark.asyncio
async def test_casual_kak_dela_canned_skips_openrouter():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(500)

    mock_inner = httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=30.0)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            wire_app_state(
                app,
                mock_inner,
                greeting_canned_response_enabled=True,
                greeting_canned_message="Отлично, готов помочь!",
            )
            r = await ac.post(
                "/v1/chat/completions",
                headers={"Authorization": "Bearer test-key"},
                json={"model": "gpt-hub", "messages": [{"role": "user", "content": "как дела?"}]},
            )
        assert r.status_code == 200
        assert calls == []
        assert r.json()["choices"][0]["message"]["content"] == "Отлично, готов помочь!"
    finally:
        await mock_inner.aclose()
