"""Tests for runtime model health bans."""

from gpthub_orchestrator.openrouter.model_health import ModelHealthTracker


def test_ban_after_n_429s():
    h = ModelHealthTracker(ban_after_failures=2, ban_ttl_seconds=3600)
    assert not h.is_banned("a:free")
    h.record_failure("a:free", status_code=429)
    assert not h.is_banned("a:free")
    h.record_failure("a:free", status_code=429)
    assert h.is_banned("a:free")


def test_filter_chain_skips_banned():
    h = ModelHealthTracker(ban_after_failures=1, ban_ttl_seconds=3600)
    h.record_failure("a:free", status_code=429)
    filtered = h.filter_chain(["a:free", "b:free"])
    assert filtered == ["b:free"]


def test_success_clears_ban():
    h = ModelHealthTracker(ban_after_failures=1, ban_ttl_seconds=3600)
    h.record_failure("a:free", status_code=429)
    assert h.is_banned("a:free")
    h.record_success("a:free")
    assert not h.is_banned("a:free")
