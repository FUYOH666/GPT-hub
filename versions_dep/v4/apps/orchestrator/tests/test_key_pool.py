import time

import pytest

from gpthub_orchestrator.openrouter.key_pool import KeyPool, parse_keys_spec


def test_parse_keys_spec_with_quotas():
    parsed = parse_keys_spec("key-a:50,key-b:1000")
    assert parsed == [("key-a", 50), ("key-b", 1000)]


def test_key_pool_acquire_and_success():
    pool = KeyPool(keys=[("k1", 50), ("k2", 50)], rpm_limit=100)
    e1, i1 = pool.acquire()
    pool.record_success(e1)
    assert i1 == 0
    snap = pool.quota_snapshot()
    assert snap[0]["used_today"] == 1
    assert snap[0]["remaining"] == 49


def test_key_pool_rate_limit_cooldown():
    pool = KeyPool(keys=[("k1", 50)], rpm_limit=100, cooldown_seconds=60)
    entry, _ = pool.acquire()
    pool.record_rate_limit(entry)
    with pytest.raises(RuntimeError, match="exhausted"):
        pool.acquire()


def test_key_pool_rpm_throttle():
    pool = KeyPool(keys=[("k1", 50)], rpm_limit=2)
    pool.acquire()
    pool.acquire()
    with pytest.raises(RuntimeError, match="exhausted"):
        pool.acquire()
    # After 61s window, should work again
    entry = pool._entries[0]
    entry.request_timestamps = [time.monotonic() - 61]
    e, _ = pool.acquire()
    assert e.key == "k1"


def test_key_pool_daily_quota_exhausted():
    pool = KeyPool(keys=[("k1", 2)], rpm_limit=100)
    for _ in range(2):
        e, _ = pool.acquire()
        pool.record_success(e)
    with pytest.raises(RuntimeError, match="exhausted"):
        pool.acquire()
