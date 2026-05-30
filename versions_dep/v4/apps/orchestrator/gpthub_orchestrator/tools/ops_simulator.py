"""Operational simulator: routing invariants + mock/live E2E with JSON/MD report."""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import yaml
from httpx import ASGITransport, AsyncClient

from gpthub_orchestrator.main import app
from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.openrouter.client import OpenRouterClient
from gpthub_orchestrator.ops.routing_invariants import (
    FaultScenario,
    OpsScenariosFile,
    RoutingScenario,
    assert_router_suggestion_invariants,
    assert_trace_invariants,
    load_ops_scenarios,
)
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger("ops_simulator")


@dataclass
class ScenarioResult:
    scenario_id: str
    kind: str
    mode: str
    passed: bool
    critical: bool
    latency_ms: float | None = None
    error: str | None = None
    trace: dict[str, Any] | None = None
    http_status: int | None = None
    details: dict[str, Any] = field(default_factory=dict)


def _decode_trace_header(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        return json.loads(base64.b64decode(value).decode("utf-8"))
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"invalid X-GPTHub-Trace: {e}") from e


def _settings_for_scenario(scenario_code_pref: str | None) -> Settings:
    kwargs: dict[str, Any] = {
        "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY", "or-test-key"),
        "orchestrator_api_key": os.environ.get("ORCHESTRATOR_API_KEY", "test-key"),
        "orchestrator_admin_api_key": os.environ.get(
            "ORCHESTRATOR_ADMIN_API_KEY",
            os.environ.get("ORCHESTRATOR_API_KEY", "test-key"),
        ),
        "openrouter_refresh_catalog_on_startup": False,
        "auto_route_model": True,
        "orchestrator_openrouter_fallback": True,
    }
    if scenario_code_pref:
        kwargs["code_route_preference"] = scenario_code_pref
    return Settings(**kwargs)


class MockOpenRouterFactory:
    """Build httpx MockTransport handlers from scenario mock config."""

    def __init__(self, strategy: str, *, status: int = 429, repeat: int = 3) -> None:
        self._strategy = strategy
        self._status = status
        self._repeat = repeat
        self._chain: list[str] = []
        self._call_counts: dict[str, int] = {}
        self._request_count = 0

    def set_chain(self, chain: list[str]) -> None:
        self._chain = list(chain)

    def handler(self, request: httpx.Request) -> httpx.Response:
        if "/models" in request.url.path:
            return httpx.Response(200, json={"data": []})
        if "/chat/completions" not in request.url.path:
            return httpx.Response(404, json={"error": "not found"})

        body = json.loads(request.content.decode())
        model = str(body.get("model") or "")
        self._call_counts[model] = self._call_counts.get(model, 0) + 1
        self._request_count += 1

        if self._strategy == "fail_all_models":
            return httpx.Response(self._status, json={"error": "rate_limited"})

        if self._strategy == "fail_first_chain_model":
            first = self._chain[0] if self._chain else model
            if model == first:
                return httpx.Response(self._status, json={"error": "rate_limited"})
            return self._ok_response(model)

        if self._strategy == "fail_same_model_repeated":
            first = self._chain[0] if self._chain else model
            if model == first:
                return httpx.Response(self._status, json={"error": "rate_limited"})
            return self._ok_response(model)

        return self._ok_response(model)

    @staticmethod
    def _ok_response(model: str) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "sim",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
            },
        )


async def _setup_mock_app(
    settings: Settings,
    factory: MockOpenRouterFactory,
    messages: list[dict[str, Any]],
) -> AsyncClient:
    classification_chain = None
    from gpthub_orchestrator.classifier import classify_messages
    from gpthub_orchestrator.router import choose_model

    rs = choose_model(classify_messages(messages), settings)
    factory.set_chain(list(rs.get("fallback_aliases") or []))

    transport = httpx.MockTransport(factory.handler)
    mock_inner = httpx.AsyncClient(transport=transport, timeout=30.0)
    app.state.settings = settings
    app.state.http = mock_inner
    app.state.openrouter = OpenRouterClient(mock_inner, settings)
    app.state.catalog_refresh = {"ok": True, "source": "mock", "error": None}
    app.state.curator = {"status": "disabled"}
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _post_chat(
    ac: AsyncClient,
    *,
    settings: Settings,
    messages: list[dict[str, Any]],
    stream: bool = False,
) -> tuple[int, dict[str, Any], dict[str, Any] | None, dict[str, str]]:
    t0 = time.perf_counter()
    r = await ac.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.orchestrator_api_key}"},
        json={"model": "gpt-hub", "messages": messages, "stream": stream},
    )
    latency = (time.perf_counter() - t0) * 1000.0
    trace = _decode_trace_header(r.headers.get("X-GPTHub-Trace"))
    try:
        body = r.json()
    except json.JSONDecodeError:
        body = {"raw": r.text[:500]}
    body["_latency_ms"] = round(latency, 2)
    return r.status_code, body, trace, dict(r.headers)


async def _get_admin(ac: AsyncClient, settings: Settings) -> dict[str, Any]:
    r = await ac.get(
        "/v1/admin/catalog",
        headers={"Authorization": f"Bearer {settings.orchestrator_admin_api_key}"},
    )
    r.raise_for_status()
    return r.json()


async def run_routing_offline(scenario: RoutingScenario) -> ScenarioResult:
    t0 = time.perf_counter()
    try:
        pref = scenario.code_route_preference
        settings = _settings_for_scenario(pref)
        suggestion = assert_router_suggestion_invariants(
            messages=scenario.messages,
            settings=settings,
            expect=scenario.expect,
        )
        ms = (time.perf_counter() - t0) * 1000.0
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="routing",
            mode="offline",
            passed=True,
            critical=scenario.critical,
            latency_ms=ms,
            details={"model_name": suggestion.get("model_name"), "chain_len": len(suggestion.get("fallback_aliases") or [])},
        )
    except Exception as e:
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="routing",
            mode="offline",
            passed=False,
            critical=scenario.critical,
            error=str(e),
        )


async def run_routing_mock_e2e(scenario: RoutingScenario) -> ScenarioResult:
    try:
        settings = _settings_for_scenario(scenario.code_route_preference)
        factory = MockOpenRouterFactory("fail_none")
        async with await _setup_mock_app(settings, factory, scenario.messages) as ac:
            status, body, trace, _ = await _post_chat(ac, settings=settings, messages=scenario.messages)
        if status != 200:
            return ScenarioResult(
                scenario_id=scenario.id,
                kind="routing",
                mode="mock_e2e",
                passed=False,
                critical=scenario.critical,
                http_status=status,
                error=f"HTTP {status}: {body}",
            )
        assert trace is not None
        assert_trace_invariants(trace=trace, expect=scenario.expect)
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="routing",
            mode="mock_e2e",
            passed=True,
            critical=scenario.critical,
            http_status=status,
            latency_ms=body.get("_latency_ms"),
            trace=trace,
            details={"model_used": trace.get("model_used"), "fallback_used": trace.get("fallback_used")},
        )
    except Exception as e:
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="routing",
            mode="mock_e2e",
            passed=False,
            critical=scenario.critical,
            error=str(e),
        )


async def run_fault_mock(scenario: FaultScenario) -> ScenarioResult:
    try:
        settings = _settings_for_scenario(None)
        mock_cfg = scenario.mock
        strategy = str(mock_cfg.get("strategy") or "fail_all_models")
        status = int(mock_cfg.get("status") or 429)
        repeat = int(mock_cfg.get("repeat") or 3)
        factory = MockOpenRouterFactory(strategy, status=status, repeat=repeat)

        if strategy == "fail_same_model_repeated" and scenario.expect.admin_banned_nonempty:
            async with await _setup_mock_app(settings, factory, scenario.messages) as ac:
                for _ in range(repeat):
                    st, _, _, _ = await _post_chat(ac, settings=settings, messages=scenario.messages)
                    if st != 200:
                        pass
                admin = await _get_admin(ac, settings)
            banned = admin.get("model_health", {}).get("banned") or []
            if not banned:
                return ScenarioResult(
                    scenario_id=scenario.id,
                    kind="fault",
                    mode="mock_e2e",
                    passed=False,
                    critical=scenario.critical,
                    error="expected banned slugs in admin model_health",
                    details={"admin": admin},
                )
            return ScenarioResult(
                scenario_id=scenario.id,
                kind="fault",
                mode="mock_e2e",
                passed=True,
                critical=scenario.critical,
                details={"banned_count": len(banned)},
            )

        async with await _setup_mock_app(settings, factory, scenario.messages) as ac:
            http_status, body, trace, _ = await _post_chat(
                ac, settings=settings, messages=scenario.messages
            )

        exp = scenario.expect
        if exp.http_status is not None and http_status != exp.http_status:
            return ScenarioResult(
                scenario_id=scenario.id,
                kind="fault",
                mode="mock_e2e",
                passed=False,
                critical=scenario.critical,
                http_status=http_status,
                error=f"HTTP want {exp.http_status} got {http_status}",
                trace=trace,
            )

        if exp.error_type == "openrouter_exhausted":
            err = body.get("error") or {}
            if err.get("type") != "openrouter_exhausted":
                return ScenarioResult(
                    scenario_id=scenario.id,
                    kind="fault",
                    mode="mock_e2e",
                    passed=False,
                    critical=scenario.critical,
                    error=f"error.type={err.get('type')!r}",
                )
            if exp.message_contains_ru and not err.get("message_ru"):
                return ScenarioResult(
                    scenario_id=scenario.id,
                    kind="fault",
                    mode="mock_e2e",
                    passed=False,
                    critical=scenario.critical,
                    error="missing message_ru",
                )

        if trace and exp.fallback_used is not None:
            assert_trace_invariants(trace=trace, expect=exp)

        return ScenarioResult(
            scenario_id=scenario.id,
            kind="fault",
            mode="mock_e2e",
            passed=True,
            critical=scenario.critical,
            http_status=http_status,
            latency_ms=body.get("_latency_ms"),
            trace=trace,
            details={"fallback_used": (trace or {}).get("fallback_used")},
        )
    except Exception as e:
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="fault",
            mode="mock_e2e",
            passed=False,
            critical=scenario.critical,
            error=str(e),
        )


async def run_routing_live(
    scenario: RoutingScenario,
    *,
    base_url: str,
    api_key: str,
    delay_s: float,
) -> ScenarioResult:
    try:
        async with httpx.AsyncClient(base_url=base_url.rstrip("/"), timeout=120.0) as client:
            t0 = time.perf_counter()
            r = await client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "gpt-hub", "messages": scenario.messages, "stream": False},
            )
            ms = (time.perf_counter() - t0) * 1000.0
            trace = _decode_trace_header(r.headers.get("X-GPTHub-Trace"))
            body: dict[str, Any] = {}
            try:
                body = r.json()
            except json.JSONDecodeError:
                body = {"raw": r.text[:500]}
            if r.status_code != 200:
                if trace:
                    try:
                        assert_trace_invariants(trace=trace, expect=scenario.expect)
                        await asyncio.sleep(delay_s)
                        return ScenarioResult(
                            scenario_id=scenario.id,
                            kind="routing",
                            mode="live",
                            passed=True,
                            critical=scenario.critical,
                            http_status=r.status_code,
                            latency_ms=ms,
                            trace=trace,
                            details={
                                "degraded": "routing_ok_upstream_failed",
                                "http_status": r.status_code,
                                "model_role": trace.get("model_role"),
                            },
                        )
                    except Exception:
                        pass
                return ScenarioResult(
                    scenario_id=scenario.id,
                    kind="routing",
                    mode="live",
                    passed=False,
                    critical=scenario.critical,
                    http_status=r.status_code,
                    latency_ms=ms,
                    error=f"HTTP {r.status_code}: {body}",
                    trace=trace,
                )
            assert trace is not None
            assert_trace_invariants(trace=trace, expect=scenario.expect)
            await asyncio.sleep(delay_s)
            return ScenarioResult(
                scenario_id=scenario.id,
                kind="routing",
                mode="live",
                passed=True,
                critical=scenario.critical,
                http_status=200,
                latency_ms=ms,
                trace=trace,
                details={
                    "model_used": trace.get("model_used"),
                    "routing_source": trace.get("routing_source"),
                    "fallback_used": trace.get("fallback_used"),
                },
            )
    except Exception as e:
        return ScenarioResult(
            scenario_id=scenario.id,
            kind="routing",
            mode="live",
            passed=False,
            critical=scenario.critical,
            error=str(e),
        )


def _report_to_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# GPTHub v4 ops simulator report",
        "",
        f"- **mode:** {report.get('mode')}",
        f"- **passed:** {report.get('passed')}/{report.get('total')}",
        f"- **critical_failures:** {report.get('critical_failures')}",
        "",
        "| scenario | kind | mode | pass | ms | notes |",
        "|----------|------|------|------|-----|-------|",
    ]
    for r in report.get("results") or []:
        notes = r.get("error") or r.get("details", {}).get("model_used") or ""
        lines.append(
            f"| {r.get('scenario_id')} | {r.get('kind')} | {r.get('mode')} | "
            f"{'OK' if r.get('passed') else 'FAIL'} | {r.get('latency_ms') or '-'} | {notes} |"
        )
    return "\n".join(lines) + "\n"


async def run_simulator(
    *,
    mode: str,
    scenarios_path: Path | None,
    base_url: str,
    report_path: Path | None,
    live_delay_s: float,
) -> int:
    scenarios = load_ops_scenarios(scenarios_path)
    results: list[ScenarioResult] = []

    if mode == "mock":
        for sc in scenarios.routing:
            results.append(await run_routing_offline(sc))
            results.append(await run_routing_mock_e2e(sc))
        for sc in scenarios.fault:
            results.append(await run_fault_mock(sc))

    elif mode == "live":
        api_key = os.environ.get("ORCHESTRATOR_API_KEY", "").strip()
        if not api_key:
            print("ORCHESTRATOR_API_KEY required for live mode", file=sys.stderr)
            return 2
        or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not or_key or or_key.startswith("replace") or "PASTE" in or_key.upper():
            print("Valid OPENROUTER_API_KEY required for live mode", file=sys.stderr)
            return 2
        for sc in scenarios.routing:
            results.append(await run_routing_offline(sc))
            if sc.live_skip:
                results.append(
                    ScenarioResult(
                        scenario_id=sc.id,
                        kind="routing",
                        mode="live",
                        passed=True,
                        critical=sc.critical,
                        details={"skipped": "live_skip in scenario"},
                    )
                )
            else:
                results.append(await run_routing_live(sc, base_url=base_url, api_key=api_key, delay_s=live_delay_s))

    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        return 2

    passed = sum(1 for r in results if r.passed)
    critical_failures = [r for r in results if not r.passed and r.critical]
    report: dict[str, Any] = {
        "mode": mode,
        "base_url": base_url if mode == "live" else "mock",
        "catalog_generated_at": load_free_models_catalog().generated_at,
        "total": len(results),
        "passed": passed,
        "critical_failures": len(critical_failures),
        "results": [
            {
                "scenario_id": r.scenario_id,
                "kind": r.kind,
                "mode": r.mode,
                "passed": r.passed,
                "critical": r.critical,
                "latency_ms": r.latency_ms,
                "http_status": r.http_status,
                "error": r.error,
                "details": r.details,
                "trace_summary": {
                    k: (r.trace or {}).get(k)
                    for k in (
                        "task_type",
                        "model_role",
                        "model_used",
                        "fallback_used",
                        "routing_source",
                    )
                }
                if r.trace
                else None,
            }
            for r in results
        ],
    }

    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        md_path = report_path.with_suffix(".md")
        md_path.write_text(_report_to_markdown(report), encoding="utf-8")
        print(f"Report: {report_path}")
        print(f"Summary: {md_path}")

    print(f"ops_simulator mode={mode} passed={passed}/{len(results)} critical_failures={len(critical_failures)}")
    return 1 if critical_failures else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="GPTHub v4 operational simulator")
    parser.add_argument("--mode", choices=("mock", "live"), default="mock")
    parser.add_argument("--base-url", default=os.environ.get("ORCH_URL", "http://127.0.0.1:8089"))
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--scenarios", type=Path, default=None)
    parser.add_argument("--live-delay", type=float, default=1.5, help="Seconds between live OR calls")
    parser.add_argument("--log-level", default="WARNING")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.WARNING))

    default_report = Path("reports") / f"ops-{args.mode}.json"
    report_path = args.report or default_report

    os.environ.setdefault("OPENROUTER_API_KEY", "or-test-key")
    os.environ.setdefault("ORCHESTRATOR_API_KEY", "test-key")
    os.environ["OPENROUTER_REFRESH_CATALOG_ON_STARTUP"] = "false"

    exit_code = asyncio.run(
        run_simulator(
            mode=args.mode,
            scenarios_path=args.scenarios,
            base_url=args.base_url,
            report_path=report_path,
            live_delay_s=args.live_delay,
        )
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
