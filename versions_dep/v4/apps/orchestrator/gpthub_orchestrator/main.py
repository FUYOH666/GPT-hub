"""FastAPI entry: health + OpenAI-compatible proxy with OpenRouter survival engine."""

from __future__ import annotations

import asyncio
import codecs
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from gpthub_orchestrator.classifier import classify_messages
from gpthub_orchestrator.clock_context import build_session_clock_block
from gpthub_orchestrator.greeting_canned import (
    canned_chat_completion_json,
    canned_chat_completion_sse_chunks,
    client_visible_model_id,
    greeting_canned_eligible,
)
from gpthub_orchestrator.messages import apply_role_system_messages
from gpthub_orchestrator.openrouter.catalog import load_free_models_catalog
from gpthub_orchestrator.openrouter.catalog_refresh import (
    CatalogRefreshError,
    fetch_models_async,
    refresh_catalog_from_openrouter,
)
from gpthub_orchestrator.openrouter.client import (
    OPENROUTER_EXHAUSTED_MESSAGE_RU,
    OpenRouterClient,
    OpenRouterExhaustedError,
)
from gpthub_orchestrator.openrouter.curator import run_curator
from gpthub_orchestrator.openrouter.routing_manifest import curator_manifest, routing_source
from gpthub_orchestrator.public_models import build_models_list, map_facade_model_to_backend
from gpthub_orchestrator.role_prompts import load_role_prompts
from gpthub_orchestrator.router import choose_model
from gpthub_orchestrator.settings import Settings, load_settings
from gpthub_orchestrator.reasoning_response_filter import (
    filter_sse_data_line_json,
    merge_reasoning_exclude_into_body,
    strip_reasoning_from_completion_payload,
)
from gpthub_orchestrator.response_preamble_strip import strip_known_cot_preamble
from gpthub_orchestrator.ingest.pipeline import run_ingest_pipeline
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


def _catalog_persist_path(settings: Settings) -> Path | None:
    if not settings.openrouter_catalog_persist_on_refresh:
        return None
    if settings.free_models_catalog_path:
        return Path(settings.free_models_catalog_path)
    from gpthub_orchestrator.openrouter.catalog import _PACKAGE_CATALOG

    return _PACKAGE_CATALOG.parent / "free_models_catalog.runtime.yaml"


async def _refresh_catalog_task(app: FastAPI, settings: Settings, http: httpx.AsyncClient) -> None:
    persist = _catalog_persist_path(settings)
    catalog = await refresh_catalog_from_openrouter(
        http,
        api_key=settings.openrouter_api_key,
        api_base=settings.openrouter_api_base,
        text_limit=settings.openrouter_catalog_text_limit,
        vision_limit=settings.openrouter_catalog_vision_limit,
        persist_path=persist,
    )
    app.state.catalog_refresh = {
        "ok": True,
        "source": "openrouter_live",
        "generated_at": catalog.generated_at,
        "text_fast": catalog.text_fast,
        "vision": catalog.vision,
        "error": None,
    }


async def _periodic_catalog_refresh(app: FastAPI, settings: Settings, http: httpx.AsyncClient) -> None:
    interval_h = float(settings.openrouter_catalog_refresh_interval_hours)
    if interval_h <= 0:
        return
    interval_s = interval_h * 3600.0
    while True:
        await asyncio.sleep(interval_s)
        try:
            await _refresh_catalog_task(app, settings, http)
            logger.info("periodic_catalog_refresh_ok interval_hours=%s", interval_h)
        except Exception as e:
            logger.warning("periodic_catalog_refresh_failed error=%s", e)


async def _curator_background(app: FastAPI, settings: Settings, http: httpx.AsyncClient) -> None:
    if not settings.openrouter_curator_enabled:
        app.state.curator = {"status": "disabled"}
        return
    app.state.curator = {"status": "running", "routing_source": routing_source()}
    try:
        models = await fetch_models_async(
            http,
            api_base=settings.openrouter_api_base,
            api_key=settings.openrouter_api_key,
        )
        base = load_free_models_catalog(settings.free_models_catalog_path)
        manifest = await run_curator(http, settings, models, base_catalog=base)
        app.state.curator = {
            "status": "ok",
            "routing_source": routing_source(),
            "manifest_version": manifest.version,
            "rationale_short": manifest.rationale_short,
        }
        logger.info("curator_background_ok manifest_version=%s", manifest.version)
    except Exception as e:
        logger.warning("curator_background_failed error=%s", e)
        app.state.curator = {
            "status": "failed",
            "routing_source": routing_source(),
            "error": str(e),
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    _configure_logging(settings.log_level)
    load_role_prompts(settings.role_prompts_path)
    sec = float(settings.openrouter_timeout_seconds)
    timeout = httpx.Timeout(
        connect=min(60.0, sec),
        read=sec,
        write=sec,
        pool=min(60.0, sec),
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        app.state.settings = settings
        app.state.http = client
        app.state.catalog_refresh = {"ok": False, "source": "packaged", "error": None}
        app.state.curator = {"status": "pending"}

        if settings.openrouter_refresh_catalog_on_startup:
            persist = _catalog_persist_path(settings)
            try:
                catalog = await refresh_catalog_from_openrouter(
                    client,
                    api_key=settings.openrouter_api_key,
                    api_base=settings.openrouter_api_base,
                    text_limit=settings.openrouter_catalog_text_limit,
                    vision_limit=settings.openrouter_catalog_vision_limit,
                    persist_path=persist,
                )
                app.state.catalog_refresh = {
                    "ok": True,
                    "source": "openrouter_live",
                    "generated_at": catalog.generated_at,
                    "text_fast": catalog.text_fast,
                    "vision": catalog.vision,
                    "error": None,
                }
            except CatalogRefreshError as e:
                logger.warning("catalog_refresh_failed error=%s", e)
                app.state.catalog_refresh = {
                    "ok": False,
                    "source": "packaged_fallback",
                    "error": str(e),
                }
                if settings.openrouter_catalog_fail_on_refresh_error:
                    raise
                load_free_models_catalog(settings.free_models_catalog_path)
            except httpx.HTTPError as e:
                logger.exception("catalog_refresh_http_error")
                app.state.catalog_refresh = {
                    "ok": False,
                    "source": "packaged_fallback",
                    "error": str(e),
                }
                if settings.openrouter_catalog_fail_on_refresh_error:
                    raise CatalogRefreshError(str(e)) from e
                load_free_models_catalog(settings.free_models_catalog_path)
        else:
            load_free_models_catalog(settings.free_models_catalog_path)

        app.state.openrouter = OpenRouterClient(client, settings)

        refresh_task: asyncio.Task[None] | None = None
        curator_task: asyncio.Task[None] | None = None
        if settings.openrouter_catalog_refresh_interval_hours > 0:
            refresh_task = asyncio.create_task(_periodic_catalog_refresh(app, settings, client))
        if settings.openrouter_curator_enabled:
            curator_task = asyncio.create_task(_curator_background(app, settings, client))
        else:
            app.state.curator = {"status": "disabled"}

        yield

        for task in (refresh_task, curator_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


app = FastAPI(title="GPTHub Orchestrator v4", version="0.4.0", lifespan=lifespan)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_openrouter(request: Request) -> OpenRouterClient:
    return request.app.state.openrouter


def verify_bearer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if token != settings.orchestrator_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


def verify_admin_bearer(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization[7:].strip()
    if token != settings.orchestrator_admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


def _openrouter_exhausted_payload(e: OpenRouterExhaustedError) -> dict[str, Any]:
    return {
        "error": {
            "message": str(e),
            "message_ru": OPENROUTER_EXHAUSTED_MESSAGE_RU,
            "type": "openrouter_exhausted",
            "attempts": e.attempts,
            "hint": "Попробуйте позже или отключите stream для полной цепочки fallback.",
        }
    }


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "gpthub-orchestrator", "backend": "openrouter"}


@app.get("/readyz")
async def readyz(
    request: Request,
    or_client: OpenRouterClient = Depends(get_openrouter),
) -> dict[str, Any]:
    ok = await or_client.health_check()
    if not ok:
        logger.warning("readyz_openrouter_unreachable")
        raise HTTPException(status_code=503, detail="OpenRouter unreachable")
    catalog_meta = getattr(request.app.state, "catalog_refresh", {})
    catalog = load_free_models_catalog()
    return {
        "status": "ready",
        "service": "gpthub-orchestrator",
        "openrouter": "ok",
        "catalog_refresh": catalog_meta,
        "active_catalog": {
            "generated_at": catalog.generated_at,
            "text_fast": catalog.text_fast,
            "vision": catalog.vision,
            "routing_source": routing_source(),
        },
    }


_TRACE_PAGE_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <title>GPTHub Trace</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
    textarea { width: 100%; min-height: 120px; font-family: monospace; }
    pre { background: #f4f4f4; padding: 1rem; overflow: auto; border-radius: 6px; }
    .hint { color: #555; font-size: 0.95rem; }
  </style>
</head>
<body>
  <h1>GPTHub · Trace decoder</h1>
  <p class="hint">Вставьте значение заголовка <code>X-GPTHub-Trace</code> (base64) из ответа оркестратора.</p>
  <textarea id="input" placeholder="eyJkZXRlY3RlZF90YXNrIjog..."></textarea>
  <p><button type="button" id="decode">Decode</button></p>
  <pre id="out">{}</pre>
  <script>
    const params = new URLSearchParams(location.search);
    const q = params.get('trace');
    if (q) document.getElementById('input').value = q;
    document.getElementById('decode').onclick = () => {
      const raw = document.getElementById('input').value.trim();
      try {
        const json = JSON.parse(atob(raw));
        document.getElementById('out').textContent = JSON.stringify(json, null, 2);
      } catch (e) {
        document.getElementById('out').textContent = 'Invalid trace: ' + e;
      }
    };
    if (q) document.getElementById('decode').click();
  </script>
</body>
</html>"""


@app.get("/trace", response_class=HTMLResponse)
async def trace_decoder_page() -> HTMLResponse:
    return HTMLResponse(content=_TRACE_PAGE_HTML)


@app.get("/v1/admin/catalog")
async def admin_catalog(
    request: Request,
    or_client: OpenRouterClient = Depends(get_openrouter),
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_admin_bearer),
) -> dict[str, Any]:
    catalog = load_free_models_catalog(settings.free_models_catalog_path)
    manifest = curator_manifest()
    return {
        "catalog_refresh": getattr(request.app.state, "catalog_refresh", {}),
        "active_catalog": catalog.model_dump(),
        "routing_source": routing_source(),
        "curator": getattr(request.app.state, "curator", {}),
        "manifest": manifest.model_dump() if manifest else None,
        "model_health": or_client.model_health.snapshot(),
        "key_pool_quota": or_client.key_pool.quota_snapshot(),
    }


@app.get("/v1/models")
async def openai_list_models(
    settings: Settings = Depends(get_settings),
    _: None = Depends(verify_bearer),
) -> JSONResponse:
    catalog = load_free_models_catalog(settings.free_models_catalog_path)
    payload = build_models_list(settings, catalog)
    return JSONResponse(status_code=200, content=payload)


def _fallback_meta_from_or(or_meta: dict[str, Any]) -> dict[str, Any]:
    attempts = or_meta.get("attempts") or []
    retries = max(0, len(attempts) - 1)
    return {
        "enabled": True,
        "attempts": attempts,
        "model_attempts": attempts,
        "model_selected": or_meta.get("openrouter_model"),
        "retries_after_failure": retries,
        "openrouter": or_meta,
    }


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    settings: Settings = Depends(get_settings),
    http: httpx.AsyncClient = Depends(get_http),
    or_client: OpenRouterClient = Depends(get_openrouter),
    _: None = Depends(verify_bearer),
) -> Response:
    try:
        body: dict[str, Any] = await request.json()
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from e

    messages = body.get("messages")
    if not isinstance(messages, list):
        raise HTTPException(status_code=400, detail="messages must be a list")

    ingested, ingest_artifacts, ingest_ms = await run_ingest_pipeline(messages, settings, http)
    body["messages"] = ingested

    map_facade_model_to_backend(body, settings)

    classification = classify_messages(body["messages"])
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
            artifacts=ingest_artifacts,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            canned_response=True,
            ingest_ms=ingest_ms,
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
        list(body["messages"]),
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

    if stream:
        stream_chain = chain if settings.auto_route_model else [str(body.get("model", chain[0]))]
        try:
            byte_iter, or_meta = await or_client.chat_completions_stream(body, model_chain=stream_chain)
        except OpenRouterExhaustedError as e:
            trace = build_trace(
                classification=classification,
                router_suggestion=router_suggestion,
                model_used=stream_chain[-1],
                artifacts=ingest_artifacts,
                orchestrator_fallback={"enabled": True, "attempts": e.attempts, "failed": True},
                prompt_version=prompt_version,
                classifier_source="heuristic",
                server_clock_iso=server_clock_iso,
                ingest_ms=ingest_ms,
            )
            return JSONResponse(
                status_code=503,
                content=_openrouter_exhausted_payload(e),
                headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e

        stream_fb: dict[str, Any] = {
            "mode": "stream_fallback",
            "auto_route_model": settings.auto_route_model,
            "attempts": or_meta.get("attempts") or [],
        }
        winning = str(or_meta.get("openrouter_model") or stream_chain[0])
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=winning,
            artifacts=ingest_artifacts,
            orchestrator_fallback=stream_fb,
            openrouter_meta=or_meta,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            ingest_ms=ingest_ms,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))

        async def passthrough():
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            pending = ""
            async for chunk in byte_iter:
                pending += decoder.decode(chunk)
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    if settings.orchestrator_strip_reasoning_from_response:
                        line = filter_sse_data_line_json(line, strip_enabled=True)
                    yield (line + "\n").encode("utf-8")
            pending += decoder.decode(b"", final=True)
            if pending:
                line = pending.rstrip("\r")
                if settings.orchestrator_strip_reasoning_from_response:
                    line = filter_sse_data_line_json(line, strip_enabled=True)
                yield (line + "\n").encode("utf-8")

        return StreamingResponse(
            passthrough(),
            media_type="text/event-stream",
            headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
        )

    use_fallback = settings.auto_route_model and settings.orchestrator_openrouter_fallback and len(chain) > 0

    if not use_fallback:
        single_chain = [str(body.get("model", model_used))]
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=model_used,
            artifacts=ingest_artifacts,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            ingest_ms=ingest_ms,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
        try:
            out, or_meta = await or_client.chat_completions(body, model_chain=single_chain)
        except OpenRouterExhaustedError as e:
            return JSONResponse(
                status_code=503,
                content=_openrouter_exhausted_payload(e),
                headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
            )
        except RuntimeError as e:
            raise HTTPException(status_code=503, detail=str(e)) from e
        _apply_reasoning_strip_to_completion(out, settings)
        _apply_preamble_strip_to_completion(out, settings)
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=str(out.get("model") or model_used),
            artifacts=ingest_artifacts,
            openrouter_meta=or_meta,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            ingest_ms=ingest_ms,
        )
        return JSONResponse(content=out, headers={"X-GPTHub-Trace": trace_to_header_value(trace)})

    try:
        out, or_meta = await or_client.chat_completions(body, model_chain=chain)
    except OpenRouterExhaustedError as e:
        fb_meta = {
            "enabled": True,
            "attempts": e.attempts,
            "model_attempts": e.attempts,
            "failed": True,
        }
        trace = build_trace(
            classification=classification,
            router_suggestion=router_suggestion,
            model_used=chain[-1],
            artifacts=ingest_artifacts,
            orchestrator_fallback=fb_meta,
            prompt_version=prompt_version,
            classifier_source="heuristic",
            server_clock_iso=server_clock_iso,
            ingest_ms=ingest_ms,
        )
        logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
        return JSONResponse(
            status_code=503,
            content=_openrouter_exhausted_payload(e),
            headers={"X-GPTHub-Trace": trace_to_header_value(trace)},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    fb_meta = _fallback_meta_from_or(or_meta)
    winning = str(or_meta.get("openrouter_model") or model_used)
    trace = build_trace(
        classification=classification,
        router_suggestion=router_suggestion,
        model_used=winning,
        artifacts=ingest_artifacts,
        orchestrator_fallback=fb_meta,
        openrouter_meta=or_meta,
        prompt_version=prompt_version,
        classifier_source="heuristic",
        server_clock_iso=server_clock_iso,
        ingest_ms=ingest_ms,
    )
    logger.info("execution_trace %s", json.dumps(trace, ensure_ascii=False))
    _apply_reasoning_strip_to_completion(out, settings)
    _apply_preamble_strip_to_completion(out, settings)
    return JSONResponse(content=out, headers={"X-GPTHub-Trace": trace_to_header_value(trace)})
