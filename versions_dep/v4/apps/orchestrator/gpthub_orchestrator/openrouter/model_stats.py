"""In-memory EMA stats and bandit-style chain resort."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from gpthub_orchestrator.openrouter.catalog import FreeModelsCatalog, install_runtime_catalog
from gpthub_orchestrator.openrouter.routing_manifest import set_routing_source

logger = logging.getLogger(__name__)

CATALOG_SECTIONS = ("text_fast", "text_code", "text_doc", "vision")


@dataclass
class SlugStats:
    success_ema: float = 0.0
    latency_ema_ms: float = 0.0
    rate_429_ema: float = 0.0
    rate_400_ema: float = 0.0
    samples: int = 0
    last_updated: float = field(default_factory=time.monotonic)


class ModelStatsTracker:
    """EMA per catalog section + slug; optional periodic resort."""

    def __init__(
        self,
        *,
        ema_alpha: float = 0.15,
        min_samples_for_resort: int = 5,
        w_success: float = 2.0,
        w_429: float = 3.0,
        w_400: float = 1.5,
        w_latency: float = 0.002,
    ) -> None:
        self._alpha = max(0.01, min(1.0, ema_alpha))
        self._min_samples = max(1, min_samples_for_resort)
        self._w_success = w_success
        self._w_429 = w_429
        self._w_400 = w_400
        self._w_latency = w_latency
        self._stats: dict[tuple[str, str], SlugStats] = {}
        self._heuristic_prior: dict[tuple[str, str], float] = {}
        self._last_resort_at: float | None = None
        self._last_resort_sections: dict[str, list[str]] = {}

    def set_heuristic_prior(self, section: str, chain: list[str]) -> None:
        for i, slug in enumerate(chain):
            self._heuristic_prior[(section, slug)] = float(len(chain) - i)

    def record_attempt(
        self,
        *,
        section: str | None,
        slug: str,
        success: bool,
        status_code: int,
        latency_ms: float,
    ) -> None:
        if not section or not slug.strip():
            return
        key = (section, slug.strip())
        st = self._stats.get(key)
        if st is None:
            st = SlugStats()
            self._stats[key] = st
        a = self._alpha
        st.samples += 1
        st.success_ema = (1 - a) * st.success_ema + a * (1.0 if success else 0.0)
        st.latency_ema_ms = (1 - a) * st.latency_ema_ms + a * max(0.0, latency_ms)
        is_429 = 1.0 if status_code == 429 else 0.0
        is_400 = 1.0 if status_code in (400, 422) else 0.0
        st.rate_429_ema = (1 - a) * st.rate_429_ema + a * is_429
        st.rate_400_ema = (1 - a) * st.rate_400_ema + a * is_400
        st.last_updated = time.monotonic()

    def bandit_score(self, section: str, slug: str) -> float:
        st = self._stats.get((section, slug))
        prior = self._heuristic_prior.get((section, slug), 0.0)
        if st is None or st.samples < self._min_samples:
            return prior
        return (
            self._w_success * st.success_ema
            - self._w_429 * st.rate_429_ema
            - self._w_400 * st.rate_400_ema
            - self._w_latency * st.latency_ema_ms
            + prior * 0.1
        )

    def resort_catalog(
        self,
        catalog: FreeModelsCatalog,
        *,
        banned: set[str] | None = None,
    ) -> FreeModelsCatalog | None:
        """Reorder chains by bandit score; at most one position swap per section."""
        banned = banned or set()
        updates: dict[str, list[str]] = {}
        changed = False
        for section in CATALOG_SECTIONS:
            chain = list(getattr(catalog, section))
            if len(chain) < 2:
                continue
            available = [s for s in chain if s not in banned]
            if len(available) < 2:
                continue
            scored = sorted(
                available,
                key=lambda s: (-self.bandit_score(section, s), s),
            )
            if scored[0] == chain[0]:
                continue
            new_chain = list(chain)
            try:
                idx_best = new_chain.index(scored[0])
                new_chain[0], new_chain[idx_best] = new_chain[idx_best], new_chain[0]
            except ValueError:
                continue
            if new_chain != chain:
                updates[section] = new_chain
                changed = True
        if not changed:
            return None
        updated = catalog.model_copy(update=updates)
        if "text_fast" in updates:
            updated = updated.model_copy(update={"fallback": updates["text_fast"][:1]})
        install_runtime_catalog(updated)
        set_routing_source("bandit")
        self._last_resort_at = time.monotonic()
        self._last_resort_sections = {k: list(v) for k, v in updates.items()}
        logger.info("bandit_resort_applied sections=%s", list(updates.keys()))
        return updated

    def snapshot(self) -> dict[str, Any]:
        by_section: dict[str, list[dict[str, Any]]] = {s: [] for s in CATALOG_SECTIONS}
        for (section, slug), st in sorted(self._stats.items()):
            by_section.setdefault(section, []).append(
                {
                    "slug": slug,
                    "samples": st.samples,
                    "success_ema": round(st.success_ema, 4),
                    "latency_ema_ms": round(st.latency_ema_ms, 2),
                    "rate_429_ema": round(st.rate_429_ema, 4),
                    "rate_400_ema": round(st.rate_400_ema, 4),
                    "bandit_score": round(self.bandit_score(section, slug), 4),
                }
            )
        return {
            "min_samples_for_resort": self._min_samples,
            "last_resort_at_monotonic": self._last_resort_at,
            "last_resort_sections": self._last_resort_sections,
            "by_section": by_section,
        }


_global_stats: ModelStatsTracker | None = None


def get_model_stats() -> ModelStatsTracker:
    global _global_stats
    if _global_stats is None:
        _global_stats = ModelStatsTracker()
    return _global_stats


def configure_model_stats(*, min_samples_for_resort: int = 5) -> ModelStatsTracker:
    global _global_stats
    _global_stats = ModelStatsTracker(min_samples_for_resort=min_samples_for_resort)
    return _global_stats


def reset_model_stats() -> None:
    global _global_stats
    _global_stats = None
