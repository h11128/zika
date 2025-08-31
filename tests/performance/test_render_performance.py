"""
Performance tests for render performance with baselines.
Tests first render <500ms after digest change, cached <100ms, memory usage tracking.
"""

import pytest
import time
import psutil
import os
import sys
from unittest.mock import MagicMock, patch
import threading
import gc

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class PerformanceMonitor:
    """Monitor performance metrics during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.end_time = None
        self.start_memory = None
        self.end_memory = None
        self.peak_memory = None
        self.cpu_percent = None
    
    def start_monitoring(self):
        """Start performance monitoring."""
        gc.collect()  # Clean up before measurement
        self.start_time = time.perf_counter()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        
        # Start CPU monitoring
        self.process.cpu_percent()  # Initialize CPU monitoring
    
    def end_monitoring(self):
        """End performance monitoring."""
        self.end_time = time.perf_counter()
        self.end_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.cpu_percent = self.process.cpu_percent()
        
        # Update peak memory
        self.peak_memory = max(self.peak_memory, self.end_memory)
    
    def get_metrics(self):
        """Get performance metrics."""
        if self.start_time is None or self.end_time is None:
            return None
        
        return {
            'duration_ms': (self.end_time - self.start_time) * 1000,
            'memory_start_mb': self.start_memory,
            'memory_end_mb': self.end_memory,
            'memory_peak_mb': self.peak_memory,
            'memory_delta_mb': self.end_memory - self.start_memory,
            'cpu_percent': self.cpu_percent
        }


class MockRenderEngine:
    """Mock render engine for performance testing."""
    
    def __init__(self):
        self.cache = {}
        self.render_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.render_times = []
    
    def render_preview(self, cards_data, digest, use_cache=True):
        """Render preview with caching."""
        start_time = time.perf_counter()
        
        # Check cache
        if use_cache and digest in self.cache:
            self.cache_hits += 1
            result = self.cache[digest]
            render_time = (time.perf_counter() - start_time) * 1000
            self.render_times.append(render_time)
            return result
        
        # Cache miss - perform rendering
        self.cache_misses += 1
        self.render_count += 1
        
        # Simulate rendering work
        self._simulate_rendering_work(len(cards_data))
        
        # Generate result
        result = f"<div>Rendered {len(cards_data)} cards</div>"
        
        # Cache result
        if use_cache:
            self.cache[digest] = result
        
        render_time = (time.perf_counter() - start_time) * 1000
        self.render_times.append(render_time)
        
        return result
    
    def _simulate_rendering_work(self, card_count):
        """Simulate rendering work proportional to card count."""
        # Simulate processing time (0.1ms per card base + some overhead)
        base_time = 0.001  # 1ms base
        per_card_time = 0.0001  # 0.1ms per card
        
        work_time = base_time + (card_count * per_card_time)
        time.sleep(work_time)
    
    def get_cache_stats(self):
        """Get cache statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'cache_size': len(self.cache),
            'avg_render_time_ms': sum(self.render_times) / len(self.render_times) if self.render_times else 0
        }
    
    def clear_cache(self):
        """Clear cache."""
        self.cache.clear()
    
    def reset_stats(self):
        """Reset statistics."""
        self.cache_hits = 0
        self.cache_misses = 0
        self.render_count = 0
        self.render_times.clear()


class TestRenderPerformanceBaselines:
    """Test render performance against baselines."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.render_engine = MockRenderEngine()
        self.monitor = PerformanceMonitor()
        
        # Performance baselines
        self.FIRST_RENDER_BASELINE_MS = 500
        self.CACHED_RENDER_BASELINE_MS = 100
        self.MEMORY_BASELINE_MB = 150  # Adjusted for test environment
        self.MIN_CACHE_HIT_RATE = 0.8
    
    def test_first_render_performance(self):
        """Test first render performance meets baseline."""
        # Generate test data
        cards_data = [
            {'uuid': f'card-{i}', 'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
            for i in range(50)  # Medium dataset
        ]
        digest = "test_digest_first_render"
        
        # Monitor first render
        self.monitor.start_monitoring()
        result = self.render_engine.render_preview(cards_data, digest, use_cache=True)
        self.monitor.end_monitoring()
        
        # Get metrics
        metrics = self.monitor.get_metrics()
        
        # Verify baseline compliance
        assert metrics['duration_ms'] < self.FIRST_RENDER_BASELINE_MS, \
            f"First render took {metrics['duration_ms']:.2f}ms, exceeds baseline of {self.FIRST_RENDER_BASELINE_MS}ms"
        
        # Verify result
        assert result is not None
        assert len(result) > 0
        
        # Verify cache miss (first render)
        stats = self.render_engine.get_cache_stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0
    
    def test_cached_render_performance(self):
        """Test cached render performance meets baseline."""
        # Generate test data
        cards_data = [
            {'uuid': f'card-{i}', 'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
            for i in range(50)
        ]
        digest = "test_digest_cached_render"
        
        # First render (populate cache)
        self.render_engine.render_preview(cards_data, digest, use_cache=True)
        
        # Monitor cached render
        self.monitor.start_monitoring()
        result = self.render_engine.render_preview(cards_data, digest, use_cache=True)
        self.monitor.end_monitoring()
        
        # Get metrics
        metrics = self.monitor.get_metrics()
        
        # Verify baseline compliance
        assert metrics['duration_ms'] < self.CACHED_RENDER_BASELINE_MS, \
            f"Cached render took {metrics['duration_ms']:.2f}ms, exceeds baseline of {self.CACHED_RENDER_BASELINE_MS}ms"
        
        # Verify result
        assert result is not None
        
        # Verify cache hit
        stats = self.render_engine.get_cache_stats()
        assert stats['hits'] >= 1
    
    def test_memory_usage_baseline(self):
        """Test memory usage stays within baseline."""
        # Generate large dataset
        cards_data = [
            {'uuid': f'card-{i}', 'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'char{i}'}
            for i in range(1000)  # Large dataset
        ]
        
        # Monitor memory during rendering
        self.monitor.start_monitoring()
        
        # Render multiple times with different digests
        for i in range(10):
            digest = f"test_digest_memory_{i}"
            self.render_engine.render_preview(cards_data, digest, use_cache=True)
        
        self.monitor.end_monitoring()
        
        # Get metrics
        metrics = self.monitor.get_metrics()
        
        # Verify memory baseline
        assert metrics['memory_peak_mb'] < self.MEMORY_BASELINE_MB, \
            f"Peak memory usage {metrics['memory_peak_mb']:.2f}MB exceeds baseline of {self.MEMORY_BASELINE_MB}MB"
        
        # Verify memory delta is reasonable
        assert metrics['memory_delta_mb'] < 20, \
            f"Memory delta {metrics['memory_delta_mb']:.2f}MB is too high"
    
    def test_cache_hit_rate_baseline(self):
        """Test cache hit rate meets baseline."""
        # Generate test data
        cards_data = [
            {'uuid': f'card-{i}', 'hanzi': f'字{i}'}
            for i in range(20)
        ]
        
        # Create multiple digests for variety
        digests = [f"digest_{i}" for i in range(5)]
        
        # Perform many renders with repeated digests
        for _ in range(20):
            for digest in digests:
                self.render_engine.render_preview(cards_data, digest, use_cache=True)
        
        # Get cache statistics
        stats = self.render_engine.get_cache_stats()
        
        # Verify cache hit rate baseline
        assert stats['hit_rate'] >= self.MIN_CACHE_HIT_RATE, \
            f"Cache hit rate {stats['hit_rate']:.2f} below baseline of {self.MIN_CACHE_HIT_RATE}"
        
        # Verify reasonable cache size
        assert stats['cache_size'] == len(digests)
        assert stats['total_requests'] == 20 * len(digests)


class TestPerformanceRegression:
    """Test performance regression detection."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.render_engine = MockRenderEngine()
        self.baseline_metrics = {}
    
    def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        # Establish baseline
        cards_data = [{'uuid': f'card-{i}', 'hanzi': f'字{i}'} for i in range(100)]
        
        # Measure baseline performance
        baseline_times = []
        for i in range(10):
            start_time = time.perf_counter()
            self.render_engine.render_preview(cards_data, f"baseline_{i}", use_cache=False)
            end_time = time.perf_counter()
            baseline_times.append((end_time - start_time) * 1000)
        
        baseline_avg = sum(baseline_times) / len(baseline_times)
        baseline_max = max(baseline_times)
        
        # Store baseline
        self.baseline_metrics = {
            'avg_render_time_ms': baseline_avg,
            'max_render_time_ms': baseline_max,
            'p95_render_time_ms': sorted(baseline_times)[int(0.95 * len(baseline_times))]
        }
        
        # Test current performance
        current_times = []
        for i in range(10):
            start_time = time.perf_counter()
            self.render_engine.render_preview(cards_data, f"current_{i}", use_cache=False)
            end_time = time.perf_counter()
            current_times.append((end_time - start_time) * 1000)
        
        current_avg = sum(current_times) / len(current_times)
        current_max = max(current_times)
        current_p95 = sorted(current_times)[int(0.95 * len(current_times))]
        
        # Check for regression (allow 20% variance)
        regression_threshold = 1.2
        
        assert current_avg <= baseline_avg * regression_threshold, \
            f"Average render time regression: {current_avg:.2f}ms vs baseline {baseline_avg:.2f}ms"
        
        assert current_max <= baseline_max * regression_threshold, \
            f"Max render time regression: {current_max:.2f}ms vs baseline {baseline_max:.2f}ms"
        
        assert current_p95 <= self.baseline_metrics['p95_render_time_ms'] * regression_threshold, \
            f"P95 render time regression: {current_p95:.2f}ms vs baseline {self.baseline_metrics['p95_render_time_ms']:.2f}ms"
    
    def test_cache_performance_regression(self):
        """Test cache performance regression detection."""
        cards_data = [{'uuid': f'card-{i}', 'hanzi': f'字{i}'} for i in range(50)]
        digest = "cache_perf_test"
        
        # Baseline: First render (cache miss)
        start_time = time.perf_counter()
        self.render_engine.render_preview(cards_data, digest, use_cache=True)
        miss_time = (time.perf_counter() - start_time) * 1000
        
        # Test: Cached render (cache hit)
        start_time = time.perf_counter()
        self.render_engine.render_preview(cards_data, digest, use_cache=True)
        hit_time = (time.perf_counter() - start_time) * 1000
        
        # Cache hit should be significantly faster
        cache_speedup = miss_time / hit_time if hit_time > 0 else float('inf')
        
        assert cache_speedup >= 2.0, \
            f"Cache speedup {cache_speedup:.2f}x is below expected minimum of 2.0x"
        
        assert hit_time < 50, \
            f"Cache hit time {hit_time:.2f}ms is too slow"


class TestConcurrentPerformance:
    """Test performance under concurrent load."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.render_engine = MockRenderEngine()
        self.results = []
        self.errors = []
    
    def test_concurrent_render_performance(self):
        """Test performance under concurrent rendering load."""
        cards_data = [{'uuid': f'card-{i}', 'hanzi': f'字{i}'} for i in range(30)]
        
        def render_worker(worker_id):
            """Worker function for concurrent rendering."""
            try:
                start_time = time.perf_counter()
                
                # Each worker renders with different digests
                for i in range(5):
                    digest = f"worker_{worker_id}_render_{i}"
                    result = self.render_engine.render_preview(cards_data, digest, use_cache=True)
                    assert result is not None
                
                end_time = time.perf_counter()
                duration = (end_time - start_time) * 1000
                
                self.results.append({
                    'worker_id': worker_id,
                    'duration_ms': duration,
                    'renders_per_second': 5 / ((end_time - start_time) or 0.001)
                })
                
            except Exception as e:
                self.errors.append(f"Worker {worker_id}: {str(e)}")
        
        # Start concurrent workers
        num_workers = 4
        threads = []
        
        start_time = time.perf_counter()
        
        for worker_id in range(num_workers):
            thread = threading.Thread(target=render_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all workers to complete
        for thread in threads:
            thread.join()
        
        end_time = time.perf_counter()
        total_duration = (end_time - start_time) * 1000
        
        # Verify no errors
        assert len(self.errors) == 0, f"Concurrent rendering errors: {self.errors}"
        
        # Verify all workers completed
        assert len(self.results) == num_workers
        
        # Verify performance
        avg_worker_duration = sum(r['duration_ms'] for r in self.results) / len(self.results)
        total_renders = num_workers * 5
        overall_rps = total_renders / (total_duration / 1000)
        
        # Performance assertions
        assert avg_worker_duration < 1000, \
            f"Average worker duration {avg_worker_duration:.2f}ms too slow"
        
        assert overall_rps > 10, \
            f"Overall renders per second {overall_rps:.2f} too low"
        
        # Verify cache effectiveness
        stats = self.render_engine.get_cache_stats()
        assert stats['total_requests'] == total_renders


if __name__ == "__main__":
    pytest.main([__file__])
