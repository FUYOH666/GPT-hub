"""Execution trace serialization for logs and optional response headers."""

from __future__ import annotations

import base64
import json
from typing import Any


def build_trace(
    *,
    classification: dict[str, Any],
    router_suggestion: dict[str, Any],
    model_used: str,
    artifacts: list[dict[str, Any]] | None = None,
    orchestrator_fallback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rs = router_suggestion or {}
    trace: dict[str, Any] = {
        "detected_task": classification.get("task_type"),
        "modalities": classification.get("modalities"),
        "complexity_score": classification.get("complexity_score"),
        "router_suggestion": router_suggestion,
        "model_role": rs.get("model_role"),
        "fallback_aliases": rs.get("fallback_aliases"),
        "model_used": model_used,
        "artifacts": artifacts or [],
        "tools_used": [],
    }
    if orchestrator_fallback is not None:
        trace["orchestrator_fallback"] = orchestrator_fallback
    return trace


def trace_to_header_value(trace: dict[str, Any]) -> str:
    raw = json.dumps(trace, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")
