"""Background LLM curator: rank free OpenRouter models into routing manifest."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.openrouter.routing_manifest import (
    RoutingManifest,
    apply_curator_manifest,
    parse_curator_json,
)
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

_CURATOR_SYSTEM = """You are a model routing curator for GPTHub (OpenRouter free tier only).
Given a JSON list of free models (id, name, context_length, modalities), output ONLY valid JSON matching this schema:
{
  "version": 1,
  "roles": {
    "fast_text": ["slug", ...],
    "text_code": ["slug", ...],
    "text_doc": ["slug", ...],
    "vision": ["slug", ...]
  },
  "rationale_short": "one sentence for logs"
}
Rules:
- Use ONLY model ids from the input list (exact slugs).
- Order each role array by preference (best first); 3-6 slugs per role.
- fast_text: low latency chat; text_code: coding; text_doc: long context / summarization; vision: image input.
- No markdown, no prose outside JSON."""


def build_model_digest(models: list[dict[str, Any]], *, limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for m in models:
        mid = str(m.get("id") or "").strip()
        if not mid or ":free" not in mid:
            continue
        arch = m.get("architecture") if isinstance(m.get("architecture"), dict) else {}
        modalities = arch.get("input_modalities") or arch.get("modality") or []
        if isinstance(modalities, str):
            modalities = [modalities]
        rows.append(
            {
                "id": mid,
                "name": str(m.get("name") or mid),
                "context_length": m.get("context_length"),
                "modalities": modalities,
            }
        )
    return rows[: max(1, limit)]


def _extract_json_object(text: str) -> str:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return match.group(0)
    raise ValueError("curator response contains no JSON object")


async def call_curator_llm(
    http: httpx.AsyncClient,
    settings: Settings,
    digest: list[dict[str, Any]],
) -> RoutingManifest:
    if not digest:
        raise ValueError("empty model digest for curator")
    model = settings.openrouter_curator_model.strip()
    if not model:
        raise ValueError("OPENROUTER_CURATOR_MODEL is empty")
    url = f"{settings.openrouter_api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.or_site_url,
        "X-Title": settings.or_app_name,
    }
    user_content = json.dumps({"free_models": digest}, ensure_ascii=False)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _CURATOR_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    timeout = httpx.Timeout(settings.openrouter_curator_timeout)
    resp = await http.post(url, json=body, headers=headers, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("curator LLM returned no choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("curator LLM returned empty content")
    raw_json = _extract_json_object(content)
    manifest = parse_curator_json(raw_json)
    allowed = {row["id"] for row in digest}
    for field_name in ("fast_text", "text_code", "text_doc", "vision"):
        slugs = getattr(manifest.roles, field_name)
        filtered = [s for s in slugs if s in allowed]
        if not filtered:
            raise ValueError(f"curator role {field_name} has no valid slugs from digest")
        setattr(manifest.roles, field_name, filtered)
    return manifest


async def run_curator(
    http: httpx.AsyncClient,
    settings: Settings,
    models: list[dict[str, Any]],
    *,
    base_catalog: FreeModelsCatalog,
) -> RoutingManifest:
    digest = build_model_digest(models, limit=settings.openrouter_curator_digest_limit)
    manifest = await call_curator_llm(http, settings, digest)
    apply_curator_manifest(manifest, base_catalog=base_catalog)
    if manifest.rationale_short:
        logger.info("curator_rationale %s", manifest.rationale_short)
    return manifest
