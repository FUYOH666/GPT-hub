"""Run ingest on the last user message and inject artifacts as a client system block."""

from __future__ import annotations

import asyncio
import copy
import json
import logging
import time
from typing import Any

import httpx

from gpthub_orchestrator.ingest.asr_client import AsrError, transcribe_audio_bytes
from gpthub_orchestrator.ingest.parts import (
    FileWorkItem,
    extract_file_work_items,
    strip_content_indices,
)
from gpthub_orchestrator.ingest.pdf_extract import PdfExtractError, parse_pdf_bytes
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

_ARTIFACT_CONTENT_CAP = 24_000


def _is_audio_item(mime: str, filename: str) -> bool:
    if mime.startswith("audio/"):
        return True
    low = filename.lower()
    return low.endswith((".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"))


def _artifact_for_trace(a: dict[str, Any]) -> dict[str, Any]:
    """Smaller payload for trace header."""
    out = dict(a)
    c = out.get("content")
    if isinstance(c, str) and len(c) > 2000:
        out["content"] = c[:2000] + f"\n… [{len(c) - 2000} chars truncated for trace]"
    return out


def _build_artifact_system_message(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    lines = ["## GPTHub ingested context (orchestrator)", ""]
    for a in artifacts:
        t = a.get("type")
        title = a.get("title", "")
        content = a.get("content", "")
        lines.append(f"### {t}: {title}")
        lines.append(str(content))
        lines.append("")
    body = "\n".join(lines).strip()
    return {"role": "system", "content": body}


def _parse_pdf_sync(item: FileWorkItem, settings: Settings) -> str:
    try:
        return parse_pdf_bytes(
            item.raw,
            max_bytes=settings.ingest_pdf_max_bytes,
            max_pages=settings.ingest_pdf_max_pages,
        )
    except PdfExtractError as e:
        logger.warning("pdf_ingest_failed file=%s err=%s", item.filename, e)
        return f"[PDF could not be extracted: {e}]"


async def _process_one_pdf(item: FileWorkItem, settings: Settings) -> dict[str, Any]:
    text = await asyncio.to_thread(_parse_pdf_sync, item, settings)
    if len(text) > _ARTIFACT_CONTENT_CAP:
        text = text[:_ARTIFACT_CONTENT_CAP] + "\n… [truncated by orchestrator]"
    return {"type": "document_text", "title": item.filename, "content": text}


async def _process_one_audio(
    item: FileWorkItem,
    settings: Settings,
    http: httpx.AsyncClient,
) -> dict[str, Any]:
    if not settings.orchestrator_asr_base_url:
        return {
            "type": "transcript",
            "title": item.filename,
            "content": "[Audio attachment present; set ORCHESTRATOR_ASR_BASE_URL to transcribe.]",
        }
    ct = item.mime if "/" in item.mime else "application/octet-stream"
    try:
        text = await transcribe_audio_bytes(
            http,
            base_url=settings.orchestrator_asr_base_url,
            api_key=settings.orchestrator_asr_api_key,
            model=settings.orchestrator_asr_model,
            data=item.raw,
            filename=item.filename,
            content_type=ct,
        )
    except AsrError as e:
        logger.warning("asr_ingest_failed file=%s err=%s", item.filename, e)
        text = f"[ASR error: {e}]"
    if len(text) > _ARTIFACT_CONTENT_CAP:
        text = text[:_ARTIFACT_CONTENT_CAP] + "\n… [truncated]"
    return {"type": "transcript", "title": item.filename, "content": text}


async def run_ingest_pipeline(
    messages: list[dict[str, Any]],
    settings: Settings,
    http: httpx.AsyncClient,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float | None]:
    """
    Deep-copy messages, extract PDF/audio from last user parts, append artifacts as system message.

    Returns (new_messages, trace_artifacts, ingest_ms).
    """
    if not settings.ingest_enabled:
        return messages, [], None

    peek_idx, peek_items = extract_file_work_items(messages)
    if peek_idx is None or not peek_items:
        return messages, [], None

    t0 = time.perf_counter()
    msgs = copy.deepcopy(messages)
    user_idx, indexed_items = extract_file_work_items(msgs)
    if user_idx is None or not indexed_items:
        return messages, [], None

    drop_indices: set[int] = set()
    tasks: list[Any] = []
    meta: list[tuple[str, int]] = []  # kind, part_index

    for part_idx, item in indexed_items:
        if item.mime == "application/pdf":
            tasks.append(_process_one_pdf(item, settings))
            meta.append(("pdf", part_idx))
            drop_indices.add(part_idx)
        elif _is_audio_item(item.mime, item.filename):
            tasks.append(_process_one_audio(item, settings, http))
            meta.append(("audio", part_idx))
            drop_indices.add(part_idx)

    if not tasks:
        return messages, [], None

    results = await asyncio.gather(*tasks, return_exceptions=True)
    artifacts: list[dict[str, Any]] = []
    for (kind, part_idx), res in zip(meta, results, strict=True):
        if isinstance(res, Exception):
            logger.warning("ingest_task_failed kind=%s part=%s err=%s", kind, part_idx, res)
            artifacts.append(
                {
                    "type": "ingest_error",
                    "title": str(part_idx),
                    "content": str(res),
                }
            )
            continue
        artifacts.append(res)

    strip_content_indices(msgs, user_idx, drop_indices)
    sys_msg = _build_artifact_system_message(artifacts)
    msgs.insert(0, sys_msg)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    trace_artifacts = [_artifact_for_trace(a) for a in artifacts]
    logger.info(
        "ingest_complete ms=%.2f artifacts=%s",
        elapsed_ms,
        json.dumps([a.get("type") for a in artifacts]),
    )
    return msgs, trace_artifacts, elapsed_ms
