"""
In-memory TTL cache for investigation results.

Designed to be easily replaceable with Redis in the future.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from loguru import logger
from app.core.config import settings


class InvestigationCache:
    """
    Simple thread-safe in-memory cache with TTL support.
    """

    def __init__(self, ttl_seconds: int = 300) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        logger.info(
            "Investigation cache initialized (TTL={} seconds)",
            settings.INVESTIGATION_CACHE_TTL,
        )

    def get(self, key: str) -> Any | None:
        """
        Retrieve a cached value if it exists and has not expired.
        """
        with self._lock:
            item = self._cache.get(key)

            if item is None:
                self._misses += 1
                logger.info("Cache MISS: {}", key)
                return None

            expires_at, value = item

            if datetime.utcnow() > expires_at:
                logger.info("Cache EXPIRED: {}", key)
                del self._cache[key]
                return None
            
            self._hits += 1
            logger.info("Cache HIT: {}", key)
            return value

    def set(self, key: str, value: Any) -> None:
        """
        Store a value in the cache.
        """
        with self._lock:
            expires_at = datetime.utcnow() + self._ttl
            self._cache[key] = (expires_at, value)

            logger.debug("Cached investigation: {}", key)

    def invalidate(self, key: str) -> None:
        """
        Remove a single cached entry.
        """
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """
        Clear the entire cache.
        """
        with self._lock:
            self._cache.clear()

            logger.info("Investigation cache cleared.")

    def stats(self) -> dict[str, int]:
        return {
            "hits": self._hits,
            "misses": self._misses,
        }
# Shared singleton cache instance

investigation_cache = InvestigationCache(
    ttl_seconds=settings.INVESTIGATION_CACHE_TTL,
)