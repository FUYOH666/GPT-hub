"""Model → key fallback orchestration for OpenRouter free tier."""

from __future__ import annotations

import logging
from typing import Any

from gpthub_orchestrator.openrouter.key_pool import KeyPool, KeyPoolEntry

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def is_retryable_status(status_code: int) -> bool:
    return status_code in RETRYABLE_STATUS


class FallbackExecutor:
    """Try model chain with key rotation on retryable errors."""

    def __init__(self, key_pool: KeyPool, *, max_attempts: int = 8) -> None:
        self._key_pool = key_pool
        self._max_attempts = max(1, max_attempts)

    def plan_attempts(self, model_chain: list[str]) -> list[str]:
        """Expand model chain into attempt list (model-first order)."""
        if not model_chain:
            raise ValueError("model_chain must not be empty")
        attempts: list[str] = []
        for model in model_chain:
            attempts.append(model)
        return attempts[: self._max_attempts]
