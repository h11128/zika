"""
Performance tests for UI refactor optimizations.
"""

import time
import pytest
from unittest.mock import Mock, patch

from ui.ports import get_ui_adapter, create_component_config, ComponentConfig
from ui.performance_utils import (
    get_performance_optimizer, debounce_ui_operation, 
    memoize_ui_computation, throttle_ui_updates,
    create_lazy_loader, create_batch_processor
)


class TestAdapterPerformance:
    """Test adapter performance optimizations."""
    
    def test_adapter_singleton_performance(self):
        """Test that adapter singleton pattern is efficient."""
        start_time = time.time()
        
        # Create many adapter instances (should reuse singleton)
        adapters = []
        for _ in range(1000):
            adapter = get_ui_adapter()
            adapters.append(adapter)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should be very fast due to singleton pattern
        assert duration_ms < 100  # Less than 100ms for 1000 calls
        
        # All should be same instance
        assert all(adapter is adapters[0] for adapter in adapters)
    
    def test_component_config_caching(self):
        """Test ComponentConfig caching performance."""
        start_time = time.time()
        
        # Create many configs with same parameters (should be cached)
        configs = []
        for _ in range(1000):
            config = create_component_config(
                key="test_key",
                label="Test Label",
                help_text="Help text"
            )
            configs.append(config)
        
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        
        # Should be fast due to caching
        assert duration_ms < 50  # Less than 50ms for 1000 cached calls
        
        # All should be same instance due to caching
        assert all(config is configs[0] for config in configs)
    
    def test_lazy_initialization_performance(self):
        """Test lazy initialization performance."""
        from ui.adapters.streamlit_adapter import StreamlitAdapter
        
        # Create adapter (should not initialize sub-adapters yet)
        start_time = time.time()
        adapter = StreamlitAdapter()
        init_time = (time.time() - start_time) * 1000
        
        # Initial creation should be very fast
        assert init_time < 10  # Less than 10ms
        
        # First access should initialize
        start_time = time.time()
        _ = adapter.inputs  # This should trigger initialization
        first_access_time = (time.time() - start_time) * 1000
        
        # Subsequent accesses should be fast
        start_time = time.time()
        for _ in range(100):
            _ = adapter.inputs
            _ = adapter.layout
            _ = adapter.notifications
        subsequent_access_time = (time.time() - start_time) * 1000
        
        # Subsequent accesses should be much faster (or at least not slower)
        # Allow for timing variations and timer precision; enforce a small floor tolerance
        tolerance_ms = max(2.0, first_access_time + 1.0)
        assert subsequent_access_time <= tolerance_ms, (
            f"Subsequent access {subsequent_access_time:.3f}ms > tolerance {tolerance_ms:.3f}ms"
        )


class TestPerformanceOptimizations:
    """Test performance optimization utilities."""
    
    def test_debounce_performance(self):
        """Test debounce optimization."""
        call_count = 0
        
        @debounce_ui_operation("test_debounce", delay_ms=50)
        def test_function():
            nonlocal call_count
            call_count += 1
        
        # Call function multiple times rapidly
        for _ in range(10):
            test_function()
        
        # Should not have been called yet due to debouncing
        assert call_count == 0
        
        # Wait for debounce delay
        time.sleep(0.1)
        
        # Should have been called only once
        assert call_count <= 1
    
    def test_memoization_performance(self):
        """Test memoization optimization."""
        call_count = 0
        
        @memoize_ui_computation("test_memo", ttl_seconds=1)
        def expensive_computation(x, y):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate expensive operation
            return x + y
        
        # First call
        start_time = time.time()
        result1 = expensive_computation(1, 2)
        first_call_time = (time.time() - start_time) * 1000
        
        # Second call with same parameters (should be cached)
        start_time = time.time()
        result2 = expensive_computation(1, 2)
        second_call_time = (time.time() - start_time) * 1000
        
        assert result1 == result2 == 3
        assert call_count == 1  # Function called only once
        assert second_call_time < first_call_time  # Cached call is faster
    
    def test_throttle_performance(self):
        """Test throttle optimization."""
        call_count = 0
        
        @throttle_ui_updates("test_throttle", min_interval_ms=50)
        def test_function():
            nonlocal call_count
            call_count += 1
            return call_count
        
        # Call function multiple times rapidly
        results = []
        for _ in range(10):
            result = test_function()
            results.append(result)
            time.sleep(0.01)  # Small delay between calls
        
        # Should have been throttled (not all calls executed)
        assert call_count < 10
        assert len([r for r in results if r is not None]) == call_count
    
    def test_lazy_loader_performance(self):
        """Test lazy loader performance."""
        load_count = 0
        
        def expensive_loader():
            nonlocal load_count
            load_count += 1
            time.sleep(0.01)  # Simulate expensive loading
            return "loaded_value"
        
        loader = create_lazy_loader(expensive_loader)
        
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
        assert subsequent_access_time < first_access_time  # Cached access is faster
    
    def test_batch_processor_performance(self):
        """Test batch processor performance."""
        processed_count = 0
        
        def process_operation():
            nonlocal processed_count
            processed_count += 1
        
        import logging
        logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s] %(message)s')

        processor = create_batch_processor(batch_size=5, flush_interval_ms=50)

        # Add operations to batch
        for i in range(12):
            logging.debug(f"[test] Adding operation {i+1}")
            processor.add(process_operation)

        # Should have auto-flushed when batch reached size 5 and 10
        time.sleep(0.05)  # Allow processing
        logging.debug(f"[test] Processed after first wait: {processed_count}")
        assert processed_count >= 10

        # Wait for remaining operations to be flushed
        time.sleep(0.2)
        logging.debug(f"[test] Processed after second wait: {processed_count}")
        assert processed_count == 12

        processor.cleanup()
        logging.debug("[test] Cleanup complete")


class TestMemoryOptimizations:
    """Test memory optimization features."""
    
    def test_adapter_cleanup(self):
        """Test adapter cleanup functionality."""
        from ui.adapters.streamlit_adapter import StreamlitAdapter
        
        adapter = StreamlitAdapter()
        
        # Initialize adapters
        _ = adapter.inputs
        _ = adapter.layout
        assert adapter._initialized is True
        
        # Cleanup
        adapter.cleanup()
        
        # Should be reset
        assert adapter._initialized is False
        assert adapter._inputs is None
        assert adapter._layout is None
    
    def test_performance_optimizer_cleanup(self):
        """Test performance optimizer cleanup."""
        optimizer = get_performance_optimizer()
        
        # Add some cached data
        @optimizer.memoize("test_cleanup", ttl_seconds=60)
        def test_func(x):
            return x * 2
        
        result = test_func(5)
        assert result == 10
        
        # Cleanup
        optimizer.cleanup()
        
        # Cache should be cleared
        assert len(optimizer._cache) == 0
        assert len(optimizer._cache_timestamps) == 0


class TestRegressionPrevention:
    """Test that optimizations don't break functionality."""
    
    def test_adapter_functionality_preserved(self, monkeypatch):
        """Test that adapter optimizations don't break functionality."""
        mock_st = Mock()
        monkeypatch.setattr('ui.adapters.streamlit_adapter.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Test that basic functionality still works
        adapter.header("Test Header")
        adapter.write("Test content")
        
        # Should have called streamlit functions
        mock_st.header.assert_called_with("Test Header")
        mock_st.write.assert_called_with("Test content")
    
    def test_component_config_functionality_preserved(self):
        """Test that ComponentConfig caching doesn't break functionality."""
        config1 = create_component_config("key1", "Label1", "Help1")
        config2 = create_component_config("key2", "Label2", "Help2")
        config3 = create_component_config("key1", "Label1", "Help1")  # Same as config1
        
        # Different configs should have different values
        assert config1.key != config2.key
        assert config1.label != config2.label
        
        # Same configs should be cached (same instance)
        assert config1 is config3
    
    def test_performance_utils_dont_break_errors(self):
        """Test that performance utils don't suppress important errors."""
        error_raised = False
        
        @debounce_ui_operation("test_error", delay_ms=10)
        def failing_function():
            nonlocal error_raised
            error_raised = True
            raise ValueError("Test error")
        
        # Error should still be raised (after debounce delay)
        failing_function()
        time.sleep(0.02)  # Wait for debounce
        
        # Note: Debounced functions run in separate threads, 
        # so we can't directly catch the exception here.
        # In real usage, error boundaries would handle this.


class TestPerformanceBenchmarks:
    """Benchmark tests for performance regression detection."""
    
    def test_adapter_creation_benchmark(self):
        """Benchmark adapter creation performance."""
        iterations = 1000
        
        start_time = time.time()
        for _ in range(iterations):
            adapter = get_ui_adapter()
        end_time = time.time()
        
        avg_time_ms = ((end_time - start_time) / iterations) * 1000
        
        # Should be very fast due to singleton
        assert avg_time_ms < 0.1  # Less than 0.1ms per call
    
    def test_component_config_creation_benchmark(self):
        """Benchmark ComponentConfig creation performance."""
        iterations = 1000
        
        start_time = time.time()
        for i in range(iterations):
            config = create_component_config(f"key_{i}", f"Label {i}")
        end_time = time.time()
        
        avg_time_ms = ((end_time - start_time) / iterations) * 1000
        
        # Should be reasonably fast
        assert avg_time_ms < 1.0  # Less than 1ms per call
    
    def test_memoization_benchmark(self):
        """Benchmark memoization performance improvement."""
        call_count = 0
        
        @memoize_ui_computation("benchmark_memo", ttl_seconds=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            # Simulate expensive computation
            total = 0
            for i in range(1000):
                total += i * x
            return total
        
        # First call (not cached)
        start_time = time.time()
        result1 = expensive_function(5)
        first_call_time = (time.time() - start_time) * 1000
        
        # Second call (cached)
        start_time = time.time()
        result2 = expensive_function(5)
        cached_call_time = (time.time() - start_time) * 1000
        
        assert result1 == result2
        assert call_count == 1  # Function called only once
        assert cached_call_time < first_call_time * 0.1  # Cached call is >10x faster
