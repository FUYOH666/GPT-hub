"""Tests for async LLM curator (mocked OpenRouter)."""

import json
import os

import httpx
import pytest

os.environ.setdefault("OPENROUTER_API_KEY", "or-test")
os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-key")

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, clear_runtime_catalog
from gpthub_orchestrator.openrouter.curator import build_model_digest, call_curator_llm, run_curator
from gpthub_orchestrator.openrouter.routing_manifest import reset_curator_state, routing_source
from gpthub_orchestrator.settings import Settings


@pytest.fixture(autouse=True)
def _reset():
    reset_curator_state()
    clear_runtime_catalog()
    yield
    reset_curator_state()
    clear_runtime_catalog()


def test_build_model_digest_filters_free():
    models = [
        {"id": "a:free", "name": "A", "context_length": 8192, "architecture": {"input_modalities": ["text"]}},
        {"id": "paid/model", "name": "Paid"},
    ]
    digest = build_model_digest(models, limit=10)
    assert len(digest) == 1
    assert digest[0]["id"] == "a:free"


@pytest.mark.asyncio
async def test_call_curator_llm_mock():
    manifest_json = {
        "version": 1,
        "roles": {
            "fast_text": ["alpha:free"],
            "text_code": ["alpha:free"],
            "text_doc": ["alpha:free"],
            "vision": ["beta:free"],
        },
        "rationale_short": "mock",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "/chat/completions" in request.url.path
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(manifest_json)}}],
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        openrouter_api_key="or-test",
        orchestrator_api_key="test-key",
        openrouter_curator_model="curator:free",
    )
    digest = [{"id": "alpha:free", "name": "A"}, {"id": "beta:free", "name": "B"}]
    try:
        m = await call_curator_llm(client, settings, digest)
        assert m.roles.fast_text == ["alpha:free"]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_run_curator_applies_manifest():
    manifest_json = {
        "version": 3,
        "roles": {
            "fast_text": ["m1:free"],
            "text_code": ["m1:free"],
            "text_doc": ["m1:free"],
            "vision": ["m2:free"],
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(manifest_json)}}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        openrouter_api_key="or-test",
        orchestrator_api_key="test-key",
        openrouter_curator_model="curator:free",
    )
    base = FreeModelsCatalog(
        text_fast=["old:free"],
        text_code=["old:free"],
        text_doc=["old:free"],
        vision=["old:free"],
        fallback=["old:free"],
    )
    models = [
        {"id": "m1:free", "name": "M1"},
        {"id": "m2:free", "name": "M2", "architecture": {"input_modalities": ["text", "image"]}},
    ]
    try:
        m = await run_curator(client, settings, models, base_catalog=base)
        assert m.version == 3
        assert routing_source() == "curator"
    finally:
        await client.aclose()
