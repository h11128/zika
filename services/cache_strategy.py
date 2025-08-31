"""
Enhanced Cache Strategy Implementation.
Provides comprehensive caching with TTL, LRU eviction, observability, and multi-level cache management.
"""

import time
import threading
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import weakref
from collections import OrderedDict

from core.feature_flags import get_feature_flag
from services.observability import record_cache_hit, record_cache_miss, record_error

T = TypeVar('T')


class CacheLevel(Enum):
    """Cache levels with different characteristics."""
    SESSION = "session"      # Short-lived, user session data
    PREVIEW = "preview"      # Medium-lived, preview rendering cache
    EXPORT = "export"        # Long-lived, export generation cache
    PERSISTENT = "persistent"  # Very long-lived, cross-session data


@dataclass
class CachePolicy:
    """Cache policy configuration."""
    max_entries: int = 100
    max_size_bytes: int = 10 * 1024 * 1024  # 10MB
    ttl_seconds: int = 3600  # 1 hour
    enable_lru: bool = True
    enable_monitoring: bool = True
    cleanup_interval_seconds: int = 300  # 5 minutes
    
    # Level-specific policies
    @classmethod
    def for_level(cls, level: CacheLevel) -> 'CachePolicy':
        """Get policy for specific cache level."""
        policies = {
            CacheLevel.SESSION: cls(
                max_entries=50,
                max_size_bytes=5 * 1024 * 1024,  # 5MB
                ttl_seconds=1800,  # 30 minutes
                cleanup_interval_seconds=180  # 3 minutes
            ),
            CacheLevel.PREVIEW: cls(
                max_entries=100,
                max_size_bytes=20 * 1024 * 1024,  # 20MB
                ttl_seconds=3600,  # 1 hour
                cleanup_interval_seconds=300  # 5 minutes
            ),
            CacheLevel.EXPORT: cls(
                max_entries=200,
                max_size_bytes=50 * 1024 * 1024,  # 50MB
                ttl_seconds=7200,  # 2 hours
                cleanup_interval_seconds=600  # 10 minutes
            ),
            CacheLevel.PERSISTENT: cls(
                max_entries=500,
                max_size_bytes=100 * 1024 * 1024,  # 100MB
                ttl_seconds=86400,  # 24 hours
                cleanup_interval_seconds=3600  # 1 hour
            )
        }
        return policies.get(level, cls())


@dataclass
class CacheEntry(Generic[T]):
    """Enhanced cache entry with comprehensive metadata."""
    value: T
    key: str
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0
    tags: Dict[str, str] = field(default_factory=dict)
    
    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = time.time()
        self.access_count += 1
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry is expired."""
        return time.time() - self.created_at > ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age in seconds."""
        return time.time() - self.created_at


@dataclass
class CacheMetrics:
    """Comprehensive cache metrics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0
    cleanup_runs: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    @property
    def miss_rate(self) -> float:
        """Calculate miss rate percentage."""
        total = self.hits + self.misses
        return (self.misses / total * 100) if total > 0 else 0.0


class StrategyCache(Generic[T]):
    """Enhanced cache implementation with comprehensive strategy support."""
    
    def __init__(self, name: str, level: CacheLevel, policy: Optional[CachePolicy] = None):
        self.name = name
        self.level = level
        self.policy = policy or CachePolicy.for_level(level)
        
        # Use OrderedDict for LRU support
        self._entries: OrderedDict[str, CacheEntry[T]] = OrderedDict()
        self._metrics = CacheMetrics()
        self._lock = threading.RLock()
        
        # Cleanup scheduling
        self._last_cleanup = time.time()
        self._cleanup_callbacks: List[Callable[[], None]] = []
        
        # Monitoring
        self._enable_monitoring = self.policy.enable_monitoring and get_feature_flag('cache_monitoring', True)
        
    def get(self, key: str) -> Optional[T]:
        """Get value from cache with comprehensive tracking."""
        with self._lock:
            if key not in self._entries:
                self._record_miss(key)
                return None
            
            entry = self._entries[key]
            
            # Check expiration
            if entry.is_expired(self.policy.ttl_seconds):
                self._remove_entry(key, reason="expired")
                self._metrics.expirations += 1
                self._record_miss(key)
                return None
            
            # Update access info and move to end (LRU)
            entry.touch()
            if self.policy.enable_lru:
                self._entries.move_to_end(key)
            
            self._record_hit(key)
            return entry.value
    
    def set(self, key: str, value: T, tags: Optional[Dict[str, str]] = None) -> bool:
        """Set value in cache with capacity management."""
        with self._lock:
            # Estimate size
            size_bytes = self._estimate_size(value)
            
            # Check if single item exceeds policy
            if size_bytes > self.policy.max_size_bytes:
                if self._enable_monitoring:
                    record_error("cache_oversized_item", f"Item too large for cache {self.name}")
                return False
            
            # Ensure capacity
            if not self._ensure_capacity(size_bytes):
                return False
            
            # Remove existing entry if present
            if key in self._entries:
                self._remove_entry(key, reason="replaced")
            
            # Create new entry
            entry = CacheEntry(
                value=value,
                key=key,
                created_at=time.time(),
                last_accessed=time.time(),
                size_bytes=size_bytes,
                tags=tags or {}
            )
            
            # Add to cache
            self._entries[key] = entry
            self._metrics.total_size_bytes += size_bytes
            self._metrics.entry_count += 1
            
            # Schedule cleanup if needed
            self._maybe_cleanup()
            
            return True
    
    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        with self._lock:
            if key in self._entries:
                self._remove_entry(key, reason="invalidated")
                return True
            return False
    
    def invalidate_by_tags(self, tags: Dict[str, str]) -> int:
        """Invalidate entries matching all specified tags."""
        with self._lock:
            keys_to_remove = []
            for key, entry in self._entries.items():
                if all(entry.tags.get(tag_key) == tag_value for tag_key, tag_value in tags.items()):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_entry(key, reason="tag_invalidation")
            
            return len(keys_to_remove)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._entries.clear()
            self._metrics = CacheMetrics()
    
    def cleanup(self) -> int:
        """Manual cleanup of expired entries."""
        with self._lock:
            expired_keys = []
            current_time = time.time()
            
            for key, entry in self._entries.items():
                if entry.is_expired(self.policy.ttl_seconds):
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_entry(key, reason="cleanup_expired")
            
            self._metrics.cleanup_runs += 1
            self._last_cleanup = current_time
            
            # Run cleanup callbacks
            for callback in self._cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    if self._enable_monitoring:
                        record_error("cache_cleanup_callback", str(e))
            
            return len(expired_keys)
    
    def get_metrics(self) -> CacheMetrics:
        """Get cache metrics."""
        with self._lock:
            return CacheMetrics(
                hits=self._metrics.hits,
                misses=self._metrics.misses,
                evictions=self._metrics.evictions,
                expirations=self._metrics.expirations,
                total_size_bytes=self._metrics.total_size_bytes,
                entry_count=self._metrics.entry_count,
                cleanup_runs=self._metrics.cleanup_runs
            )
    
    def get_info(self) -> Dict[str, Any]:
        """Get comprehensive cache information."""
        with self._lock:
            metrics = self.get_metrics()
            return {
                'name': self.name,
                'level': self.level.value,
                'policy': {
                    'max_entries': self.policy.max_entries,
                    'max_size_bytes': self.policy.max_size_bytes,
                    'ttl_seconds': self.policy.ttl_seconds,
                    'enable_lru': self.policy.enable_lru,
                    'cleanup_interval_seconds': self.policy.cleanup_interval_seconds
                },
                'metrics': {
                    'hits': metrics.hits,
                    'misses': metrics.misses,
                    'hit_rate': metrics.hit_rate,
                    'evictions': metrics.evictions,
                    'expirations': metrics.expirations,
                    'entry_count': metrics.entry_count,
                    'total_size_bytes': metrics.total_size_bytes,
                    'cleanup_runs': metrics.cleanup_runs
                },
                'status': {
                    'utilization_percent': (metrics.total_size_bytes / self.policy.max_size_bytes * 100),
                    'entry_utilization_percent': (metrics.entry_count / self.policy.max_entries * 100),
                    'last_cleanup_age_seconds': time.time() - self._last_cleanup
                }
            }
    
    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add callback to run during cleanup."""
        self._cleanup_callbacks.append(callback)
    
    def _ensure_capacity(self, needed_bytes: int) -> bool:
        """Ensure cache has capacity for new entry."""
        # Check entry count limit
        while len(self._entries) >= self.policy.max_entries:
            if not self._evict_one():
                return False
        
        # Check size limit
        while self._metrics.total_size_bytes + needed_bytes > self.policy.max_size_bytes:
            if not self._evict_one():
                return False
        
        return True
    
    def _evict_one(self) -> bool:
        """Evict one entry using LRU policy."""
        if not self._entries:
            return False
        
        # Get LRU key (first in OrderedDict)
        lru_key = next(iter(self._entries))
        self._remove_entry(lru_key, reason="evicted")
        self._metrics.evictions += 1
        return True
    
    def _remove_entry(self, key: str, reason: str = "") -> None:
        """Remove entry and update metrics."""
        if key in self._entries:
            entry = self._entries[key]
            self._metrics.total_size_bytes -= entry.size_bytes
            self._metrics.entry_count -= 1
            del self._entries[key]
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items())
            else:
                return 1024  # Default 1KB estimate
    
    def _record_hit(self, key: str) -> None:
        """Record cache hit."""
        self._metrics.hits += 1
        if self._enable_monitoring:
            record_cache_hit(f"{self.level.value}_{self.name}")
    
    def _record_miss(self, key: str) -> None:
        """Record cache miss."""
        self._metrics.misses += 1
        if self._enable_monitoring:
            record_cache_miss(f"{self.level.value}_{self.name}")
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if interval has passed."""
        if time.time() - self._last_cleanup > self.policy.cleanup_interval_seconds:
            self.cleanup()


class CacheRegistry:
    """Registry for managing multiple cache instances."""

    def __init__(self):
        self._caches: Dict[str, StrategyCache] = {}
        self._lock = threading.RLock()

    def register_cache(self, name: str, cache: StrategyCache) -> None:
        """Register a cache instance."""
        with self._lock:
            self._caches[name] = cache

    def get_cache(self, name: str) -> Optional[StrategyCache]:
        """Get cache by name."""
        with self._lock:
            return self._caches.get(name)

    def get_or_create_cache(self, name: str, level: CacheLevel,
                           policy: Optional[CachePolicy] = None) -> StrategyCache:
        """Get existing cache or create new one."""
        with self._lock:
            if name not in self._caches:
                self._caches[name] = StrategyCache(name, level, policy)
            return self._caches[name]

    def invalidate_all(self) -> None:
        """Invalidate all registered caches."""
        with self._lock:
            for cache in self._caches.values():
                cache.clear()

    def invalidate_by_level(self, level: CacheLevel) -> None:
        """Invalidate all caches of specific level."""
        with self._lock:
            for cache in self._caches.values():
                if cache.level == level:
                    cache.clear()

    def cleanup_all(self) -> Dict[str, int]:
        """Run cleanup on all caches."""
        with self._lock:
            results = {}
            for name, cache in self._caches.items():
                results[name] = cache.cleanup()
            return results

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all caches."""
        with self._lock:
            return {name: cache.get_info() for name, cache in self._caches.items()}

    def list_caches(self) -> List[str]:
        """List all registered cache names."""
        with self._lock:
            return list(self._caches.keys())


# Global cache registry
_cache_registry: Optional[CacheRegistry] = None


def get_cache_registry() -> CacheRegistry:
    """Get global cache registry."""
    global _cache_registry
    if _cache_registry is None:
        _cache_registry = CacheRegistry()
    return _cache_registry


# Convenience functions for common cache operations
def get_session_cache() -> StrategyCache:
    """Get or create session-level cache."""
    return get_cache_registry().get_or_create_cache("session", CacheLevel.SESSION)


def get_preview_cache() -> StrategyCache:
    """Get or create preview-level cache."""
    return get_cache_registry().get_or_create_cache("preview", CacheLevel.PREVIEW)


def get_export_cache() -> StrategyCache:
    """Get or create export-level cache."""
    return get_cache_registry().get_or_create_cache("export", CacheLevel.EXPORT)


def get_persistent_cache() -> StrategyCache:
    """Get or create persistent-level cache."""
    return get_cache_registry().get_or_create_cache("persistent", CacheLevel.PERSISTENT)


def invalidate_cache_level(level: CacheLevel, reason: str = "") -> None:
    """Invalidate all caches of specific level."""
    get_cache_registry().invalidate_by_level(level)
    if get_feature_flag('cache_monitoring', True):
        record_cache_miss(f"level_{level.value}_invalidated")


def get_cache_summary() -> Dict[str, Any]:
    """Get comprehensive cache summary."""
    registry = get_cache_registry()
    all_metrics = registry.get_all_metrics()

    # Aggregate metrics
    total_hits = sum(cache['metrics']['hits'] for cache in all_metrics.values())
    total_misses = sum(cache['metrics']['misses'] for cache in all_metrics.values())
    total_size = sum(cache['metrics']['total_size_bytes'] for cache in all_metrics.values())
    total_entries = sum(cache['metrics']['entry_count'] for cache in all_metrics.values())

    return {
        'summary': {
            'total_caches': len(all_metrics),
            'total_hits': total_hits,
            'total_misses': total_misses,
            'overall_hit_rate': (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0.0,
            'total_size_bytes': total_size,
            'total_entries': total_entries
        },
        'caches': all_metrics
    }


# Cache decorators for easy integration
def cached(cache_name: str, level: CacheLevel, ttl_seconds: Optional[int] = None,
          tags: Optional[Dict[str, str]] = None):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Create cache key
            import hashlib
            import json
            key_data = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(sorted(kwargs.items()))
            }
            cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

            # Get cache
            policy = CachePolicy.for_level(level)
            if ttl_seconds is not None:
                policy.ttl_seconds = ttl_seconds

            cache = get_cache_registry().get_or_create_cache(cache_name, level, policy)

            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, tags)
            return result

        return wrapper
    return decorator


def cache_with_strategy(cache: StrategyCache, key_func: Optional[Callable] = None,
                       tags: Optional[Dict[str, str]] = None):
    """Decorator for caching with specific cache instance."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                import hashlib
                import json
                key_data = {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(sorted(kwargs.items()))
                }
                cache_key = hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

            # Try cache first
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Compute and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, tags)
            return result

        return wrapper
    return decorator
