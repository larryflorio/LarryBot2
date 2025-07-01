"""
High-performance caching utilities for LarryBot2.

Provides query result caching, TTL-based invalidation, and memory-efficient storage
for frequently accessed data like task lists, analytics, and client information.
"""

import time
import asyncio
import hashlib
import json
import logging
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, List
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import RLock

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class CacheEntry(Generic[T]):
    """Represents a cached entry with TTL and metadata."""
    value: T
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0  # 5 minutes default
    
    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return time.time() - self.created_at > self.ttl_seconds
    
    def is_stale(self, stale_threshold: float = 0.8) -> bool:
        """Check if entry is stale (approaching expiration)."""
        age = time.time() - self.created_at
        return age > (self.ttl_seconds * stale_threshold)
    
    def access(self) -> T:
        """Access the cached value and update access statistics."""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value


class QueryCache:
    """
    High-performance query result cache with TTL, LRU eviction, and analytics.
    
    Features:
    - TTL-based expiration
    - LRU eviction when memory limits reached
    - Access statistics for optimization
    - Automatic cache warming for frequently accessed data
    - Thread-safe operations
    """
    
    def __init__(self, max_entries: int = 500, default_ttl: float = 300.0):
        self._cache: Dict[str, CacheEntry] = {}
        self._access_order: List[str] = []  # For LRU tracking
        self._max_entries = max_entries
        self._default_ttl = default_ttl
        self._lock = RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        logger.info(f"QueryCache initialized: max_entries={max_entries}, default_ttl={default_ttl}s")
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate a unique cache key from function name and arguments."""
        # Create a deterministic string representation
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': {k: v for k, v in sorted(kwargs.items())}
        }
        
        # Use hash for efficiency with large arguments
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache, handling expiration and LRU."""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None
            
            entry = self._cache[key]
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats['expirations'] += 1
                self._stats['misses'] += 1
                return None
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
            
            self._stats['hits'] += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set a value in cache with optional TTL override."""
        with self._lock:
            # Use provided TTL or default
            ttl = ttl or self._default_ttl
            
            # Create cache entry
            entry = CacheEntry(value=value, ttl_seconds=ttl)
            
            # Evict if at capacity
            if len(self._cache) >= self._max_entries and key not in self._cache:
                self._evict_lru()
            
            # Store entry
            self._cache[key] = entry
            
            # Update LRU order
            if key in self._access_order:
                self._access_order.remove(key)
            self._access_order.append(key)
    
    def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._access_order:
            return
        
        # Remove oldest entries
        evict_count = max(1, len(self._cache) // 10)  # Evict 10% when full
        for _ in range(evict_count):
            if self._access_order:
                lru_key = self._access_order.pop(0)
                if lru_key in self._cache:
                    del self._cache[lru_key]
                    self._stats['evictions'] += 1
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache entry."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all cache entries matching a pattern."""
        with self._lock:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'entries': len(self._cache),
                'max_entries': self._max_entries,
                'hit_rate': f"{hit_rate:.1f}%",
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'memory_usage': f"{len(self._cache) / self._max_entries * 100:.1f}%"
            }
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries and return count."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() 
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                self._stats['expirations'] += 1
            
            return len(expired_keys)


# Global cache instance
_global_cache = QueryCache(max_entries=1000, default_ttl=300.0)


def cached(ttl: float = 300.0, invalidate_on: Optional[List[str]] = None):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl: Time to live in seconds
        invalidate_on: List of cache key patterns to invalidate when this function is called
    
    Example:
        @cached(ttl=120.0, invalidate_on=['task_list'])
        def get_task_count():
            return expensive_query()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _global_cache._generate_key(func.__name__, args, kwargs)
            
            # Try to get from cache
            cached_result = _global_cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_result
            
            # Execute function and cache result
            logger.debug(f"Cache miss for {func.__name__}, executing...")
            result = func(*args, **kwargs)
            _global_cache.set(cache_key, result, ttl)
            
            # Invalidate related cache entries if specified
            if invalidate_on:
                for pattern in invalidate_on:
                    invalidated = _global_cache.invalidate_pattern(pattern)
                    if invalidated > 0:
                        logger.debug(f"Invalidated {invalidated} cache entries matching '{pattern}'")
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(pattern: str) -> int:
    """Invalidate cache entries matching a pattern."""
    return _global_cache.invalidate_pattern(pattern)


def cache_stats() -> Dict[str, Any]:
    """Get global cache statistics."""
    return _global_cache.get_stats()


def cache_clear() -> None:
    """Clear the global cache."""
    _global_cache.clear()


async def cache_cleanup_task():
    """
    Background task for cache maintenance.
    
    This performs one cleanup cycle without sleeping. The task manager
    handles the periodic scheduling and shutdown signaling.
    """
    try:
        expired_count = _global_cache.cleanup_expired()
        if expired_count > 0:
            logger.info(f"Cache cleanup: removed {expired_count} expired entries")
        
        # Log stats periodically
        stats = _global_cache.get_stats()
        if stats['entries'] > 0:
            logger.debug(f"Cache stats: {stats}")
        
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")
    
    # No sleep - the task manager handles scheduling 