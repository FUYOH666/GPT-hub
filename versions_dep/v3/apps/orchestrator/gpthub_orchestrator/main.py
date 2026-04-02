"""FastAPI entry: health + OpenAI-compatible proxy with trace."""

from __future__ import annotations

import codecs
import json
import logging
from contextlib import asynccontextmanager
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from gpthub_orchestrator.classifier import classify_messages
from gpthub_orchestrator.clock_context import build_session_clock_block
from gpthub_orchestrator.greeting_canned import (
    canned_chat_completion_json,
    canned_chat_completion_sse_chunks,
    client_visible_model_id,
    greeting_canned_eligible,
)
from gpthub_orchestrator.messages import apply_role_system_messages
from gpthub_orchestrator.public_models import apply_models_catalog, map_facade_model_to_litellm
from gpthub_orchestrator.role_prompts import load_role_prompts
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings, load_settings
from gpthub_orchestrator.reasoning_response_filter import (
    filter_sse_data_line_json,
    merge_reasoning_exclude_into_body,
    strip_reasoning_from_completion_payload,
)
from gpthub_orchestrator.response_preamble_strip import strip_known_cot_preamble
from gpthub_orchestrator.trace import build_trace, trace_to_header_value

logger = logging.getLogger("gpthub_orchestrator")


def _apply_preamble_strip_to_completion(payload: dict[str, Any], settings: Settings) -> None:
    if not settings.orchestrator_strip_known_cot_preamble:
        return
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return
    for ch in choices:
        if not isinstance(ch, dict):
            continue
        msg = ch.get("message")
        if not isinstance(msg, dict):
            continue
        c = msg.get("content")
        if not isinstance(c, str):
            continue
        new_c, applied = strip_known_cot_preamble(c)
        if applied:
            msg["content"] = new_c
            logger.info("preamble_strip_applied_to_completion")


def _apply_reasoning_strip_to_completion(payload: dict[str, Any], settings: Settings) -> None:
    if settings.orchestrator_strip_reasoning_from_response:
        strip_reasoning_from_completion_payload(payload)


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _retryable_litellm_status(status_code: int) -> bool:
    return status_code in (429, 503)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    _configure_logging(settings.log_level)
    load_role_prompts(settings.role_prompts_path)
    sec = float(settings.litellm_timeout_seconds)
    timeout = httpx.Timeout(
        connect=min(60.0, sec),
        read=sec,
        write=sec,
        pool=min(60.0, sec),
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        app.state.settings = settings
        app.state.http = client
        yield


app = FastAPI(title="GPTHub Orchestrator", version="0.1.0", lifespan=lifespan)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def verify_bearer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if token != settings.orchestrator_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "gpthub-orchestrator"}


@app.get("/v1/models")
async def openai_list_models(
    request: Request,
    settings: Settings = Depends(get_settings),
    http: httpx.AsyncClient = Depends(get_http),
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    """Proxy for Open WebUI: it calls GET /v1/models to populate the model dropdown."""
    url = f"{settings.litellm_base_url.rstrip('/')}/v1/models"
    resp = await http.get(url, headers={"Authorization": request.headers.get("Authorization", "")})
    if resp.status_code >= 400:
        logger.warning("litellm_models_error %s %s", resp.status_code, resp.text[:400])
        return _error_json_response(resp)
    ct = resp.headers.get("content-type", "")
    if "application/json" not in ct:
        return _error_json_response(resp)
    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return _error_json_response(resp)
    if not isinstance(payload, dict):
        return _error_json_response(resp)
    filtered = apply_models_catalog(payload, settings)
    return JSONResponse(status_code=200, content=filtered)


def _error_json_response(resp: httpx.Response) -> JSONResponse:
    ct = resp.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            payload = resp.json()
        except json.JSONDecodeError:
            payload = {"detail": resp.text}
    else:
        payload = {"detail": resp.text}
    return JSONResponse(status_code=resp.status_code, content=payload)


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    settings: Settings = Depends(get_settings),
    http: httpx.AsyncClient = Depends(get_http),
    _: None = Depends(verify_bearer),
) -> Response:
    try:
        body: dict[str, Any] = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be a list")

    map_facade_model_to_litellm(body, settings)

    classification = classify_messages(messages)
    router_suggestion = choose_model(classification, settings)
    clock_prefix, server_clock_iso = build_session_clock_block(settings)

    if settings.greeting_canned_response_enabled and greeting_canned_eligible(classification):
        role_prompts = load_role_prompts(settings.role_prompts_path)
        prompt_version = role_prompts.prompt_version
        model_vis = client_visible_model_id(body, settings.orchestrator_public_model_id)
        canned_text = settings.greeting_canned_message
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=model_vis,
            artifacts=[],
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            canned_response=True,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
        trace_hdr = trace_to_header_value(trace)
        stream = bool(body.get("stream"))
        if stream:

            async def canned_sse():
                for chunk in canned_chat_completion_sse_chunks(model=model_vis, content=canned_text):
                    yield chunk

            return StreamingResponse(
                canned_sse(),
                media_type="text/event-stream",
                headers={"X-GPTHub-Trace": trace_hdr},
            )
        out = canned_chat_completion_json(model=model_vis, content=canned_text)
        return JSONResponse(content=out, headers={"X-GPTHub-Trace": trace_hdr})

    role_prompts = load_role_prompts(settings.role_prompts_path)
    role_key = str(router_suggestion["model_role"])
    body["messages"] = apply_role_system_messages(
        list(messages),
        role_key,
        role_prompts,
        session_clock_prefix=clock_prefix,
    )
    prompt_version = role_prompts.prompt_version

    chain: list[str] = list(router_suggestion.get("fallback_aliases") or [router_suggestion["model_name"]])

    model_used = str(body.get("model") or chain[0])
    if settings.auto_route_model:
        model_used = chain[0]
        body["model"] = model_used

    merge_reasoning_exclude_into_body(
        body,
        enabled=settings.orchestrator_request_reasoning_exclude,
    )

    stream = bool(body.get("stream"))
    url = f"{settings.litellm_base_url.rstrip('/')}/v1/chat/completions"
    auth_header = request.headers.get("Authorization", "")

    if stream:
        stream_fb: dict[str, Any] = {
            "mode": "stream_single_attempt",
            "auto_route_model": settings.auto_route_model,
            "note": "orchestrator does not chain fallback for stream; LiteLLM fallbacks apply",
        }
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=str(body.get("model", model_used)),
            artifacts=[],
            orchestrator_fallback=stream_fb,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))

        def _sse_error_event(message: str, *, err_type: str = "upstream_error", code: int | None = None) -> bytes:
            err_obj: dict[str, Any] = {"error": {"message": message, "type": err_type}}
            if code is not None:
                err_obj["error"]["code"] = code
            return f"data: {json.dumps(err_obj, ensure_ascii=False)}\n\n".encode("utf-8")

        async def passthrough():
            try:
                async with http.stream(
                    "POST",
                    url,
                    json=body,
                    headers={"Authorization": auth_header},
                ) as r:
                    if r.status_code >= 400:
                        err_bytes = await r.aread()
                        preview = err_bytes[:1200].decode("utf-8", errors="replace")
                        logger.warning(
                            "litellm_stream_upstream_error status=%s preview=%s",
                            r.status_code,
                            preview,
                        )
                        try:
                            parsed = json.loads(err_bytes)
                            inner = parsed.get("error")
                            if isinstance(inner, dict):
                                msg = str(inner.get("message", preview))
                            elif isinstance(inner, str):
                                msg = inner
                            else:
                                msg = preview
                        except json.JSONDecodeError:
                            msg = preview
                        yield _sse_error_event(msg, code=r.status_code)
                        yield b"data: [DONE]\n\n"
                        return
                    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
                    pending = ""
                    async for chunk in r.aiter_bytes():
                        pending += decoder.decode(chunk)
                        while "\n" in pending:
                            line, pending = pending.split("\n", 1)
                            if settings.orchestrator_strip_reasoning_from_response:
                                line = filter_sse_data_line_json(
                                    line,
                                    strip_enabled=True,
                                )
                            yield (line + "\n").encode("utf-8")
                    pending += decoder.decode(b"", final=True)
                    if pending:
                        line = pending.rstrip("\r")
                        if settings.orchestrator_strip_reasoning_from_response:
                            line = filter_sse_data_line_json(line, strip_enabled=True)
                        yield (line + "\n").encode("utf-8")
            except httpx.TimeoutException:
                logger.exception("litellm_stream_timeout")
                yield _sse_error_event(
                    "Upstream LLM stream timed out (increase LITELLM_TIMEOUT_SECONDS)",
                    err_type="timeout",
                    code=504,
                )
                yield b"data: [DONE]\n\n"
            except httpx.HTTPError:
                logger.exception("litellm_stream_http_error")
                yield _sse_error_event("Upstream LLM connection error", err_type="connection_error", code=502)
                yield b"data: [DONE]\n\n"

        return StreamingResponse(
            passthrough(),
            media_type="text/event-stream",
            headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
        )

    use_chain = (
        settings.auto_route_model
        and settings.orchestrator_litellm_fallback
        and len(chain) > 0
    )
    max_t = min(len(chain), settings.orchestrator_fallback_max_attempts) if use_chain else 1

    if not use_chain:
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=model_used,
            artifacts=[],
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
        resp = await http.post(url, json=body, headers={"Authorization": auth_header})
        if resp.status_code >= 400:
            logger.warning("litellm_error %s %s", resp.status_code, resp.text[:500])
            return _error_json_response(resp)
        out = resp.json()
        if isinstance(out, dict):
            _apply_reasoning_strip_to_completion(out, settings)
            _apply_preamble_strip_to_completion(out, settings)
        return JSONResponse(
            content=out,
            headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
        )

    attempts_log: list[dict[str, Any]] = []
    last_resp: httpx.Response | None = None
    winning_model = model_used

    for i in range(max_t):
        alias = chain[i]
        body_attempt = dict(body)
        body_attempt["model"] = alias
        winning_model = alias
        resp = await http.post(url, json=body_attempt, headers={"Authorization": auth_header})
        attempts_log.append({"model": alias, "status_code": resp.status_code})
        if resp.status_code < 400:
            fb_meta: dict[str, Any] = {
                "enabled": True,
                "attempts": attempts_log,
                "model_selected": alias,
                "retries_after_failure": max(0, i),
            }
            trace = build_trace(
                classification=classification,
                router_suggestion=router_suggestion,
                model_used=winning_model,
                artifacts=[],
                orchestrator_fallback=fb_meta,
                prompt_version=prompt_version,
                classifier_source="heuristic",
                server_clock_iso=server_clock_iso,
            )
            logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
            out = resp.json()
            if isinstance(out, dict):
                _apply_reasoning_strip_to_completion(out, settings)
                _apply_preamble_strip_to_completion(out, settings)
            return JSONResponse(
                content=out,
                headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
            )
        last_resp = resp
        logger.warning(
            "litellm_attempt_failed status=%s model=%s body_preview=%s",
            resp.status_code,
            alias,
            resp.text[:300],
        )
        if i < max_t - 1 and _retryable_litellm_status(resp.status_code):
            continue
        break

    assert last_resp is not None
    fb_meta = {
        "enabled": True,
        "attempts": attempts_log,
        "failed": True,
    }
    trace = build_trace(
        classification=classification,
        router_suggestion=router_suggestion,
        model_used=winning_model,
        artifacts=[],
        orchestrator_fallback=fb_meta,
        prompt_version=prompt_version,
        classifier_source="heuristic",
        server_clock_iso=server_clock_iso,
    )
    logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
    logger.warning("litellm_error %s %s", last_resp.status_code, last_resp.text[:500])
    trace_hdr = trace_to_header_value(trace)
    err_resp = _error_json_response(last_resp)
    err_payload: Any
    if isinstance(err_resp.body, (bytes, memoryview)):
        err_payload = json.loads(bytes(err_resp.body).decode("utf-8"))
    else:
        err_payload = err_resp.body
    return JSONResponse(
        status_code=err_resp.status_code,
        content=err_payload,
        headers={**dict(err_resp.headers), "X-GPTHub-Trace": trace_hdr},
    )
