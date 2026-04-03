"""List OpenRouter models with zero prompt+completion pricing (curation aid).

Usage (from apps/orchestrator):
  export OPENROUTER_API_KEY=...
  uv run python -m gpthub_orchestrator.tools.list_free_models
  uv run python -m gpthub_orchestrator.tools.list_free_models --vision-only --json
  uv run python -m gpthub_orchestrator.tools.list_free_models --suggest-vision-chain --limit 5

Эвристика --suggest-vision-chain: не-Google раньше (меньше коррелированных 429), крупнее context; из списка выкидываются
`openrouter/free` (нестабильно за LiteLLM proxy) и `google/lyria-*` (не целевой vision-chat).
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

# В явных slug'ах для LiteLLM не используем (502 и нестабильность в связке с proxy) — см. v2_c2/README.md.
VISION_SUGGEST_EXCLUDE_IDS: frozenset[str] = frozenset({"openrouter/free"})


def is_excluded_from_vision_suggest(model_id: str) -> bool:
    """Исключения для --suggest-vision-chain (чат+картинка; не общий каталог API)."""
    mid = model_id.strip()
    if mid in VISION_SUGGEST_EXCLUDE_IDS:
        return True
    if mid.startswith("google/lyria-"):
        return True
    return False

# Имена алиасов в versions_dep/v2_c2/litellm/config.yaml (последний — общий OR fallback).
LITELLM_VISION_ALIAS_ORDER: tuple[str, ...] = (
    "gpt-hub-vision",
    "gpt-hub-vision-2",
    "gpt-hub-vision-3",
    "gpt-hub-vision-4",
    "gpt-hub-fallback",
)


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


def vision_model_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    """Стабильный порядок для vision free: сначала не-Google (ниже коррелированный 429), затем больший контекст."""
    mid = str(row.get("id") or "")
    google = 1 if mid.startswith("google/") else 0
    ctx = row.get("context_length")
    try:
        n = int(ctx) if ctx is not None else 0
    except (TypeError, ValueError):
        n = 0
    return (google, -n, mid)


def order_free_vision_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=vision_model_sort_key)


def build_litellm_vision_snippet(ordered_ids: list[str]) -> str:
    """Фрагмент YAML для model_list + подсказка по fallbacks (ручной merge в config.yaml)."""
    if not ordered_ids:
        return "# (no models)\n"
    lines: list[str] = [
        "# --- Paste into model_list (adjust if alias count differs) ---",
    ]
    for alias, mid in zip(LITELLM_VISION_ALIAS_ORDER, ordered_ids):
        lines.append(f"  - model_name: {alias}")
        lines.append("    litellm_params:")
        lines.append(f"      model: openrouter/{mid}")
        lines.append("      api_key: os.environ/OPENROUTER_API_KEY")
        lines.append("")
    if len(ordered_ids) > len(LITELLM_VISION_ALIAS_ORDER):
        lines.append("# Additional free vision ids (extend aliases / fallbacks manually):")
        for mid in ordered_ids[len(LITELLM_VISION_ALIAS_ORDER) :]:
            lines.append(f"#   - openrouter/{mid}")
        lines.append("")
    n = min(len(ordered_ids), len(LITELLM_VISION_ALIAS_ORDER))
    names = list(LITELLM_VISION_ALIAS_ORDER[:n])
    if len(names) >= 2:
        tail = names[1:]
        lines.append("# litellm_settings.fallbacks (vision: only multimodal aliases; no local text-only model):")
        lines.append(f"#   - {names[0]}: {tail}")
        for i in range(1, len(names) - 1):
            lines.append(f"#   - {names[i]}: {names[i + 1 :]}")
        lines.append(f"#   - {names[-1]}: []  # or omit further fallback")
    return "\n".join(lines) + "\n"


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
    p.add_argument(
        "--suggest-vision-chain",
        action="store_true",
        help="Fetch API, rank free+image models, print suggested slug order + LiteLLM YAML snippet",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=5,
        metavar="N",
        help="With --suggest-vision-chain: max models in the chain (default: 5)",
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

    if args.suggest_vision_chain:
        vision = filter_free(models, vision_only=True)
        vrows = order_free_vision_rows([simplify(m) for m in vision])
        vrows = [r for r in vrows if not is_excluded_from_vision_suggest(str(r.get("id") or ""))]
        lim = max(1, min(args.limit, 12))
        vrows = vrows[:lim]
        ids = [str(r.get("id") or "") for r in vrows if r.get("id")]
        print("# Free + image-capable models (heuristic: non-google first, then larger context)\n")
        for i, row in enumerate(vrows, start=1):
            mid = row.get("id")
            ctx = row.get("context_length")
            mods = ",".join(row.get("input_modalities") or [])
            name = row.get("name") or ""
            print(f"{i}.\t{mid}\tctx={ctx}\t[{mods}]\t{name}")
        print()
        print(build_litellm_vision_snippet(ids))
        print(
            "# Verify slugs in OpenRouter UI; merge into versions_dep/v2_c2/litellm/config.yaml after review.",
        )
        return 0

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
