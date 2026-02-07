"""
Unified Cache System for V2
Handles caching of METAR data, geocoding, and other frequently accessed data
with TTL (time-to-live) expiration
"""

import time
import json
import logging
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict
from dataclasses import dataclass, field
from threading import Lock

logger = logging.getLogger("MissionGenerator.Cache")

@dataclass
class CacheEntry:
    """Single cache entry with expiration"""
    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    hits: int = 0

class UnifiedCache:
    """
    Thread-safe unified cache with TTL support
    Caches METAR, geocoding, and other data
    """

    # Default TTLs in seconds
    DEFAULT_TTL = {
        'metar': 1800,        # 30 minutes for METAR
        'geocoding': 86400,   # 24 hours for geocoding
        'airport': 86400,     # 24 hours for airport data
        'runway': 86400,      # 24 hours for runway data
        'weather_sim': 60,    # 1 minute for SimConnect weather
        'default': 300        # 5 minutes default
    }

    def __init__(self, cache_file: Optional[Path] = None, max_entries: int = 10000):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._cache_file = cache_file
        self._max_entries = max_entries
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

        if cache_file and cache_file.exists():
            self._load_from_disk()

    def get(self, key: str, category: str = 'default') -> Optional[Any]:
        """
        Get value from cache if exists and not expired

        Args:
            key: Cache key
            category: Category for stats tracking

        Returns:
            Cached value or None if not found/expired
        """
        cache_key = f"{category}:{key}"

        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats['misses'] += 1
                return None

            # Check expiration
            if time.time() > entry.expires_at:
                del self._cache[cache_key]
                self._stats['misses'] += 1
                return None

            entry.hits += 1
            self._stats['hits'] += 1
            return entry.value

    def set(self, key: str, value: Any, category: str = 'default', ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL

        Args:
            key: Cache key
            value: Value to cache
            category: Category for TTL lookup
            ttl: Custom TTL in seconds (overrides category default)
        """
        cache_key = f"{category}:{key}"

        if ttl is None:
            ttl = self.DEFAULT_TTL.get(category, self.DEFAULT_TTL['default'])

        expires_at = time.time() + ttl

        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()

            self._cache[cache_key] = CacheEntry(
                value=value,
                expires_at=expires_at
            )

    def delete(self, key: str, category: str = 'default') -> bool:
        """Delete a specific cache entry"""
        cache_key = f"{category}:{key}"

        with self._lock:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return True
            return False

    def clear_category(self, category: str) -> int:
        """Clear all entries in a category"""
        count = 0
        prefix = f"{category}:"

        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1

        logger.info(f"Cleared {count} entries from cache category '{category}'")
        return count

    def clear_all(self) -> None:
        """Clear entire cache"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove all expired entries"""
        count = 0
        now = time.time()

        with self._lock:
            keys_to_delete = [
                k for k, v in self._cache.items()
                if now > v.expires_at
            ]
            for key in keys_to_delete:
                del self._cache[key]
                count += 1

        if count > 0:
            logger.debug(f"Cleaned up {count} expired cache entries")

        return count

    def _evict_oldest(self) -> None:
        """Evict oldest entries when cache is full"""
        # Sort by creation time and remove oldest 10%
        entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].created_at
        )

        num_to_evict = max(1, len(entries) // 10)

        for key, _ in entries[:num_to_evict]:
            del self._cache[key]
            self._stats['evictions'] += 1

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self._lock:
            total = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0

            return {
                'entries': len(self._cache),
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'hit_rate': f"{hit_rate:.1f}%"
            }

    def _load_from_disk(self) -> None:
        """Load cache from disk file"""
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            now = time.time()
            loaded = 0

            for key, entry_data in data.items():
                if entry_data['expires_at'] > now:
                    self._cache[key] = CacheEntry(
                        value=entry_data['value'],
                        expires_at=entry_data['expires_at'],
                        created_at=entry_data.get('created_at', now)
                    )
                    loaded += 1

            logger.info(f"Loaded {loaded} cache entries from disk")
        except Exception as e:
            logger.warning(f"Could not load cache from disk: {e}")

    def save_to_disk(self) -> None:
        """Save cache to disk file"""
        if not self._cache_file:
            return

        try:
            data = {}
            now = time.time()

            with self._lock:
                for key, entry in self._cache.items():
                    if entry.expires_at > now:  # Only save non-expired
                        data[key] = {
                            'value': entry.value,
                            'expires_at': entry.expires_at,
                            'created_at': entry.created_at
                        }

            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f)

            logger.debug(f"Saved {len(data)} cache entries to disk")
        except Exception as e:
            logger.error(f"Could not save cache to disk: {e}")


# Global cache instance
_global_cache: Optional[UnifiedCache] = None

def get_cache() -> UnifiedCache:
    """Get or create global cache instance"""
    global _global_cache

    if _global_cache is None:
        cache_file = Path(__file__).parent.parent / "cache_data.json"
        _global_cache = UnifiedCache(cache_file=cache_file)

    return _global_cache


def cached(category: str = 'default', ttl: Optional[int] = None):
    """
    Decorator for caching function results

    Usage:
        @cached(category='metar', ttl=1800)
        def fetch_metar(icao: str) -> str:
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            key_parts.extend(str(a) for a in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()

            cache = get_cache()

            # Try to get from cache
            result = cache.get(cache_key, category)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, category, ttl)

            return result

        return wrapper
    return decorator
