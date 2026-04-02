"""Modality / task hints from OpenAI-style chat messages (rule-based v1)."""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    SIMPLE_CHAT = "simple_chat"
    CODE_HELP = "code_help"
    FILE_ANALYSIS = "file_analysis"
    SUMMARIZATION = "summarization"
    IMAGE_ANALYSIS = "image_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    MULTIMODAL_WORKFLOW = "multimodal_workflow"


def _flatten_text(parts: list[dict[str, Any]] | str) -> str:
    if isinstance(parts, str):
        return parts
    chunks: list[str] = []
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text":
            chunks.append(str(p.get("text", "")))
    return " ".join(chunks)


def _message_text(m: dict[str, Any]) -> str:
    c = m.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return _flatten_text(c)
    return ""


def _has_image_part(content: Any) -> bool:
    if isinstance(content, list):
        for p in content:
            if not isinstance(p, dict):
                continue
            if p.get("type") == "image_url":
                return True
            if p.get("type") == "image":
                return True
    return False


def classify_messages(messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Return modalities, task_type, complexity_hint for trace + router."""
    has_image = any(_has_image_part(m.get("content")) for m in messages)
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = _message_text(m)
            break

    lower = last_user.lower()
    code_hints = any(
        x in lower
        for x in (
            "traceback",
            "exception",
            "async def",
            "def ",
            "import ",
            "typescript",
            "javascript",
            "fastapi",
            "docker",
        )
    )
    analyze_hints = any(x in lower for x in ("analyze", "compare", "architecture", "debug", "анализ", "сравни"))
    doc_hints = any(
        x in lower
        for x in (
            "summarize",
            "summary",
            "tl;dr",
            "pdf",
            "document",
            "docx",
            "whitepaper",
            "суммариз",
            "документ",
            "конспект",
        )
    )
    long_text = len(last_user) > 6000

    modalities: list[str] = ["text"]
    if has_image:
        modalities.append("image")

    if has_image and (analyze_hints or code_hints):
        task = TaskType.MULTIMODAL_WORKFLOW
    elif has_image:
        task = TaskType.IMAGE_ANALYSIS
    elif (doc_hints or long_text) and not has_image:
        task = TaskType.SUMMARIZATION if doc_hints else TaskType.FILE_ANALYSIS
    elif code_hints or analyze_hints:
        task = TaskType.CODE_HELP
    else:
        task = TaskType.SIMPLE_CHAT

    complexity = 0
    if len(modalities) > 1 or (has_image and analyze_hints):
        complexity += 2
    if code_hints:
        complexity += 1
    if analyze_hints:
        complexity += 1

    out = {
        "modalities": modalities,
        "task_type": task.value,
        "complexity_score": complexity,
        "user_text_preview": last_user[:200],
    }
    logger.info(
        "modality_classified",
        extra={"extra": json.dumps(out, ensure_ascii=False)},
    )
    return out
