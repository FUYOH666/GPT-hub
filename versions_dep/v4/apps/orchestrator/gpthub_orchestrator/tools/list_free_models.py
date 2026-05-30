"""List OpenRouter models with zero prompt+completion pricing (curation aid).

Usage (from apps/orchestrator):
  export OPENROUTER_API_KEY=...
  uv run python -m gpthub_orchestrator.tools.list_free_models
  uv run python -m gpthub_orchestrator.tools.list_free_models --vision-only --json
  uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-vision-chain --limit 5
  uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-text-chain --limit 4
  uv run python -m gpthub_orchestrator.tools.list_free_models --write-catalog --output path/to/free_models_catalog.yaml
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import yaml

from gpthub_orchestrator.openrouter.catalog import build_catalog_from_rows

logger = logging.getLogger(__name__)

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

VISION_SUGGEST_EXCLUDE_IDS: frozenset[str] = frozenset({"openrouter/free"})
TEXT_SUGGEST_EXCLUDE_IDS: frozenset[str] = frozenset({"openrouter/free"})

LITELLM_VISION_ALIAS_ORDER: tuple[str, ...] = (
    "gpt-hub-vision",
    "gpt-hub-vision-2",
    "gpt-hub-vision-3",
    "gpt-hub-vision-4",
    "gpt-hub-fallback",
)


def is_excluded_from_vision_suggest(model_id: str) -> bool:
    mid = model_id.strip()
    if mid in VISION_SUGGEST_EXCLUDE_IDS:
        return True
    if mid.startswith("google/lyria-"):
        return True
    return False


def is_excluded_from_text_suggest(model_id: str) -> bool:
    mid = model_id.strip()
    if mid in TEXT_SUGGEST_EXCLUDE_IDS:
        return True
    if mid.startswith("google/lyria-"):
        return True
    return False


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
    text_only: bool = False,
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
        if text_only and "image" in modalities:
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


def vision_model_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    mid = str(row.get("id") or "")
    google = 1 if mid.startswith("google/") else 0
    ctx = row.get("context_length")
    try:
        n = int(ctx) if ctx is not None else 0
    except (TypeError, ValueError):
        n = 0
    return (google, -n, mid)


def text_model_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    """Prefer smaller/faster models first for chat; non-Google before Google."""
    mid = str(row.get("id") or "")
    google = 1 if mid.startswith("google/") else 0
    ctx = row.get("context_length")
    try:
        n = int(ctx) if ctx is not None else 0
    except (TypeError, ValueError):
        n = 0
    return (google, n, mid)


def order_free_vision_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=vision_model_sort_key)


def order_free_text_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = [r for r in rows if not is_excluded_from_text_suggest(str(r.get("id") or ""))]
    return sorted(filtered, key=text_model_sort_key)


def build_litellm_vision_snippet(ordered_ids: list[str]) -> str:
    if not ordered_ids:
        return "# (no models)\n"
    lines: list[str] = ["# --- Legacy LiteLLM snippet (v3); v4 uses free_models_catalog.yaml ---"]
    for alias, mid in zip(LITELLM_VISION_ALIAS_ORDER, ordered_ids):
        lines.append(f"  - model_name: {alias}")
        lines.append("    litellm_params:")
        lines.append(f"      model: openrouter/{mid}")
        lines.append("      api_key: os.environ/OPENROUTER_API_KEY")
        lines.append("")
    return "\n".join(lines) + "\n"


def write_catalog_file(
    *,
    models: list[dict[str, Any]],
    output: Path,
    text_limit: int = 4,
    vision_limit: int = 5,
) -> dict[str, Any]:
    text_rows = order_free_text_rows([simplify(m) for m in filter_free(models, vision_only=False, text_only=True)])
    vision_rows = order_free_vision_rows([simplify(m) for m in filter_free(models, vision_only=True)])
    vision_rows = [r for r in vision_rows if not is_excluded_from_vision_suggest(str(r.get("id") or ""))]
    text_rows = text_rows[: max(1, text_limit)]
    vision_rows = vision_rows[: max(1, vision_limit)]
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    catalog = build_catalog_from_rows(
        text_rows=text_rows,
        vision_rows=vision_rows,
        generated_at=generated_at,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False), encoding="utf-8")
    logger.info("wrote catalog to %s", output)
    return catalog


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="List free (zero-priced) OpenRouter chat models.")
    p.add_argument("--vision-only", action="store_true", help="Only models that accept image input")
    p.add_argument("--json", action="store_true", help="Print JSON array to stdout")
    p.add_argument("--no-auth", action="store_true", help="Call API without Authorization")
    p.add_argument("--suggest-vision-chain", action="store_true")
    p.add_argument("--suggest-text-chain", action="store_true")
    p.add_argument(
        "--write-catalog",
        action="store_true",
        help="Write gpthub_orchestrator/data/free_models_catalog.yaml (or --output)",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path for --write-catalog",
    )
    p.add_argument("--limit", type=int, default=5, metavar="N")
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

    if args.write_catalog:
        default_out = (
            Path(__file__).resolve().parent.parent / "data" / "free_models_catalog.yaml"
        )
        out_path = args.output or default_out
        catalog = write_catalog_file(
            models=models,
            output=out_path,
            text_limit=args.limit,
            vision_limit=args.limit,
        )
        print(yaml.safe_dump(catalog, allow_unicode=True, sort_keys=False))
        return 0

    free = filter_free(models, vision_only=args.vision_only)
    simplified = [simplify(m) for m in free]
    simplified.sort(key=lambda x: (str(x.get("id") or "")))

    if args.suggest_vision_chain:
        vision = filter_free(models, vision_only=True)
        vrows = order_free_vision_rows([simplify(m) for m in vision])
        vrows = [r for r in vrows if not is_excluded_from_vision_suggest(str(r.get("id") or ""))]
        lim = max(1, min(args.limit, 12))
        vrows = vrows[:lim]
        for i, row in enumerate(vrows, start=1):
            print(f"{i}.\t{row.get('id')}\tctx={row.get('context_length')}")
        print()
        ids = [str(r.get("id") or "") for r in vrows if r.get("id")]
        print(build_litellm_vision_snippet(ids))
        return 0

    if args.suggest_text_chain:
        text = filter_free(models, vision_only=False, text_only=True)
        trows = order_free_text_rows([simplify(m) for m in text])
        lim = max(1, min(args.limit, 12))
        trows = trows[:lim]
        print("# Free text-only models (heuristic: non-google first, smaller context for fast)\n")
        for i, row in enumerate(trows, start=1):
            print(f"{i}.\t{row.get('id')}\tctx={row.get('context_length')}")
        return 0

    if args.json:
        print(json.dumps(simplified, ensure_ascii=False, indent=2))
    else:
        for row in simplified:
            print(f"{row.get('id')}\tctx={row.get('context_length')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
