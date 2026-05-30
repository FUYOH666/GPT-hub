"""Quota-aware OpenRouter API key pool with throttle and cooldown."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

DEFAULT_RPM_LIMIT = 20
DEFAULT_COOLDOWN_SECONDS = 4 * 3600


@dataclass
class KeyPoolEntry:
    key: str
    daily_quota: int = 50
    used_today: int = 0
    cooldown_until: float | None = None
    last_request_at: float | None = None
    request_timestamps: list[float] = field(default_factory=list)

    def masked_id(self) -> str:
        k = self.key.strip()
        if len(k) <= 8:
            return "***"
        return f"{k[:4]}...{k[-4:]}"


def parse_keys_spec(spec: str) -> list[tuple[str, int]]:
    """Parse ``key1:50,key2:1000`` or single key without quota."""
    out: list[tuple[str, int]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            key, quota_s = part.rsplit(":", 1)
            try:
                quota = int(quota_s.strip())
            except ValueError:
                quota = 50
            out.append((key.strip(), max(1, quota)))
        else:
            out.append((part, 50))
    return out


class KeyPool:
    """Round-robin key selection with RPM throttle, daily quota, and 429 cooldown."""

    def __init__(
        self,
        *,
        keys: list[tuple[str, int]],
        rpm_limit: int = DEFAULT_RPM_LIMIT,
        cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS,
        timezone: str = "UTC",
    ) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one API key")
        self._entries = [KeyPoolEntry(key=k, daily_quota=q) for k, q in keys]
        self._rpm_limit = max(1, rpm_limit)
        self._cooldown_seconds = max(1.0, cooldown_seconds)
        self._tz = ZoneInfo(timezone)
        self._lock = Lock()
        self._cursor = 0
        self._last_reset_date: datetime | None = None

    @classmethod
    def from_env(cls, keys_spec: str, *, single_key: str | None = None, **kwargs: Any) -> KeyPool:
        parsed = parse_keys_spec(keys_spec) if keys_spec.strip() else []
        if not parsed and single_key and single_key.strip():
            parsed = [(single_key.strip(), 50)]
        if not parsed:
            raise ValueError("No OpenRouter keys configured (OPENROUTER_KEYS or OPENROUTER_API_KEY)")
        return cls(keys=parsed, **kwargs)

    def _maybe_reset_daily(self) -> None:
        now_local = datetime.now(self._tz)
        today = now_local.date()
        if self._last_reset_date is None or self._last_reset_date.date() != today:
            for e in self._entries:
                e.used_today = 0
            self._last_reset_date = now_local
            logger.info("key_pool_daily_reset date=%s keys=%d", today.isoformat(), len(self._entries))

    def _is_available(self, entry: KeyPoolEntry, now: float) -> bool:
        if entry.cooldown_until is not None and now < entry.cooldown_until:
            return False
        if entry.used_today >= entry.daily_quota:
            return False
        cutoff = now - 60.0
        recent = [t for t in entry.request_timestamps if t > cutoff]
        entry.request_timestamps = recent
        if len(recent) >= self._rpm_limit:
            return False
        return True

    def acquire(self) -> tuple[KeyPoolEntry, int]:
        """Return (entry, index) for next usable key or raise RuntimeError."""
        with self._lock:
            self._maybe_reset_daily()
            now = time.monotonic()
            n = len(self._entries)
            for offset in range(n):
                idx = (self._cursor + offset) % n
                entry = self._entries[idx]
                if self._is_available(entry, now):
                    self._cursor = (idx + 1) % n
                    entry.request_timestamps.append(now)
                    entry.last_request_at = now
                    return entry, idx
            raise RuntimeError("All OpenRouter keys exhausted (quota, cooldown, or RPM throttle)")

    def record_success(self, entry: KeyPoolEntry) -> None:
        with self._lock:
            entry.used_today += 1

    def record_rate_limit(self, entry: KeyPoolEntry) -> None:
        with self._lock:
            until = time.monotonic() + self._cooldown_seconds
            entry.cooldown_until = until
            logger.warning(
                "key_pool_cooldown key=%s until_in_s=%.0f",
                entry.masked_id(),
                self._cooldown_seconds,
            )

    def quota_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            self._maybe_reset_daily()
            now = time.monotonic()
            out: list[dict[str, Any]] = []
            for i, e in enumerate(self._entries):
                cooldown_left = None
                if e.cooldown_until is not None and now < e.cooldown_until:
                    cooldown_left = round(e.cooldown_until - now, 1)
                out.append(
                    {
                        "index": i,
                        "key_masked": e.masked_id(),
                        "daily_quota": e.daily_quota,
                        "used_today": e.used_today,
                        "remaining": max(0, e.daily_quota - e.used_today),
                        "cooldown_seconds_left": cooldown_left,
                    }
                )
            return out

    def next_midnight_utc_iso(self) -> str:
        now_local = datetime.now(self._tz)
        tomorrow = (now_local + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return tomorrow.astimezone(UTC).isoformat()
