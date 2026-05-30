"""Shared routing/trace invariants for pytest and ops_simulator."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from gpthub_orchestrator.classifier import classify_messages
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings

_PACKAGE_SCENARIOS = (
    Path(__file__).resolve().parent.parent / "data" / "ops_scenarios.yaml"
)


class ScenarioExpect(BaseModel):
    task_type: str | None = None
    model_role: str | None = None
    http_status: int | None = None
    fallback_used: bool | None = None
    error_type: str | None = None
    message_contains_ru: bool | None = None
    admin_banned_nonempty: bool | None = None


class RoutingScenario(BaseModel):
    id: str
    critical: bool = True
    live_skip: bool = False
    live_soft: bool = False
    messages: list[dict[str, Any]]
    expect: ScenarioExpect
    code_route_preference: str | None = None


class FaultScenario(BaseModel):
    id: str
    critical: bool = True
    mock_only: bool = True
    messages: list[dict[str, Any]]
    mock: dict[str, Any] = Field(default_factory=dict)
    expect: ScenarioExpect


class OpsScenariosFile(BaseModel):
    version: int = 1
    routing: list[RoutingScenario] = Field(default_factory=list)
    fault: list[FaultScenario] = Field(default_factory=list)


def load_ops_scenarios(path: Path | None = None) -> OpsScenariosFile:
    p = path or _PACKAGE_SCENARIOS
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("ops_scenarios.yaml must be a mapping")
    return OpsScenariosFile.model_validate(raw)


def assert_router_suggestion_invariants(
    *,
    messages: list[dict[str, Any]],
    settings: Settings,
    expect: ScenarioExpect,
) -> dict[str, Any]:
    """Offline classifier + router; returns router_suggestion."""
    classification = classify_messages(messages)
    if expect.task_type is not None and classification.get("task_type") != expect.task_type:
        raise AssertionError(
            f"task_type: got {classification.get('task_type')!r}, want {expect.task_type!r}"
        )
    suggestion = choose_model(classification, settings)
    if expect.model_role is not None and suggestion.get("model_role") != expect.model_role:
        raise AssertionError(
            f"model_role: got {suggestion.get('model_role')!r}, want {expect.model_role!r}"
        )
    chain = list(suggestion.get("fallback_aliases") or [])
    if not chain:
        raise AssertionError("fallback_aliases empty")
    head = str(suggestion.get("model_name") or "")
    if head != chain[0]:
        raise AssertionError(f"model_name {head!r} != chain[0] {chain[0]!r}")
    if head not in chain:
        raise AssertionError(f"model_name {head!r} not in fallback_aliases")
    return suggestion


def assert_trace_invariants(
    *,
    trace: dict[str, Any],
    expect: ScenarioExpect,
    router_suggestion: dict[str, Any] | None = None,
) -> None:
    rs = router_suggestion or trace.get("router_suggestion") or {}
    if expect.task_type is not None:
        got = trace.get("task_type") or trace.get("detected_task")
        if got != expect.task_type:
            raise AssertionError(f"trace task_type: got {got!r}, want {expect.task_type!r}")
    if expect.model_role is not None:
        role = trace.get("model_role") or rs.get("model_role")
        if role != expect.model_role:
            raise AssertionError(f"trace model_role: got {role!r}, want {expect.model_role!r}")
    if expect.fallback_used is not None:
        if bool(trace.get("fallback_used")) != expect.fallback_used:
            raise AssertionError(
                f"fallback_used: got {trace.get('fallback_used')!r}, want {expect.fallback_used!r}"
            )
    chain = list(rs.get("fallback_aliases") or trace.get("fallback_aliases") or [])
    model_used = str(
        trace.get("openrouter_model")
        or trace.get("model_used")
        or trace.get("selected_model")
        or ""
    )
    if model_used and chain and model_used not in chain:
        or_attempts = trace.get("model_attempts") or []
        attempt_models = {str(a.get("model") or a.get("openrouter_model") or "") for a in or_attempts}
        if model_used not in attempt_models and model_used not in chain:
            raise AssertionError(f"model_used {model_used!r} not in chain {chain!r}")
    routing_src = rs.get("routing_source") or trace.get("routing_source")
    if routing_src is not None and routing_src not in ("heuristic", "curator"):
        raise AssertionError(f"invalid routing_source: {routing_src!r}")
