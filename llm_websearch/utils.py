"""Utility functions for llm_websearch, including async rate limiting and caching helpers."""

import os
import hashlib
import logging
import json
import asyncio 
from typing import Optional, Any, Union, Dict, List, Type
from datetime import timedelta

try: 
    from diskcache import Cache
except ImportError:
    Cache = None
    print("Warning: diskcache not installed. Caching will be disabled.")

try: 
    from aiolimiter import AsyncLimiter
except ImportError:
    AsyncLimiter = None # type: ignore
    print("Warning: aiolimiter not installed. Rate limiting disabled.")

try: 
    from .config import settings
except ImportError: 
    # Fallback settings if config fails to load during import
    class MockSettings: 
        cache_dir=os.path.join(os.path.expanduser("~"),".cache","llm_websearch_fallback")
        cache_ttl_seconds=3600
        cache_enabled=False
    settings = MockSettings()
    print("Warning: Using fallback settings for utils.")

logger = logging.getLogger(__name__)

# --- Cache Setup ---
# Attempt to configure cache based on settings
CACHE_DIR: str = getattr(settings, 'cache_dir', os.path.join(os.path.expanduser("~"), ".cache", "llm_websearch_fb"))
CACHE_TTL_SECONDS: int = getattr(settings, 'cache_ttl_seconds', 3600)
CACHE_ENABLED: bool = getattr(settings, 'cache_enabled', False) and (Cache is not None)
cache: Optional[Cache] = None
if CACHE_ENABLED:
    try: 
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache = Cache(CACHE_DIR)
        logger.info(f"Disk cache initialized: {CACHE_DIR} (TTL: {CACHE_TTL_SECONDS}s)")
    except Exception as e: 
        logger.error(f"Failed cache init {CACHE_DIR}: {e}")
        cache = None
else:
    logger.info("Disk cache disabled.")

def _cache_key(prefix: str, *args: Any) -> str:
    """Create a deterministic cache key (MD5 hash) from various arguments."""
    hasher = hashlib.md5(prefix.encode('utf-8'))
    for arg in args:
        try: 
            # Sort complex types for consistency
            s = json.dumps(arg, sort_keys=True, default=str).encode('utf-8')
        except TypeError: 
            s = str(arg).encode('utf-8') 
        hasher.update(s)
    return hasher.hexdigest()

# --- Async Rate Limiting --- 
_limiters: Dict[str, Any] = {}
_limiter_lock = asyncio.Lock()

class _DummyLimiter:
    """A no-op async context manager if aiolimiter is not installed."""
    async def acquire(self):
        """No-op acquire."""
        pass
    async def __aenter__(self):
        """No-op enter."""
        return self
    async def __aexit__(self, exc_type, exc, tb):
        """No-op exit."""
        pass

async def get_limiter(key: str, rate: Optional[float]=None, period: float = 1.0) -> Union[AsyncLimiter, _DummyLimiter]:
    """Gets or creates an AsyncLimiter (or a dummy) for a given key.

    Uses settings (e.g., 'google_search_rate') if rate is not provided.
    """
    global _limiters
    if AsyncLimiter is None:
         if key not in _limiters:
             logger.warning(f"aiolimiter missing, dummy limiter for '{key}'.")
             _limiters[key] = _DummyLimiter()
         return _limiters[key]
         
    async with _limiter_lock:
        if key not in _limiters:
            if rate is None:
                 setting_key=f"{key}_rate"
                 rate = getattr(settings, setting_key, 10.0)
                 logger.info(f"Rate limit for '{key}' from '{setting_key}'/default: {rate}/s")
            
            if rate <= 0: 
                 logger.warning(f"Rate limiter '{key}' <= 0 ({rate}), using 1/s.")
                 rate = 1.0
                 
            logger.info(f"Creating aiolimiter '{key}' rate {rate}/{period}s")
            _limiters[key] = AsyncLimiter(rate, period)
        return _limiters[key]
