"""Async OpenRouter API client with key pool and fallback."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator

import httpx

from gpthub_orchestrator.openrouter.fallback import is_retryable_status
from gpthub_orchestrator.openrouter.key_pool import KeyPool, KeyPoolEntry
from gpthub_orchestrator.openrouter.model_health import ModelHealthTracker
from gpthub_orchestrator.openrouter.model_stats import get_model_stats
from gpthub_orchestrator.settings import Settings

logger = logging.getLogger(__name__)

OPENROUTER_EXHAUSTED_MESSAGE_RU = (
    "Все бесплатные модели OpenRouter заняты или недоступны. "
    "Попробуйте через несколько минут или добавьте ещё один ключ в OPENROUTER_KEYS."
)


class OpenRouterExhaustedError(Exception):
    """All models and keys failed."""

    def __init__(
        self,
        attempts: list[dict[str, Any]],
        message: str = OPENROUTER_EXHAUSTED_MESSAGE_RU,
    ) -> None:
        self.attempts = attempts
        super().__init__(message)


class OpenRouterClient:
    """Direct OpenRouter chat completions with survival-engine fallback."""

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings
        self._base = settings.openrouter_api_base.rstrip("/")
        self._key_pool = KeyPool.from_env(
            settings.openrouter_keys,
            single_key=settings.openrouter_api_key,
            rpm_limit=settings.openrouter_rpm_limit,
            cooldown_seconds=settings.openrouter_key_cooldown_seconds,
            timezone=settings.openrouter_quota_timezone,
        )
        self._health = ModelHealthTracker(
            ban_after_failures=settings.openrouter_model_ban_after_429,
            ban_ttl_seconds=settings.openrouter_model_ban_ttl_seconds,
        )

    @property
    def key_pool(self) -> KeyPool:
        return self._key_pool

    @property
    def model_health(self) -> ModelHealthTracker:
        return self._health

    def filter_model_chain(self, model_chain: list[str]) -> list[str]:
        return self._health.filter_chain(model_chain)

    def _attribution_headers(self) -> dict[str, str]:
        return {
            "HTTP-Referer": self._settings.or_site_url,
            "X-Title": self._settings.or_app_name,
        }

    async def chat_completions(
        self,
        body: dict[str, Any],
        *,
        model_chain: list[str],
        catalog_section: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Non-stream completion with model-first then key rotation fallback."""
        chain = self.filter_model_chain(model_chain)
        attempts_log: list[dict[str, Any]] = []
        max_keys = len(self._key_pool._entries)
        keys_tried = 0
        max_total = self._settings.orchestrator_fallback_max_attempts * max(1, len(chain))

        while keys_tried < max_keys:
            try:
                entry, key_index = self._key_pool.acquire()
            except RuntimeError:
                break

            keys_tried += 1
            key_had_retryable = False

            for model in chain:
                if len(attempts_log) >= max_total:
                    break
                attempt_body = dict(body)
                attempt_body["model"] = model
                t0 = time.monotonic()
                status, payload, raw_text = await self._post_completion(attempt_body, entry)
                latency_ms = (time.monotonic() - t0) * 1000.0
                get_model_stats().record_attempt(
                    section=catalog_section,
                    slug=model,
                    success=status < 400,
                    status_code=status,
                    latency_ms=latency_ms,
                )
                log_entry: dict[str, Any] = {
                    "model": model,
                    "openrouter_model": model,
                    "key_index": key_index,
                    "key_masked": entry.masked_id(),
                    "status_code": status,
                }
                attempts_log.append(log_entry)

                if status < 400:
                    self._key_pool.record_success(entry)
                    self._health.record_success(model)
                    meta = self._build_meta(
                        model=model,
                        key_index=key_index,
                        entry=entry,
                        attempts=attempts_log,
                        success=True,
                    )
                    if isinstance(payload, dict):
                        return payload, meta
                    return {"error": {"message": raw_text}}, meta

                logger.warning(
                    "openrouter_attempt_failed model=%s key=%s status=%s",
                    model,
                    entry.masked_id(),
                    status,
                )
                if is_retryable_status(status):
                    key_had_retryable = True
                    self._health.record_failure(model, status_code=status)
                    continue
                break

            if key_had_retryable:
                self._key_pool.record_rate_limit(entry)
                continue
            break

        meta = self._build_meta(
            model=chain[-1] if chain else "",
            key_index=-1,
            entry=None,
            attempts=attempts_log,
            success=False,
        )
        raise OpenRouterExhaustedError(attempts_log)

    async def chat_completions_stream(
        self,
        body: dict[str, Any],
        *,
        model_chain: list[str],
        catalog_section: str | None = None,
    ) -> tuple[AsyncIterator[bytes], dict[str, Any]]:
        """Stream with model-first fallback (same key, then key rotation)."""
        chain = self.filter_model_chain(model_chain)
        if not chain:
            raise OpenRouterExhaustedError([], message="empty model chain for stream")

        attempts_log: list[dict[str, Any]] = []
        max_keys = len(self._key_pool._entries)
        keys_tried = 0
        stream_cap = min(
            self._settings.orchestrator_stream_fallback_max_attempts,
            self._settings.orchestrator_fallback_max_attempts,
        )
        max_total = stream_cap * max(1, len(chain))

        while keys_tried < max_keys:
            try:
                entry, key_index = self._key_pool.acquire()
            except RuntimeError:
                break

            keys_tried += 1
            key_had_retryable = False

            for model in chain:
                if len(attempts_log) >= max_total:
                    break
                attempt_body = dict(body)
                attempt_body["model"] = model
                attempt_body["stream"] = True
                url = f"{self._base}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {entry.key}",
                    "Content-Type": "application/json",
                    **self._attribution_headers(),
                }
                log_entry: dict[str, Any] = {
                    "model": model,
                    "openrouter_model": model,
                    "key_index": key_index,
                    "key_masked": entry.masked_id(),
                    "mode": "stream",
                }
                attempts_log.append(log_entry)

                req = self._http.build_request("POST", url, json=attempt_body, headers=headers)
                t0 = time.monotonic()
                resp = await self._http.send(req, stream=True)
                latency_ms = (time.monotonic() - t0) * 1000.0

                if resp.status_code >= 400:
                    raw = await resp.aread()
                    await resp.aclose()
                    preview = raw[:1200].decode("utf-8", errors="replace")
                    log_entry["status_code"] = resp.status_code
                    get_model_stats().record_attempt(
                        section=catalog_section,
                        slug=model,
                        success=False,
                        status_code=resp.status_code,
                        latency_ms=latency_ms,
                    )
                    logger.warning(
                        "openrouter_stream_attempt_failed model=%s status=%s",
                        model,
                        resp.status_code,
                    )
                    if is_retryable_status(resp.status_code):
                        key_had_retryable = True
                        self._health.record_failure(model, status_code=resp.status_code)
                        if resp.status_code == 429:
                            self._key_pool.record_rate_limit(entry)
                        continue
                    break

                self._key_pool.record_success(entry)
                self._health.record_success(model)
                get_model_stats().record_attempt(
                    section=catalog_section,
                    slug=model,
                    success=True,
                    status_code=resp.status_code,
                    latency_ms=latency_ms,
                )
                meta = self._build_meta(
                    model=model,
                    key_index=key_index,
                    entry=entry,
                    attempts=attempts_log,
                    success=True,
                )
                meta["mode"] = "stream_fallback"

                async def iterator(resp=resp, entry=entry, model=model) -> AsyncIterator[bytes]:
                    try:
                        async for chunk in resp.aiter_bytes():
                            yield chunk
                    finally:
                        await resp.aclose()

                return iterator(), meta

            if key_had_retryable:
                self._key_pool.record_rate_limit(entry)
                continue
            break

        meta = self._build_meta(
            model=chain[-1],
            key_index=-1,
            entry=None,
            attempts=attempts_log,
            success=False,
        )
        raise OpenRouterExhaustedError(attempts_log)

    async def _post_completion(
        self,
        body: dict[str, Any],
        entry: KeyPoolEntry,
    ) -> tuple[int, dict[str, Any] | None, str]:
        url = f"{self._base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {entry.key}",
            "Content-Type": "application/json",
            **self._attribution_headers(),
        }
        stream = bool(body.get("stream"))
        if stream:
            body = dict(body)
            body["stream"] = False
        try:
            resp = await self._http.post(url, json=body, headers=headers)
        except httpx.HTTPError as e:
            logger.exception("openrouter_http_error")
            return 502, None, str(e)
        text = resp.text
        payload: dict[str, Any] | None = None
        if "application/json" in resp.headers.get("content-type", ""):
            try:
                parsed = resp.json()
                if isinstance(parsed, dict):
                    payload = parsed
            except json.JSONDecodeError:
                pass
        return resp.status_code, payload, text

    def _build_meta(
        self,
        *,
        model: str,
        key_index: int,
        entry: KeyPoolEntry | None,
        attempts: list[dict[str, Any]],
        success: bool,
    ) -> dict[str, Any]:
        return {
            "openrouter_model": model,
            "key_index": key_index if key_index >= 0 else None,
            "key_masked": entry.masked_id() if entry else None,
            "attempts": attempts,
            "model_attempts": attempts,
            "quota_remaining": self._key_pool.quota_snapshot(),
            "catalog_version": self._settings.free_models_catalog_path or "packaged",
            "success": success,
        }

    async def health_check(self) -> bool:
        """GET /models with first available key."""
        try:
            entry, _ = self._key_pool.acquire()
        except RuntimeError:
            return False
        url = f"{self._base}/models"
        headers = {"Authorization": f"Bearer {entry.key}"}
        try:
            resp = await self._http.get(url, headers=headers, timeout=httpx.Timeout(10.0))
            return resp.status_code < 400
        except httpx.HTTPError:
            logger.exception("openrouter_health_check_failed")
            return False
