"""
Performance tests for cache behavior and hit rate monitoring.
Tests cache hit rate >80%, memory efficiency, and invalidation performance.
"""

import pytest
import time
import sys
import os
import threading
import random
from collections import defaultdict
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class PerformanceCacheManager:
    """Performance-focused cache manager for testing."""
    
    def __init__(self, max_size=1000, ttl_seconds=300):
        self.cache = {}
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.access_log = []
        self.lock = threading.RLock()
    
    def get(self, key):
        """Get value from cache with performance tracking."""
        with self.lock:
            current_time = time.time()
            self.access_log.append(('get', key, current_time))
            
            # Check if key exists and is not expired
            if key in self.cache:
                access_time = self.access_times.get(key, 0)
                if current_time - access_time < self.ttl_seconds:
                    self.hit_count += 1
                    self.access_times[key] = current_time
                    return self.cache[key]
                else:
                    # Expired
                    del self.cache[key]
                    del self.access_times[key]
            
            # Cache miss
            self.miss_count += 1
            return None
    
    def set(self, key, value):
        """Set value in cache with LRU eviction."""
        with self.lock:
            current_time = time.time()
            self.access_log.append(('set', key, current_time))
            
            # Evict if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                self._evict_lru()
            
            self.cache[key] = value
            self.access_times[key] = current_time
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        del self.cache[lru_key]
        del self.access_times[lru_key]
        self.eviction_count += 1
    
    def invalidate(self, pattern=None):
        """Invalidate cache entries."""
        with self.lock:
            if pattern is None:
                # Clear all
                self.cache.clear()
                self.access_times.clear()
            else:
                # Pattern-based invalidation
                keys_to_remove = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self.cache[key]
                    del self.access_times[key]
    
    def get_stats(self):
        """Get cache performance statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.hit_count,
            'misses': self.miss_count,
            'hit_rate': hit_rate,
            'evictions': self.eviction_count,
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'total_requests': total_requests
        }
    
    def reset_stats(self):
        """Reset performance statistics."""
        self.hit_count = 0
        self.miss_count = 0
        self.eviction_count = 0
        self.access_log.clear()


class TestCacheHitRatePerformance:
    """Test cache hit rate performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PerformanceCacheManager(max_size=500)  # Larger cache to avoid evictions
        self.MIN_HIT_RATE = 0.8
    
    def test_cache_hit_rate_baseline(self):
        """Test cache hit rate meets 80% baseline."""
        # Simulate realistic access pattern
        keys = [f"key_{i}" for i in range(20)]  # 20 unique keys
        values = [f"value_{i}" for i in range(20)]
        
        # Phase 1: Populate cache
        for key, value in zip(keys, values):
            self.cache.set(key, value)
        
        # Phase 2: Mixed access pattern (80% hits, 20% misses)
        access_pattern = []
        
        # 80% accesses to existing keys
        for _ in range(800):
            key = random.choice(keys)
            access_pattern.append(('existing', key))
        
        # 20% accesses to new keys
        for i in range(200):
            new_key = f"new_key_{i}"
            access_pattern.append(('new', new_key))
        
        # Shuffle access pattern
        random.shuffle(access_pattern)
        
        # Execute access pattern
        for access_type, key in access_pattern:
            result = self.cache.get(key)
            if access_type == 'new' and result is None:
                # Set new key
                self.cache.set(key, f"value_for_{key}")
        
        # Verify hit rate
        stats = self.cache.get_stats()
        assert stats['hit_rate'] >= self.MIN_HIT_RATE, \
            f"Cache hit rate {stats['hit_rate']:.3f} below baseline {self.MIN_HIT_RATE}"
    
    def test_cache_hit_rate_under_pressure(self):
        """Test cache hit rate under memory pressure."""
        # Small cache with high pressure
        small_cache = PerformanceCacheManager(max_size=10)
        
        # Generate more keys than cache capacity
        keys = [f"pressure_key_{i}" for i in range(50)]
        
        # Access pattern: frequent access to subset of keys
        hot_keys = keys[:5]  # 5 hot keys
        cold_keys = keys[5:]  # 45 cold keys
        
        # Populate with hot keys
        for key in hot_keys:
            small_cache.set(key, f"value_{key}")
        
        # Mixed access: 90% hot keys, 10% cold keys
        for _ in range(1000):
            if random.random() < 0.9:
                # Access hot key
                key = random.choice(hot_keys)
                result = small_cache.get(key)
                if result is None:
                    small_cache.set(key, f"value_{key}")
            else:
                # Access cold key
                key = random.choice(cold_keys)
                result = small_cache.get(key)
                if result is None:
                    small_cache.set(key, f"value_{key}")
        
        # Verify reasonable hit rate even under pressure
        stats = small_cache.get_stats()
        assert stats['hit_rate'] >= 0.6, \
            f"Hit rate under pressure {stats['hit_rate']:.3f} too low"
        
        # Verify evictions occurred
        assert stats['evictions'] > 0, "No evictions occurred under pressure"
    
    def test_cache_temporal_locality(self):
        """Test cache performance with temporal locality."""
        # Simulate temporal locality (recent items accessed more frequently)
        keys = [f"temporal_key_{i}" for i in range(30)]
        
        # Time-based access simulation
        for time_window in range(10):
            # In each time window, focus on a subset of keys
            window_keys = keys[time_window:time_window + 10]
            
            # Populate window keys
            for key in window_keys:
                self.cache.set(key, f"value_{key}_window_{time_window}")
            
            # Heavy access to window keys
            for _ in range(100):
                key = random.choice(window_keys)
                self.cache.get(key)
        
        # Verify good hit rate with temporal locality
        stats = self.cache.get_stats()
        assert stats['hit_rate'] >= 0.85, \
            f"Temporal locality hit rate {stats['hit_rate']:.3f} below expected"


class TestCacheMemoryEfficiency:
    """Test cache memory efficiency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PerformanceCacheManager(max_size=1000)
    
    def test_memory_efficient_storage(self):
        """Test memory-efficient cache storage."""
        # Store various data sizes
        test_data = [
            ("small", "x" * 100),           # 100 bytes
            ("medium", "x" * 1000),         # 1KB
            ("large", "x" * 10000),         # 10KB
        ]
        
        # Populate cache
        for i in range(100):
            for size_type, data in test_data:
                key = f"{size_type}_{i}"
                self.cache.set(key, data)
        
        # Verify cache size management
        stats = self.cache.get_stats()
        assert stats['cache_size'] <= stats['max_size'], \
            f"Cache size {stats['cache_size']} exceeds max {stats['max_size']}"
        
        # Test access performance
        start_time = time.perf_counter()
        
        # Access random items
        for _ in range(1000):
            size_type = random.choice(["small", "medium", "large"])
            index = random.randint(0, 99)
            key = f"{size_type}_{index}"
            self.cache.get(key)
        
        end_time = time.perf_counter()
        access_time_ms = (end_time - start_time) * 1000
        
        # Verify reasonable access performance
        avg_access_time_ms = access_time_ms / 1000
        assert avg_access_time_ms < 0.1, \
            f"Average access time {avg_access_time_ms:.3f}ms too slow"
    
    def test_cache_eviction_efficiency(self):
        """Test efficient cache eviction."""
        # Fill cache to capacity
        for i in range(self.cache.max_size):
            self.cache.set(f"fill_key_{i}", f"value_{i}")
        
        # Verify cache is full
        assert len(self.cache.cache) == self.cache.max_size
        
        # Add more items to trigger evictions
        eviction_start_time = time.perf_counter()
        
        for i in range(100):
            self.cache.set(f"overflow_key_{i}", f"overflow_value_{i}")
        
        eviction_end_time = time.perf_counter()
        eviction_time_ms = (eviction_end_time - eviction_start_time) * 1000
        
        # Verify evictions occurred
        stats = self.cache.get_stats()
        assert stats['evictions'] > 0, "No evictions occurred"
        
        # Verify cache size maintained
        assert len(self.cache.cache) <= self.cache.max_size
        
        # Verify eviction performance
        avg_eviction_time_ms = eviction_time_ms / 100
        assert avg_eviction_time_ms < 1.0, \
            f"Average eviction time {avg_eviction_time_ms:.3f}ms too slow"


class TestCacheInvalidationPerformance:
    """Test cache invalidation performance."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PerformanceCacheManager(max_size=1000)
    
    def test_full_invalidation_performance(self):
        """Test full cache invalidation performance."""
        # Populate large cache
        for i in range(1000):
            self.cache.set(f"invalidation_key_{i}", f"value_{i}")
        
        # Verify cache is populated
        assert len(self.cache.cache) == 1000
        
        # Measure invalidation time
        start_time = time.perf_counter()
        self.cache.invalidate()
        end_time = time.perf_counter()
        
        invalidation_time_ms = (end_time - start_time) * 1000
        
        # Verify cache is cleared
        assert len(self.cache.cache) == 0
        
        # Verify invalidation performance
        assert invalidation_time_ms < 10, \
            f"Full invalidation took {invalidation_time_ms:.3f}ms, too slow"
    
    def test_pattern_invalidation_performance(self):
        """Test pattern-based invalidation performance."""
        # Populate cache with different patterns
        patterns = ["user_", "session_", "preview_", "export_"]
        
        for pattern in patterns:
            for i in range(250):  # 250 keys per pattern
                key = f"{pattern}{i}"
                self.cache.set(key, f"value_{key}")
        
        # Verify cache is populated
        assert len(self.cache.cache) == 1000
        
        # Measure pattern invalidation time
        start_time = time.perf_counter()
        self.cache.invalidate("user_")
        end_time = time.perf_counter()
        
        invalidation_time_ms = (end_time - start_time) * 1000
        
        # Verify partial invalidation
        remaining_keys = list(self.cache.cache.keys())
        assert len(remaining_keys) == 750  # 1000 - 250
        assert not any(key.startswith("user_") for key in remaining_keys)
        
        # Verify invalidation performance
        assert invalidation_time_ms < 5, \
            f"Pattern invalidation took {invalidation_time_ms:.3f}ms, too slow"


class TestConcurrentCachePerformance:
    """Test cache performance under concurrent access."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache = PerformanceCacheManager(max_size=500)
        self.results = []
        self.errors = []
    
    def test_concurrent_cache_access(self):
        """Test cache performance under concurrent access."""
        # Pre-populate cache
        for i in range(100):
            self.cache.set(f"concurrent_key_{i}", f"value_{i}")
        
        def cache_worker(worker_id, operations_count):
            """Worker function for concurrent cache access."""
            try:
                start_time = time.perf_counter()
                
                for i in range(operations_count):
                    # Mix of gets and sets
                    if random.random() < 0.8:  # 80% reads
                        key = f"concurrent_key_{random.randint(0, 149)}"
                        self.cache.get(key)
                    else:  # 20% writes
                        key = f"concurrent_key_{worker_id}_{i}"
                        self.cache.set(key, f"worker_{worker_id}_value_{i}")
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                ops_per_second = operations_count / ((end_time - start_time) or 0.001)
                
                self.results.append({
                    'worker_id': worker_id,
                    'duration_ms': duration_ms,
                    'ops_per_second': ops_per_second
                })
                
            except Exception as e:
                self.errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Start concurrent workers
        num_workers = 8
        operations_per_worker = 1000
        threads = []
        
        start_time = time.perf_counter()
        
        for worker_id in range(num_workers):
            thread = threading.Thread(
                target=cache_worker, 
                args=(worker_id, operations_per_worker)
            )
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.perf_counter()
        total_duration_ms = (end_time - start_time) * 1000
        
        # Verify no errors
        assert len(self.errors) == 0, f"Concurrent access errors: {self.errors}"
        
        # Verify all workers completed
        assert len(self.results) == num_workers
        
        # Verify performance
        total_operations = num_workers * operations_per_worker
        overall_ops_per_second = total_operations / (total_duration_ms / 1000)
        
        assert overall_ops_per_second > 10000, \
            f"Overall ops/sec {overall_ops_per_second:.0f} too low"
        
        # Verify cache integrity
        stats = self.cache.get_stats()
        assert stats['total_requests'] > 0
        assert stats['cache_size'] <= self.cache.max_size


if __name__ == "__main__":
    pytest.main([__file__])
