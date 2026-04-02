"""Normalize BGE-M3 hybrid /v1/embeddings to OpenAI shape (field `embedding`).

Open WebUI RAG expects each item in data[] to have `embedding`: float[].
Hybrid BGE often returns `dense_embedding` instead.
"""

from __future__ import annotations

import json
import logging
import os

import httpx
from fastapi import FastAPI, Request, Response

logger = logging.getLogger("gpthub_embedding_shim")

UPSTREAM = os.environ.get("BGE_EMBEDDING_UPSTREAM", "http://host.docker.internal:9001").rstrip("/")

app = FastAPI(title="GPTHub embedding OpenAI shim", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "gpthub-embedding-shim"}


def _normalize_payload(data: dict) -> dict:
    items = data.get("data")
    if not isinstance(items, list):
        return data
    for item in items:
        if not isinstance(item, dict):
            continue
        if "embedding" not in item and "dense_embedding" in item:
            item["embedding"] = item["dense_embedding"]
    return data


@app.post("/v1/embeddings")
async def embeddings(request: Request) -> Response:
    body = await request.body()
    auth = request.headers.get("authorization", "")
    url = f"{UPSTREAM}/v1/embeddings"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            url,
            content=body,
            headers={
                "Content-Type": request.headers.get("content-type", "application/json"),
                "Authorization": auth,
            },
        )
    ct = r.headers.get("content-type", "application/json")
    if r.status_code >= 400 or "json" not in ct.lower():
        logger.warning("upstream_embeddings status=%s", r.status_code)
        return Response(content=r.content, status_code=r.status_code, media_type=ct)
    try:
        payload = r.json()
    except Exception:
        return Response(content=r.content, status_code=r.status_code, media_type=ct)
    if isinstance(payload, dict):
        payload = _normalize_payload(payload)
    raw = json.dumps(payload).encode("utf-8")
    return Response(content=raw, status_code=r.status_code, media_type="application/json")
