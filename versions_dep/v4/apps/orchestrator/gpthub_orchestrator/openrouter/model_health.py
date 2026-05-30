"""Runtime health scoring: temporary ban for slugs after repeated 429s."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ModelHealthTracker:
    """In-memory ban list with TTL after N retryable failures per slug."""

    ban_after_failures: int = 3
    ban_ttl_seconds: float = 3600.0
    _failures: dict[str, int] = field(default_factory=dict)
    _banned_until: dict[str, float] = field(default_factory=dict)

    def record_failure(self, model: str, *, status_code: int) -> None:
        if status_code != 429:
            return
        now = time.monotonic()
        self._purge_expired(now)
        slug = model.strip()
        if not slug:
            return
        count = self._failures.get(slug, 0) + 1
        self._failures[slug] = count
        if count >= max(1, self.ban_after_failures):
            until = now + max(60.0, self.ban_ttl_seconds)
            self._banned_until[slug] = until
            logger.warning(
                "model_health_banned model=%s failures=%s ttl_seconds=%s",
                slug,
                count,
                self.ban_ttl_seconds,
            )

    def record_success(self, model: str) -> None:
        slug = model.strip()
        if not slug:
            return
        self._failures.pop(slug, None)
        self._banned_until.pop(slug, None)

    def is_banned(self, model: str) -> bool:
        now = time.monotonic()
        self._purge_expired(now)
        slug = model.strip()
        return slug in self._banned_until

    def filter_chain(self, chain: list[str]) -> list[str]:
        """Drop banned slugs; if all banned, return original chain."""
        if not chain:
            return chain
        available = [m for m in chain if not self.is_banned(m)]
        if available:
            return available
        logger.warning("model_health_all_banned chain_len=%s", len(chain))
        return list(chain)

    def snapshot(self) -> dict[str, object]:
        now = time.monotonic()
        self._purge_expired(now)
        banned: list[dict[str, object]] = []
        for slug, until in sorted(self._banned_until.items()):
            banned.append(
                {
                    "model": slug,
                    "failures": self._failures.get(slug, 0),
                    "banned_seconds_remaining": max(0.0, round(until - now, 1)),
                }
            )
        return {
            "ban_after_failures": self.ban_after_failures,
            "ban_ttl_seconds": self.ban_ttl_seconds,
            "banned": banned,
        }

    def _purge_expired(self, now: float) -> None:
        expired = [slug for slug, until in self._banned_until.items() if until <= now]
        for slug in expired:
            self._banned_until.pop(slug, None)
            self._failures.pop(slug, None)
