"""List OpenRouter models with zero prompt+completion pricing (curation aid).

Usage (from apps/orchestrator):
  export OPENROUTER_API_KEY=...
  uv run python -m gpthub_orchestrator.tools.list_free_models
  uv run python -m gpthub_orchestrator.tools.list_free_models --vision-only --json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"


def _parse_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def is_effectively_free(pricing: dict[str, Any] | None) -> bool:
    if not pricing:
        return False
    p = _parse_price(pricing.get("prompt"))
    c = _parse_price(pricing.get("completion"))
    if p is None or c is None:
        return False
    return p == 0.0 and c == 0.0


def fetch_models(api_key: str | None, timeout: float = 60.0) -> list[dict[str, Any]]:
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    with httpx.Client(timeout=timeout) as client:
        r = client.get(OPENROUTER_MODELS_URL, headers=headers)
        r.raise_for_status()
        data = r.json()
    raw = data.get("data")
    if not isinstance(raw, list):
        raise ValueError("Unexpected OpenRouter response: missing data array")
    return raw


def filter_free(
    models: list[dict[str, Any]],
    *,
    vision_only: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in models:
        if not isinstance(m, dict):
            continue
        pricing = m.get("pricing")
        if not isinstance(pricing, dict) or not is_effectively_free(pricing):
            continue
        arch = m.get("architecture")
        modalities: list[str] = []
        if isinstance(arch, dict):
            im = arch.get("input_modalities")
            if isinstance(im, list):
                modalities = [str(x) for x in im]
        if vision_only and "image" not in modalities:
            continue
        out.append(m)
    return out


def simplify(m: dict[str, Any]) -> dict[str, Any]:
    arch = m.get("architecture") if isinstance(m.get("architecture"), dict) else {}
    im = arch.get("input_modalities")
    modalities = list(im) if isinstance(im, list) else []
    return {
        "id": m.get("id"),
        "name": m.get("name"),
        "context_length": m.get("context_length"),
        "input_modalities": modalities,
    }


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="List free (zero-priced) OpenRouter chat models.")
    p.add_argument(
        "--vision-only",
        action="store_true",
        help="Only models that accept image input",
    )
    p.add_argument("--json", action="store_true", help="Print JSON array to stdout")
    p.add_argument(
        "--no-auth",
        action="store_true",
        help="Call API without Authorization (public list may differ)",
    )
    args = p.parse_args(argv)

    api_key = None if args.no_auth else os.environ.get("OPENROUTER_API_KEY")
    if not api_key and not args.no_auth:
        logger.error("OPENROUTER_API_KEY is not set (use --no-auth for unauthenticated request)")
        return 1

    try:
        models = fetch_models(api_key)
    except httpx.HTTPError as e:
        logger.error("HTTP error: %s", e)
        return 1
    except ValueError as e:
        logger.error("%s", e)
        return 1

    free = filter_free(models, vision_only=args.vision_only)
    simplified = [simplify(m) for m in free]
    simplified.sort(key=lambda x: (str(x.get("id") or "")))

    if args.json:
        print(json.dumps(simplified, ensure_ascii=False, indent=2))
    else:
        for row in simplified:
            mid = row.get("id")
            ctx = row.get("context_length")
            mods = ",".join(row.get("input_modalities") or [])
            name = row.get("name") or ""
            print(f"{mid}\tctx={ctx}\t[{mods}]\t{name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
