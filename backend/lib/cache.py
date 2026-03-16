"""
Redis-backed response cache for the FINTEL API.

Usage
-----
from lib.cache import get_cache, set_cache, invalidate_prefix

# In a route handler:
cached = get_cache("leaderboard:tech:composite_score")
if cached is not None:
    return cached
result = compute_result()
set_cache("leaderboard:tech:composite_score", result, ttl=300)
return result

Cache key conventions
---------------------
  leaderboard:<sector>:<sort_by>          TTL 5 min
  composite_scores:<sector>:<min_score>   TTL 5 min
  dashboard                               TTL 60 sec
  company_summary:<ticker>                TTL 5 min
  sector_heatmap:<days>                   TTL 10 min
"""
import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _get_client():
    """Lazily initialise a Redis client, returning None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://redis:6379")
        _redis_client = redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()
        logger.info("Redis cache connected")
    except Exception as e:
        logger.warning(f"Redis unavailable — caching disabled: {e}")
        _redis_client = None
    return _redis_client


def get_cache(key: str) -> Optional[Any]:
    """Return the deserialized cached value, or None on miss / Redis unavailable."""
    r = _get_client()
    if r is None:
        return None
    try:
        raw = r.get(f"fintel:{key}")
        return json.loads(raw) if raw is not None else None
    except Exception as e:
        logger.debug(f"Cache get error [{key}]: {e}")
        return None


def set_cache(key: str, value: Any, ttl: int = 300) -> None:
    """Serialize and store `value` with the given TTL (seconds)."""
    r = _get_client()
    if r is None:
        return
    try:
        r.setex(f"fintel:{key}", ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"Cache set error [{key}]: {e}")


def invalidate_prefix(prefix: str) -> int:
    """Delete all keys matching `fintel:<prefix>*`. Returns count deleted."""
    r = _get_client()
    if r is None:
        return 0
    try:
        keys = r.keys(f"fintel:{prefix}*")
        if keys:
            return r.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache invalidate error [{prefix}]: {e}")
        return 0
