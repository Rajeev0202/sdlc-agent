"""Persistent LLM response cache with Redis backend (in-memory fallback).

Cache key: sha256(model + system + user)
TTL: 24 hours by default (configurable via LLM_CACHE_TTL env var)

Backends (auto-selected):
1. Redis  — if REDIS_URL is set AND `redis` package is installed
2. Memory — fallback (process-local, lost on restart)

Stats are tracked across both backends.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)


# Default 24-hour TTL for cached responses
DEFAULT_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL", "86400"))


class _MemoryBackend:
    """Simple in-memory cache with lock for thread safety."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, value: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        # In-memory has no TTL enforcement; OK for short demos
        with self._lock:
            self._store[key] = value

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    @property
    def backend_name(self) -> str:
        return "memory"


class _RedisBackend:
    """Redis-backed persistent cache."""

    KEY_PREFIX = "sdlc:llm:"

    def __init__(self, redis_url: str):
        try:
            import redis  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "redis package not installed. Run: pip install redis>=5.0"
            ) from e

        self._client = redis.from_url(redis_url, decode_responses=True)
        # Validate connection
        self._client.ping()
        logger.info(f"[LLM Cache] Connected to Redis at {redis_url}")

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(self.KEY_PREFIX + key)
        except Exception as e:
            logger.warning(f"[LLM Cache] Redis GET failed: {e}")
            return None

    def set(self, key: str, value: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        try:
            self._client.setex(self.KEY_PREFIX + key, ttl_seconds, value)
        except Exception as e:
            logger.warning(f"[LLM Cache] Redis SET failed: {e}")

    def clear(self) -> None:
        try:
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=f"{self.KEY_PREFIX}*", count=500)
                if keys:
                    self._client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.warning(f"[LLM Cache] Redis clear failed: {e}")

    def size(self) -> int:
        try:
            count = 0
            cursor = 0
            while True:
                cursor, keys = self._client.scan(cursor, match=f"{self.KEY_PREFIX}*", count=500)
                count += len(keys)
                if cursor == 0:
                    break
            return count
        except Exception:
            return -1

    @property
    def backend_name(self) -> str:
        return "redis"


class LLMCache:
    """Unified cache façade with Redis backend, falling back to memory."""

    def __init__(self):
        self._stats = {"hits": 0, "misses": 0, "writes": 0}
        self._backend = self._init_backend()
        logger.info(f"[LLM Cache] Backend: {self._backend.backend_name}")

    def _init_backend(self):
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return _MemoryBackend()

        try:
            return _RedisBackend(redis_url)
        except Exception as e:
            logger.warning(
                f"[LLM Cache] Redis init failed ({e}); falling back to in-memory cache"
            )
            return _MemoryBackend()

    @staticmethod
    def make_key(system: str, user: str, model: str = "default") -> str:
        h = hashlib.sha256()
        h.update(model.encode("utf-8"))
        h.update(b"\x1e")
        h.update(system.encode("utf-8"))
        h.update(b"\x1e")
        h.update(user.encode("utf-8"))
        return h.hexdigest()

    def get(self, key: str) -> Optional[str]:
        value = self._backend.get(key)
        if value is not None:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
        return value

    def set(self, key: str, value: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._backend.set(key, value, ttl_seconds)
        self._stats["writes"] += 1

    def clear(self) -> None:
        self._backend.clear()

    def stats(self) -> dict:
        return {
            **self._stats,
            "backend": self._backend.backend_name,
            "size": self._backend.size(),
            "ttl_seconds": DEFAULT_TTL_SECONDS,
        }


# Singleton cache used by anthropic_client
_cache: Optional[LLMCache] = None


def get_cache() -> LLMCache:
    """Return the process-wide cache singleton (lazy-init)."""
    global _cache
    if _cache is None:
        _cache = LLMCache()
    return _cache
