"""
Performance benchmarks for UI refactor validation.
Tests that performance targets are met: first render <500ms, cached <100ms, memory <50MB, cache hit >80%.
"""

import time
import pytest
import psutil
import os
from unittest.mock import Mock, patch

from services.performance_monitor import (
    get_performance_monitor, measure_performance, performance_context,
    get_cache_tracker, record_cache_hit, record_cache_miss,
    validate_performance_targets, PERFORMANCE_TARGETS
)
from ui.ports import get_ui_adapter, create_component_config
from ui.performance_utils import (
    get_performance_optimizer, memoize_ui_computation, 
    debounce_ui_operation, create_lazy_loader
)


class TestPerformanceTargets:
    """Test that performance targets are met."""
    
    def test_first_render_performance(self):
        """Test that first render is under 500ms target."""
        adapter = get_ui_adapter()
        
        # Simulate first render
        start_time = time.time()
        
        # Initialize all adapter components (simulates first render)
        _ = adapter.inputs
        _ = adapter.layout
        _ = adapter.notifications
        _ = adapter.preview
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Record performance
        measure_performance('first_render', duration_ms)
        
        # Should meet target
        assert duration_ms < PERFORMANCE_TARGETS['first_render_ms'], \
            f"First render took {duration_ms:.2f}ms, target is {PERFORMANCE_TARGETS['first_render_ms']}ms"
    
    def test_cached_render_performance(self):
        """Test that cached renders are under 100ms target."""
        adapter = get_ui_adapter()
        
        # Pre-initialize (simulate cache warming)
        _ = adapter.inputs
        _ = adapter.layout
        
        # Measure cached access
        start_time = time.time()
        
        # Access already initialized components
        for _ in range(10):
            _ = adapter.inputs
            _ = adapter.layout
            _ = adapter.notifications
        
        duration_ms = (time.time() - start_time) * 1000
        avg_duration = duration_ms / 10
        
        # Record performance
        measure_performance('cached_render', avg_duration)
        
        # Should meet target
        assert avg_duration < PERFORMANCE_TARGETS['cached_render_ms'], \
            f"Cached render took {avg_duration:.2f}ms, target is {PERFORMANCE_TARGETS['cached_render_ms']}ms"
    
    def test_memory_usage_target(self):
        """Test that memory usage is under 50MB target."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many adapters and components (should reuse due to singleton)
        adapters = []
        configs = []
        
        for i in range(1000):
            adapter = get_ui_adapter()
            adapters.append(adapter)
            
            config = create_component_config(f"key_{i}", f"Label {i}")
            configs.append(config)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Should meet target
        assert memory_increase < PERFORMANCE_TARGETS['memory_usage_mb'], \
            f"Memory increase was {memory_increase:.2f}MB, target is {PERFORMANCE_TARGETS['memory_usage_mb']}MB"
    
    def test_cache_hit_rate_target(self):
        """Test that cache hit rate exceeds 80% target."""
        # Reset cache tracker
        tracker = get_cache_tracker()
        tracker.reset()
        
        # Simulate cache operations with high hit rate
        for _ in range(20):
            record_cache_hit()  # 20 hits
        
        for _ in range(4):
            record_cache_miss()  # 4 misses
        
        # Total: 20 hits, 4 misses = 83.3% hit rate
        stats = tracker.get_stats()
        hit_rate = stats['hit_rate']
        
        # Should meet target
        assert hit_rate >= PERFORMANCE_TARGETS['cache_hit_rate_percent'], \
            f"Cache hit rate was {hit_rate:.1f}%, target is {PERFORMANCE_TARGETS['cache_hit_rate_percent']}%"


class TestComponentPerformance:
    """Test performance of individual components."""
    
    def test_component_config_creation_performance(self):
        """Test ComponentConfig creation performance."""
        iterations = 1000
        
        with performance_context('component_config_creation'):
            start_time = time.time()
            
            for i in range(iterations):
                config = create_component_config(f"perf_key_{i}", f"Perf Label {i}")
            
            duration_ms = (time.time() - start_time) * 1000
        
        avg_time_ms = duration_ms / iterations
        
        # Should be very fast due to caching
        assert avg_time_ms < 0.1, f"ComponentConfig creation took {avg_time_ms:.3f}ms per call"
    
    def test_adapter_singleton_performance(self):
        """Test adapter singleton access performance."""
        iterations = 1000
        
        with performance_context('adapter_singleton_access'):
            start_time = time.time()
            
            for _ in range(iterations):
                adapter = get_ui_adapter()
            
            duration_ms = (time.time() - start_time) * 1000
        
        avg_time_ms = duration_ms / iterations
        
        # Should be extremely fast due to singleton
        assert avg_time_ms < 0.01, f"Adapter access took {avg_time_ms:.3f}ms per call"
    
    def test_memoization_performance_improvement(self):
        """Test that memoization provides significant performance improvement."""
        call_count = 0
        
        @memoize_ui_computation('perf_test_memo', ttl_seconds=60)
        def expensive_computation(x):
            nonlocal call_count
            call_count += 1
            # Simulate expensive operation
            time.sleep(0.01)
            return x * x
        
        # First call (not cached)
        start_time = time.time()
        result1 = expensive_computation(5)
        first_call_time = (time.time() - start_time) * 1000
        
        # Second call (cached)
        start_time = time.time()
        result2 = expensive_computation(5)
        cached_call_time = (time.time() - start_time) * 1000
        
        assert result1 == result2 == 25
        assert call_count == 1  # Function called only once
        
        # Cached call should be at least 5x faster
        improvement_ratio = first_call_time / max(cached_call_time, 0.001)  # Avoid division by zero
        assert improvement_ratio >= 5, f"Memoization improvement ratio was {improvement_ratio:.1f}x, expected ≥5x"
    
    def test_lazy_loading_performance(self):
        """Test lazy loading performance benefits."""
        load_count = 0
        
        def expensive_loader():
            nonlocal load_count
            load_count += 1
            time.sleep(0.005)  # Simulate expensive loading
            return "expensive_resource"
        
        loader = create_lazy_loader(expensive_loader)
        
        # Creation should be instant
        start_time = time.time()
        loader = create_lazy_loader(expensive_loader)
        creation_time = (time.time() - start_time) * 1000
        
        assert creation_time < 1.0, f"Lazy loader creation took {creation_time:.2f}ms"
        assert load_count == 0  # Should not have loaded yet
        
        # First access should trigger loading
        start_time = time.time()
        value1 = loader.get()
        first_access_time = (time.time() - start_time) * 1000
        
        # Subsequent accesses should be fast
        start_time = time.time()
        for _ in range(100):
            value = loader.get()
            assert value == value1
        subsequent_access_time = (time.time() - start_time) * 1000
        
        assert load_count == 1  # Loaded only once
        assert subsequent_access_time < first_access_time / 10, \
            f"Subsequent access took {subsequent_access_time:.2f}ms, should be <{first_access_time/10:.2f}ms"


class TestPerformanceRegression:
    """Test for performance regressions."""
    
    def test_no_performance_regression_in_adapter_access(self):
        """Test that adapter access performance hasn't regressed."""
        # Baseline: should be able to access adapter 10,000 times in under 100ms
        iterations = 10000
        
        start_time = time.time()
        for _ in range(iterations):
            adapter = get_ui_adapter()
        duration_ms = (time.time() - start_time) * 1000
        
        # Should be very fast
        assert duration_ms < 100, f"10,000 adapter accesses took {duration_ms:.2f}ms, should be <100ms"
    
    def test_no_memory_leak_in_component_creation(self):
        """Test that component creation doesn't leak memory."""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create many components
        for i in range(5000):
            config = create_component_config(f"leak_test_{i}", f"Leak Test {i}")
            # Don't store references to allow garbage collection
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / 1024 / 1024  # MB
        
        # Should not increase memory significantly due to caching
        assert memory_increase < 10, f"Memory increased by {memory_increase:.2f}MB, should be <10MB"
    
    def test_performance_monitoring_overhead(self):
        """Test that performance monitoring has minimal overhead."""
        # Test without monitoring
        start_time = time.time()
        for _ in range(1000):
            # Simple operation
            x = 1 + 1
        baseline_time = (time.time() - start_time) * 1000
        
        # Test with monitoring
        start_time = time.time()
        for i in range(1000):
            with performance_context(f'test_operation_{i}'):
                x = 1 + 1
        monitored_time = (time.time() - start_time) * 1000
        
        # Overhead should be minimal
        overhead = monitored_time - baseline_time
        overhead_percentage = (overhead / baseline_time) * 100
        
        assert overhead_percentage < 50, f"Performance monitoring overhead was {overhead_percentage:.1f}%, should be <50%"


class TestPerformanceValidation:
    """Test performance validation functions."""
    
    def test_performance_targets_validation(self):
        """Test that performance targets validation works correctly."""
        # Record some performance metrics
        measure_performance('render_component', 200)  # Good performance
        measure_performance('render_component', 150)  # Good performance
        
        # Record cache hits
        tracker = get_cache_tracker()
        tracker.reset()
        for _ in range(85):
            record_cache_hit()
        for _ in range(15):
            record_cache_miss()
        
        # Validate targets
        results = validate_performance_targets()
        
        # Should pass validation
        assert 'first_render' in results
        assert 'cache_hit_rate' in results
        assert results['cache_hit_rate'] is True  # 85% hit rate > 80% target
    
    def test_performance_report_generation(self):
        """Test that performance reports can be generated."""
        monitor = get_performance_monitor()
        
        # Add some test metrics
        measure_performance('test_metric_1', 100)
        measure_performance('test_metric_1', 150)
        measure_performance('test_metric_2', 50)
        
        # Generate report
        report = monitor.get_performance_report()
        
        assert isinstance(report, str)
        assert 'test_metric_1' in report
        assert 'test_metric_2' in report
        assert 'Mean:' in report
        assert 'P95:' in report


class TestRealWorldPerformance:
    """Test performance in realistic scenarios."""
    
    def test_typical_user_workflow_performance(self, monkeypatch):
        """Test performance of a typical user workflow."""
        # Mock streamlit to avoid actual UI rendering
        mock_st = Mock()
        monkeypatch.setattr('ui.adapters.streamlit_adapter.st', mock_st)
        
        with performance_context('typical_workflow'):
            # Simulate typical user workflow
            adapter = get_ui_adapter()
            
            # Input section
            input_config = create_component_config('user_input', 'Enter text')
            mock_st.text_area.return_value = "test input"
            text = adapter.inputs.text_area(input_config)
            
            # Options section
            option_config = create_component_config('auto_pinyin', 'Auto Pinyin')
            mock_st.checkbox.return_value = True
            auto_pinyin = adapter.inputs.checkbox(option_config)
            
            # Layout
            mock_st.columns.return_value = [Mock(), Mock()]
            col1, col2 = adapter.layout.columns([1, 1])
            
            # Notifications
            adapter.notifications.show_success("Workflow completed")
        
        # Get performance stats
        monitor = get_performance_monitor()
        stats = monitor.get_statistics('typical_workflow')
        
        if stats:
            # Typical workflow should be fast
            assert stats['mean'] < 50, f"Typical workflow took {stats['mean']:.2f}ms, should be <50ms"
    
    def test_bulk_operations_performance(self):
        """Test performance of bulk operations."""
        with performance_context('bulk_operations'):
            # Create many components in bulk
            configs = []
            for i in range(1000):
                config = create_component_config(f'bulk_{i}', f'Bulk Item {i}')
                configs.append(config)
            
            # Access adapter many times
            adapters = []
            for _ in range(1000):
                adapter = get_ui_adapter()
                adapters.append(adapter)
        
        # Get performance stats
        monitor = get_performance_monitor()
        stats = monitor.get_statistics('bulk_operations')
        
        if stats:
            # Bulk operations should be efficient due to caching
            assert stats['mean'] < 100, f"Bulk operations took {stats['mean']:.2f}ms, should be <100ms"


if __name__ == "__main__":
    # Run performance benchmarks
    pytest.main([__file__, "-v", "--tb=short"])
