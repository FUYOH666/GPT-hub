"""Micro-probe head slugs on catalog refresh."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog
from gpthub_orchestrator.openrouter.key_pool import KeyPool
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

PROBE_SECTIONS: tuple[tuple[str, list[dict[str, Any]]], ...] = (
    (
        "text_fast",
        [{"role": "user", "content": "Привет!"}],
    ),
    (
        "text_code",
        [{"role": "user", "content": "What is 1+1? Reply with the number only."}],
    ),
    (
        "text_doc",
        [{"role": "user", "content": "One sentence summary: team meeting moved to Friday."}],
    ),
    (
        "vision",
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image in one word."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,iVBORw0KGgoAAAANSUh1EUgAAAAEAAAABCAYAAAAfFcSJAAAAD0lEQVQ42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
                        },
                    },
                ],
            }
        ],
    ),
)

_TINY_VISION = PROBE_SECTIONS[3][1]


async def _probe_one(
    http: httpx.AsyncClient,
    settings: Settings,
    *,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str,
) -> tuple[bool, int, float]:
    url = f"{settings.openrouter_api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.or_site_url,
        "X-Title": settings.or_app_name,
    }
    body = {
        "model": model,
        "messages": messages,
        "max_tokens": 16,
        "stream": False,
    }
    t0 = time.monotonic()
    try:
        resp = await http.post(url, json=body, headers=headers, timeout=httpx.Timeout(45.0))
    except httpx.HTTPError as e:
        logger.warning("catalog_probe_http_error model=%s error=%s", model, e)
        return False, 0, (time.monotonic() - t0) * 1000.0
    latency_ms = (time.monotonic() - t0) * 1000.0
    ok = resp.status_code < 400
    return ok, resp.status_code, latency_ms


def demote_slug_in_chain(chain: list[str], slug: str) -> list[str]:
    if slug not in chain or len(chain) < 2:
        return list(chain)
    new_chain = [s for s in chain if s != slug]
    new_chain.append(slug)
    return new_chain


def apply_probe_demotions(
    catalog: FreeModelsCatalog,
    probe_results: list[dict[str, Any]],
) -> FreeModelsCatalog:
    updates: dict[str, list[str]] = {}
    for pr in probe_results:
        if pr.get("ok"):
            continue
        section = str(pr.get("section") or "")
        slug = str(pr.get("slug") or "")
        if section not in ("text_fast", "text_code", "text_doc", "vision") or not slug:
            continue
        chain = list(getattr(catalog, section))
        new_chain = demote_slug_in_chain(chain, slug)
        if new_chain != chain:
            updates[section] = new_chain
    if not updates:
        return catalog
    updated = catalog.model_copy(update=updates)
    if "text_fast" in updates:
        updated = updated.model_copy(update={"fallback": updates["text_fast"][:1]})
    return updated


async def run_catalog_probes(
    http: httpx.AsyncClient,
    settings: Settings,
    catalog: FreeModelsCatalog,
    *,
    key_pool: KeyPool | None = None,
) -> tuple[FreeModelsCatalog, list[dict[str, Any]]]:
    """Probe head slug per section; demote failures to chain tail."""
    if not settings.openrouter_probe_on_refresh:
        return catalog, []
    max_sections = max(1, min(settings.openrouter_probe_max_models, len(PROBE_SECTIONS)))
    results: list[dict[str, Any]] = []
    api_key = settings.openrouter_api_key
    if key_pool is not None:
        try:
            entry, _ = key_pool.acquire()
            api_key = entry.key
        except RuntimeError:
            pass
    if not api_key.strip():
        logger.warning("catalog_probe_skipped no_api_key")
        return catalog, []

    for section, messages in PROBE_SECTIONS[:max_sections]:
        chain = list(getattr(catalog, section))
        if not chain:
            continue
        slug = chain[0]
        ok, status, latency_ms = await _probe_one(
            http, settings, model=slug, messages=messages, api_key=api_key
        )
        results.append(
            {
                "section": section,
                "slug": slug,
                "ok": ok,
                "status_code": status,
                "latency_ms": round(latency_ms, 2),
            }
        )
        logger.info(
            "catalog_probe section=%s slug=%s ok=%s status=%s latency_ms=%.1f",
            section,
            slug,
            ok,
            status,
            latency_ms,
        )
        if settings.openrouter_probe_delay_seconds > 0:
            await asyncio.sleep(settings.openrouter_probe_delay_seconds)

    updated = apply_probe_demotions(catalog, results)
    return updated, results
