"""Deterministic role-specific scoring for OpenRouter free model pools."""

from __future__ import annotations

import re
from typing import Any

from gpthub_orchestrator.tools.list_free_models import (
    filter_free,
    is_excluded_from_text_suggest,
    is_excluded_from_vision_suggest,
    simplify,
)

DEFAULT_DENYLIST: frozenset[str] = frozenset({"openrouter/free", "openrouter/owl-alpha"})

_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b", re.I)


def _modalities(row: dict[str, Any]) -> list[str]:
    mods = row.get("input_modalities") or []
    return [str(m).lower() for m in mods]


def _has_image(row: dict[str, Any]) -> bool:
    return "image" in _modalities(row)


def _context(row: dict[str, Any]) -> int:
    try:
        return int(row.get("context_length") or 0)
    except (TypeError, ValueError):
        return 0


def _slug(row: dict[str, Any]) -> str:
    return str(row.get("id") or "").strip()


def _size_b_hint(slug: str) -> float | None:
    m = _SIZE_RE.search(slug.lower())
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def is_denied(slug: str, extra: frozenset[str] | None = None) -> bool:
    mid = slug.strip().lower()
    if not mid:
        return True
    if mid in DEFAULT_DENYLIST:
        return True
    if extra and mid in extra:
        return True
    if mid.startswith("google/lyria-"):
        return True
    if "dolphin" in mid and "venice" in mid:
        return True
    return False


def score_fast_text(row: dict[str, Any], *, extra_denylist: frozenset[str] | None = None) -> float:
    slug = _slug(row)
    if is_denied(slug, extra_denylist) or _has_image(row):
        return -1e9
    score = 100.0
    size = _size_b_hint(slug)
    if size is not None:
        score += max(0.0, 40.0 - size * 8.0)
    if "nano" in slug or "1.2b" in slug or "3b" in slug:
        score += 25.0
    if "405b" in slug or "120b" in slug or "70b" in slug:
        score -= 30.0
    ctx = _context(row)
    if ctx > 200_000:
        score -= 10.0
    if slug.startswith("liquid/"):
        score += 15.0
    return score


def score_text_code(row: dict[str, Any], *, extra_denylist: frozenset[str] | None = None) -> float:
    slug = _slug(row)
    if is_denied(slug, extra_denylist) or _has_image(row):
        return -1e9
    score = 50.0
    low = slug.lower()
    if "coder" in low or "code" in low:
        score += 80.0
    if "poolside" in low or "laguna" in low:
        score += 40.0
    if "qwen" in low:
        score += 25.0
    if "nemotron" in low:
        score += 15.0
    ctx = _context(row)
    score += min(ctx / 50_000.0, 20.0)
    if "405b" in slug:
        score += 10.0
    if "1.2b" in slug and "coder" not in low:
        score -= 20.0
    return score


def score_text_doc(row: dict[str, Any], *, extra_denylist: frozenset[str] | None = None) -> float:
    slug = _slug(row)
    if is_denied(slug, extra_denylist) or _has_image(row):
        return -1e9
    score = 40.0
    ctx = _context(row)
    score += min(ctx / 25_000.0, 60.0)
    low = slug.lower()
    if "flash" in low or "super" in low:
        score += 25.0
    if "deepseek" in low:
        score += 20.0
    if "nemotron-3-super" in low:
        score += 30.0
    if "1.2b" in slug:
        score -= 25.0
    return score


def score_vision(row: dict[str, Any], *, extra_denylist: frozenset[str] | None = None) -> float:
    slug = _slug(row)
    if is_denied(slug, extra_denylist) or not _has_image(row):
        return -1e9
    score = 60.0
    low = slug.lower()
    if "gemma-4" in low:
        score += 40.0
    if "gemma-3" in low:
        score += 20.0
    if "kimi" in low:
        score += 25.0
    if "nemotron" in low and "vl" in low:
        score += 20.0
    if "qwen" in low:
        score += 15.0
    ctx = _context(row)
    score += min(ctx / 100_000.0, 15.0)
    return score


def rank_rows(
    rows: list[dict[str, Any]],
    scorer: Any,
    *,
    limit: int,
    extra_denylist: frozenset[str] | None = None,
) -> list[str]:
    scored: list[tuple[float, str]] = []
    for row in rows:
        slug = _slug(row)
        if not slug:
            continue
        s = float(scorer(row, extra_denylist=extra_denylist))
        if s <= -1e8:
            continue
        scored.append((s, slug))
    scored.sort(key=lambda x: (-x[0], x[1]))
    seen: set[str] = set()
    out: list[str] = []
    for _, slug in scored:
        if slug in seen:
            continue
        seen.add(slug)
        out.append(slug)
        if len(out) >= max(1, limit):
            break
    return out


def build_role_chains_from_models(
    models: list[dict[str, Any]],
    *,
    text_limit: int = 4,
    vision_limit: int = 5,
    extra_denylist: frozenset[str] | None = None,
) -> dict[str, list[str]]:
    """Score free models into differentiated catalog sections."""
    text_rows = [
        simplify(m)
        for m in filter_free(models, vision_only=False, text_only=True)
        if not is_excluded_from_text_suggest(str(m.get("id") or ""))
    ]
    vision_rows = [
        simplify(m)
        for m in filter_free(models, vision_only=True)
        if not is_excluded_from_vision_suggest(str(m.get("id") or ""))
    ]
    text_fast = rank_rows(text_rows, score_fast_text, limit=text_limit, extra_denylist=extra_denylist)
    text_code = rank_rows(text_rows, score_text_code, limit=text_limit, extra_denylist=extra_denylist)
    text_doc = rank_rows(text_rows, score_text_doc, limit=text_limit, extra_denylist=extra_denylist)
    vision = rank_rows(vision_rows, score_vision, limit=vision_limit, extra_denylist=extra_denylist)
    if not text_fast or not text_code or not text_doc:
        raise ValueError("no scored text models for catalog")
    if not vision:
        raise ValueError("no scored vision models for catalog")
    return {
        "text_fast": text_fast,
        "text_code": text_code,
        "text_doc": text_doc,
        "vision": vision,
        "fallback": text_fast[:1],
    }
