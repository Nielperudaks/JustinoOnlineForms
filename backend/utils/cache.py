import os
import time
from typing import Any, Callable, Hashable, Optional, Tuple


def get_ttl_seconds(env_name: str, default: int) -> int:
    try:
        return int(os.environ.get(env_name, default))
    except (TypeError, ValueError):
        return default


class TTLCache:
    def __init__(self, default_ttl_seconds: int = 30, now: Callable[[], float] = time.monotonic):
        self.default_ttl_seconds = default_ttl_seconds
        self.now = now
        self._items: dict[Tuple[str, Tuple[Hashable, ...]], tuple[float, Any]] = {}

    async def get_or_set(self, namespace: str, key: Tuple[Hashable, ...], factory, ttl_seconds: Optional[int] = None):
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        if ttl <= 0:
            return await factory()

        cache_key = (namespace, key)
        current_time = self.now()
        cached = self._items.get(cache_key)
        if cached and cached[0] > current_time:
            return cached[1]

        value = await factory()
        self._items[cache_key] = (current_time + ttl, value)
        return value

    def invalidate(self, namespace: Optional[str] = None):
        if namespace is None:
            self._items.clear()
            return

        for cache_key in list(self._items):
            if cache_key[0] == namespace:
                self._items.pop(cache_key, None)


metadata_cache = TTLCache(get_ttl_seconds("METADATA_CACHE_TTL_SECONDS", 60))
stats_cache = TTLCache(get_ttl_seconds("STATS_CACHE_TTL_SECONDS", 10))


def invalidate_metadata_cache():
    metadata_cache.invalidate()


def invalidate_stats_cache():
    stats_cache.invalidate()
