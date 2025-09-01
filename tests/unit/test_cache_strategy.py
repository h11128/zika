"""
Unit tests for services/cache_strategy.py
Tests enhanced cache strategy with TTL, LRU eviction, and observability.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock

from services.cache_strategy import (
    CacheLevel, CachePolicy, CacheEntry, CacheMetrics, StrategyCache,
    CacheRegistry, get_cache_registry, get_session_cache, get_preview_cache,
    get_export_cache, get_persistent_cache, invalidate_cache_level,
    get_cache_summary, cached, cache_with_strategy
)


class TestCachePolicy:
    """Test cache policy configuration."""
    
    def test_default_policy(self):
        """Test default cache policy."""
        policy = CachePolicy()
        assert policy.max_entries == 100
        assert policy.max_size_bytes == 10 * 1024 * 1024
        assert policy.ttl_seconds == 3600
        assert policy.enable_lru is True
        assert policy.enable_monitoring is True
    
    def test_level_specific_policies(self):
        """Test level-specific cache policies."""
        session_policy = CachePolicy.for_level(CacheLevel.SESSION)
        preview_policy = CachePolicy.for_level(CacheLevel.PREVIEW)
        export_policy = CachePolicy.for_level(CacheLevel.EXPORT)
        persistent_policy = CachePolicy.for_level(CacheLevel.PERSISTENT)
        
        # Session should have smallest limits
        assert session_policy.max_entries == 50
        assert session_policy.ttl_seconds == 1800
        
        # Export should have larger limits
        assert export_policy.max_entries == 200
        assert export_policy.ttl_seconds == 7200
        
        # Persistent should have largest limits
        assert persistent_policy.max_entries == 500
        assert persistent_policy.ttl_seconds == 86400


class TestCacheEntry:
    """Test cache entry functionality."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation."""
        entry = CacheEntry(
            value="test_value",
            key="test_key",
            created_at=time.time(),
            last_accessed=time.time()
        )
        
        assert entry.value == "test_value"
        assert entry.key == "test_key"
        assert entry.access_count == 0
        assert entry.size_bytes == 0
    
    def test_cache_entry_touch(self):
        """Test cache entry touch functionality."""
        entry = CacheEntry(
            value="test",
            key="key",
            created_at=time.time(),
            last_accessed=time.time()
        )
        
        initial_access_time = entry.last_accessed
        initial_count = entry.access_count
        
        time.sleep(0.01)  # Small delay
        entry.touch()
        
        assert entry.last_accessed > initial_access_time
        assert entry.access_count == initial_count + 1
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration."""
        entry = CacheEntry(
            value="test",
            key="key",
            created_at=time.time() - 3600,  # 1 hour ago
            last_accessed=time.time()
        )
        
        assert entry.is_expired(1800)  # 30 minute TTL
        assert not entry.is_expired(7200)  # 2 hour TTL
    
    def test_cache_entry_age(self):
        """Test cache entry age calculation."""
        created_time = time.time() - 100
        entry = CacheEntry(
            value="test",
            key="key",
            created_at=created_time,
            last_accessed=time.time()
        )
        
        age = entry.age_seconds()
        assert 99 <= age <= 101  # Allow small timing variance


class TestCacheMetrics:
    """Test cache metrics functionality."""
    
    def test_cache_metrics_creation(self):
        """Test cache metrics creation."""
        metrics = CacheMetrics()
        assert metrics.hits == 0
        assert metrics.misses == 0
        assert metrics.hit_rate == 0.0
        assert metrics.miss_rate == 0.0
    
    def test_cache_metrics_rates(self):
        """Test cache metrics rate calculations."""
        metrics = CacheMetrics(hits=80, misses=20)
        assert metrics.hit_rate == 80.0
        assert metrics.miss_rate == 20.0
        
        # Test with no operations
        empty_metrics = CacheMetrics()
        assert empty_metrics.hit_rate == 0.0
        assert empty_metrics.miss_rate == 0.0


class TestStrategyCache:
    """Test strategy cache implementation."""
    
    def test_cache_creation(self):
        """Test cache creation."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        assert cache.name == "test"
        assert cache.level == CacheLevel.SESSION
        assert isinstance(cache.policy, CachePolicy)
    
    def test_cache_basic_operations(self):
        """Test basic cache get/set operations."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        
        # Test miss
        assert cache.get("key1") is None
        
        # Test set and hit
        assert cache.set("key1", "value1") is True
        assert cache.get("key1") == "value1"
        
        # Test metrics
        metrics = cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.misses == 1
        assert metrics.entry_count == 1
    
    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        policy = CachePolicy(ttl_seconds=1)  # 1 second TTL
        cache = StrategyCache("test", CacheLevel.SESSION, policy)
        
        # Set value
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
        
        # Check metrics
        metrics = cache.get_metrics()
        assert metrics.expirations == 1
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction."""
        policy = CachePolicy(max_entries=2, enable_lru=True)
        cache = StrategyCache("test", CacheLevel.SESSION, policy)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add third item, should evict key2 (LRU)
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "value1"  # Should still exist
        assert cache.get("key2") is None      # Should be evicted
        assert cache.get("key3") == "value3"  # Should exist
        
        # Check metrics
        metrics = cache.get_metrics()
        assert metrics.evictions == 1
    
    def test_cache_size_limit(self):
        """Test size-based eviction."""
        policy = CachePolicy(max_size_bytes=100, max_entries=10)
        cache = StrategyCache("test", CacheLevel.SESSION, policy)
        
        # Add items until size limit is reached
        large_value = "x" * 50  # 50 bytes
        cache.set("key1", large_value)
        cache.set("key2", large_value)
        
        # This should trigger eviction due to size
        cache.set("key3", large_value)
        
        metrics = cache.get_metrics()
        assert metrics.evictions > 0
        assert metrics.total_size_bytes <= policy.max_size_bytes
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        
        # Set values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Invalidate specific key
        assert cache.invalidate("key1") is True
        assert cache.invalidate("nonexistent") is False
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_cache_tag_invalidation(self):
        """Test tag-based invalidation."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        
        # Set values with tags
        cache.set("key1", "value1", {"type": "user", "id": "123"})
        cache.set("key2", "value2", {"type": "user", "id": "456"})
        cache.set("key3", "value3", {"type": "system"})
        
        # Invalidate by tag
        invalidated = cache.invalidate_by_tags({"type": "user"})
        assert invalidated == 2
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") == "value3"
    
    def test_cache_cleanup(self):
        """Test manual cleanup."""
        policy = CachePolicy(ttl_seconds=1)
        cache = StrategyCache("test", CacheLevel.SESSION, policy)
        
        # Add entries
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Manual cleanup
        expired_count = cache.cleanup()
        assert expired_count == 2
        
        metrics = cache.get_metrics()
        assert metrics.cleanup_runs == 1
        assert metrics.entry_count == 0
    
    def test_cache_info(self):
        """Test cache info retrieval."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        cache.set("key1", "value1")
        
        info = cache.get_info()
        assert info['name'] == "test"
        assert info['level'] == "session"
        assert 'policy' in info
        assert 'metrics' in info
        assert 'status' in info
        assert info['metrics']['entry_count'] == 1


class TestCacheRegistry:
    """Test cache registry functionality."""
    
    def test_registry_creation(self):
        """Test registry creation."""
        registry = CacheRegistry()
        assert len(registry.list_caches()) == 0
    
    def test_registry_cache_management(self):
        """Test cache registration and retrieval."""
        registry = CacheRegistry()
        cache = StrategyCache("test", CacheLevel.SESSION)
        
        # Register cache
        registry.register_cache("test", cache)
        assert "test" in registry.list_caches()
        
        # Retrieve cache
        retrieved = registry.get_cache("test")
        assert retrieved is cache
        
        # Get nonexistent cache
        assert registry.get_cache("nonexistent") is None
    
    def test_registry_get_or_create(self):
        """Test get or create cache functionality."""
        registry = CacheRegistry()
        
        # Create new cache
        cache1 = registry.get_or_create_cache("test", CacheLevel.SESSION)
        assert cache1.name == "test"
        assert cache1.level == CacheLevel.SESSION
        
        # Get existing cache
        cache2 = registry.get_or_create_cache("test", CacheLevel.PREVIEW)
        assert cache2 is cache1  # Should return existing cache
    
    def test_registry_invalidation(self):
        """Test registry-wide invalidation."""
        registry = CacheRegistry()
        
        # Create caches
        session_cache = registry.get_or_create_cache("session", CacheLevel.SESSION)
        preview_cache = registry.get_or_create_cache("preview", CacheLevel.PREVIEW)
        
        # Add data
        session_cache.set("key1", "value1")
        preview_cache.set("key2", "value2")
        
        # Invalidate by level
        registry.invalidate_by_level(CacheLevel.SESSION)
        
        assert session_cache.get("key1") is None
        assert preview_cache.get("key2") == "value2"
        
        # Invalidate all
        registry.invalidate_all()
        assert preview_cache.get("key2") is None
    
    def test_registry_cleanup_all(self):
        """Test registry-wide cleanup."""
        registry = CacheRegistry()
        
        # Create caches with expired entries
        policy = CachePolicy(ttl_seconds=1)
        cache1 = StrategyCache("cache1", CacheLevel.SESSION, policy)
        cache2 = StrategyCache("cache2", CacheLevel.SESSION, policy)
        
        registry.register_cache("cache1", cache1)
        registry.register_cache("cache2", cache2)
        
        # Add entries
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Cleanup all
        results = registry.cleanup_all()
        assert results["cache1"] == 1
        assert results["cache2"] == 1
    
    def test_registry_metrics(self):
        """Test registry metrics collection."""
        registry = CacheRegistry()
        
        # Create and populate caches
        cache1 = registry.get_or_create_cache("cache1", CacheLevel.SESSION)
        cache2 = registry.get_or_create_cache("cache2", CacheLevel.PREVIEW)
        
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")
        
        # Get all metrics
        all_metrics = registry.get_all_metrics()
        assert "cache1" in all_metrics
        assert "cache2" in all_metrics
        assert all_metrics["cache1"]["metrics"]["entry_count"] == 1
        assert all_metrics["cache2"]["metrics"]["entry_count"] == 1


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_cache_functions(self):
        """Test cache getter functions."""
        session_cache = get_session_cache()
        preview_cache = get_preview_cache()
        export_cache = get_export_cache()
        persistent_cache = get_persistent_cache()
        
        assert session_cache.level == CacheLevel.SESSION
        assert preview_cache.level == CacheLevel.PREVIEW
        assert export_cache.level == CacheLevel.EXPORT
        assert persistent_cache.level == CacheLevel.PERSISTENT
        
        # Should return same instances on subsequent calls
        assert get_session_cache() is session_cache
        assert get_preview_cache() is preview_cache
    
    def test_cache_summary(self):
        """Test cache summary function."""
        # Populate some caches
        session_cache = get_session_cache()
        preview_cache = get_preview_cache()
        
        session_cache.set("key1", "value1")
        preview_cache.set("key2", "value2")
        
        # Get summary
        summary = get_cache_summary()
        assert 'summary' in summary
        assert 'caches' in summary
        assert summary['summary']['total_caches'] >= 2
        assert summary['summary']['total_entries'] >= 2


class TestCacheDecorators:
    """Test cache decorators."""
    
    def test_cached_decorator(self):
        """Test cached decorator."""
        call_count = 0
        
        @cached("test_cache", CacheLevel.SESSION, ttl_seconds=3600)
        def expensive_function(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        # First call should execute function
        result1 = expensive_function(1, 2)
        assert result1 == 3
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_function(1, 2)
        assert result2 == 3
        assert call_count == 1  # Should not increment
        
        # Different arguments should execute function
        result3 = expensive_function(2, 3)
        assert result3 == 5
        assert call_count == 2
    
    def test_cache_with_strategy_decorator(self):
        """Test cache with strategy decorator."""
        cache = StrategyCache("test", CacheLevel.SESSION)
        call_count = 0
        
        @cache_with_strategy(cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        
        # Check cache metrics
        metrics = cache.get_metrics()
        assert metrics.hits == 1
        assert metrics.misses == 1


if __name__ == "__main__":
    pytest.main([__file__])
