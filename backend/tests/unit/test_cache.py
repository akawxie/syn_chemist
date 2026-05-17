"""SQLite cache behavior."""
from __future__ import annotations

import pytest

from app.cache import cache_get, cache_set, cached


def test_cache_set_and_get_roundtrip():
    cache_set("ns", {"k": 1}, {"v": 42})
    assert cache_get("ns", {"k": 1}) == {"v": 42}
    assert cache_get("ns", {"k": 2}) is None


def test_cache_overwrite():
    cache_set("ns", "key", {"v": 1})
    cache_set("ns", "key", {"v": 2})
    assert cache_get("ns", "key") == {"v": 2}


@pytest.mark.asyncio
async def test_cached_decorator_avoids_recomputation():
    counter = {"n": 0}

    @cached("test_ns")
    async def slow(x: int) -> int:
        counter["n"] += 1
        return x * 2

    assert await slow(3) == 6
    assert await slow(3) == 6  # second call hits cache
    assert counter["n"] == 1
    assert await slow(4) == 8
    assert counter["n"] == 2
