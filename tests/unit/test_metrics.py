"""
Unit tests for services/metrics.py
Tests performance metrics collection, timing, memory tracking, and analytics.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, Mock

from services.metrics import (
    MetricType, TimingPhase, TimingMetric, MemoryMetric, CacheMetric, RenderMetric,
    PerformanceTargets, MetricsCollector, get_metrics_collector,
    start_timing, finish_timing, record_memory_usage, record_cache_operation,
    record_render_operation, get_performance_summary, timing_context, timed_operation
)


class TestTimingMetric:
    """Test timing metric functionality."""
    
    def test_timing_metric_creation(self):
        """Test timing metric creation."""
        metric = TimingMetric(
            name="test_operation",
            phase=TimingPhase.RENDER_PREVIEW,
            start_time=time.time(),
            metadata={"cards_count": 10}
        )
        
        assert metric.name == "test_operation"
        assert metric.phase == TimingPhase.RENDER_PREVIEW
        assert metric.start_time > 0
        assert metric.end_time is None
        assert metric.duration_ms is None
        assert metric.success is True
        assert metric.metadata["cards_count"] == 10
    
    def test_timing_metric_finish(self):
        """Test timing metric completion."""
        start_time = time.time()
        metric = TimingMetric(
            name="test_operation",
            phase=TimingPhase.DATA_PROCESSING,
            start_time=start_time
        )
        
        # Wait a bit and finish
        time.sleep(0.01)
        duration = metric.finish(success=True, metadata={"result": "success"})
        
        assert metric.end_time > start_time
        assert metric.duration_ms > 0
        assert duration == metric.duration_ms
        assert metric.success is True
        assert metric.metadata["result"] == "success"
    
    def test_timing_metric_to_dict(self):
        """Test timing metric serialization."""
        metric = TimingMetric(
            name="test_op",
            phase=TimingPhase.CACHE_OPERATION,
            start_time=time.time()
        )
        metric.finish()
        
        data = metric.to_dict()
        assert data["name"] == "test_op"
        assert data["phase"] == TimingPhase.CACHE_OPERATION
        assert "start_time" in data
        assert "duration_ms" in data


class TestMemoryMetric:
    """Test memory metric functionality."""
    
    def test_memory_metric_creation(self):
        """Test memory metric creation."""
        metric = MemoryMetric(
            timestamp=time.time(),
            process_memory_mb=25.5,
            system_memory_mb=8192.0,
            memory_percent=65.2,
            gc_collections={"gen_0": 10, "gen_1": 5, "gen_2": 1},
            metadata={"source": "test"}
        )
        
        assert metric.process_memory_mb == 25.5
        assert metric.system_memory_mb == 8192.0
        assert metric.memory_percent == 65.2
        assert metric.gc_collections["gen_0"] == 10
        assert metric.metadata["source"] == "test"
    
    def test_memory_metric_to_dict(self):
        """Test memory metric serialization."""
        metric = MemoryMetric(
            timestamp=time.time(),
            process_memory_mb=30.0,
            system_memory_mb=4096.0,
            memory_percent=50.0
        )
        
        data = metric.to_dict()
        assert data["process_memory_mb"] == 30.0
        assert data["system_memory_mb"] == 4096.0
        assert "timestamp" in data


class TestCacheMetric:
    """Test cache metric functionality."""
    
    def test_cache_metric_creation(self):
        """Test cache metric creation."""
        metric = CacheMetric(
            cache_type="preview",
            operation="get",
            hit=True,
            key_size_bytes=128,
            value_size_bytes=2048,
            access_time_ms=5.2,
            metadata={"cache_level": "L1"}
        )
        
        assert metric.cache_type == "preview"
        assert metric.operation == "get"
        assert metric.hit is True
        assert metric.key_size_bytes == 128
        assert metric.value_size_bytes == 2048
        assert metric.access_time_ms == 5.2
        assert metric.metadata["cache_level"] == "L1"


class TestRenderMetric:
    """Test render metric functionality."""
    
    def test_render_metric_creation(self):
        """Test render metric creation."""
        metric = RenderMetric(
            render_type="preview_page",
            cards_count=20,
            page_number=2,
            duration_ms=150.5,
            cache_hit=False,
            memory_used_mb=15.2,
            output_size_bytes=4096,
            metadata={"format": "html"}
        )
        
        assert metric.render_type == "preview_page"
        assert metric.cards_count == 20
        assert metric.page_number == 2
        assert metric.duration_ms == 150.5
        assert metric.cache_hit is False
        assert metric.memory_used_mb == 15.2
        assert metric.output_size_bytes == 4096
        assert metric.metadata["format"] == "html"


class TestPerformanceTargets:
    """Test performance targets."""
    
    def test_performance_targets_constants(self):
        """Test performance target constants."""
        assert PerformanceTargets.FIRST_RENDER_MAX_MS == 500
        assert PerformanceTargets.CACHED_RENDER_MAX_MS == 100
        assert PerformanceTargets.LAYOUT_COMPUTATION_MAX_MS == 50
        assert PerformanceTargets.CACHE_ACCESS_MAX_MS == 10
        assert PerformanceTargets.MAX_MEMORY_MB == 50
        assert PerformanceTargets.MIN_CACHE_HIT_RATE == 0.8


class TestMetricsCollector:
    """Test metrics collector functionality."""
    
    @patch('services.metrics.get_feature_flag')
    def test_collector_creation(self, mock_feature_flag):
        """Test collector creation."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector(max_metrics=500, analysis_window_minutes=5)
        
        assert collector._max_metrics == 500
        assert collector._analysis_window_minutes == 5
        assert len(collector._timing_metrics) == 0
        assert len(collector._active_timings) == 0
        assert collector._enabled is True
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_timing_measurement(self, mock_feature_flag):
        """Test timing measurement."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Start timing
        timing_id = collector.start_timing(
            "test_operation",
            TimingPhase.RENDER_PREVIEW,
            {"cards_count": 10}
        )
        
        assert timing_id != ""
        assert timing_id in collector._active_timings
        
        # Wait a bit
        time.sleep(0.01)
        
        # Finish timing
        duration = collector.finish_timing(timing_id, success=True, metadata={"result": "success"})
        
        assert duration > 0
        assert timing_id not in collector._active_timings
        assert len(collector._timing_metrics) == 1
        
        timing = collector._timing_metrics[0]
        assert timing.name == "test_operation"
        assert timing.phase == TimingPhase.RENDER_PREVIEW
        assert timing.success is True
        assert timing.metadata["cards_count"] == 10
        assert timing.metadata["result"] == "success"
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.psutil.Process')
    @patch('services.metrics.psutil.virtual_memory')
    @patch('services.metrics.get_feature_flag')
    def test_memory_recording(self, mock_feature_flag, mock_virtual_memory, mock_process):
        """Test memory usage recording."""
        # Enable metrics and memory monitoring
        def feature_flag_side_effect(flag, default):
            if flag == 'metrics_collection':
                return True
            elif flag == 'memory_monitoring':
                return True  # Enable memory monitoring for the test
            return default
        mock_feature_flag.side_effect = feature_flag_side_effect
        
        # Mock psutil
        mock_memory_info = Mock()
        mock_memory_info.rss = 50 * 1024 * 1024  # 50 MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        mock_vm = Mock()
        mock_vm.total = 8 * 1024 * 1024 * 1024  # 8 GB
        mock_vm.percent = 60.0
        mock_virtual_memory.return_value = mock_vm
        
        collector = MetricsCollector()
        # Stop background monitoring to avoid interference
        collector.shutdown()
        
        # Record memory
        metric = collector.record_memory_usage({"source": "test"})
        
        assert metric is not None
        assert metric.process_memory_mb == 50.0
        assert metric.system_memory_mb == 8192.0
        assert metric.memory_percent == 60.0
        assert metric.metadata["source"] == "test"
        assert len(collector._memory_metrics) >= 1  # May have background metrics too
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_cache_operation_recording(self, mock_feature_flag):
        """Test cache operation recording."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Record cache operations
        collector.record_cache_operation(
            cache_type="preview",
            operation="get",
            hit=True,
            key_size_bytes=128,
            value_size_bytes=2048,
            access_time_ms=3.5,
            metadata={"level": "L1"}
        )
        
        collector.record_cache_operation(
            cache_type="preview",
            operation="get",
            hit=False,
            access_time_ms=15.2
        )
        
        assert len(collector._cache_metrics) == 2
        
        # Check first metric
        metric1 = collector._cache_metrics[0]
        assert metric1.cache_type == "preview"
        assert metric1.operation == "get"
        assert metric1.hit is True
        assert metric1.key_size_bytes == 128
        assert metric1.access_time_ms == 3.5
        
        # Check second metric
        metric2 = collector._cache_metrics[1]
        assert metric2.hit is False
        assert metric2.access_time_ms == 15.2
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_render_operation_recording(self, mock_feature_flag):
        """Test render operation recording."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Record render operation
        collector.record_render_operation(
            render_type="preview_page",
            cards_count=25,
            page_number=3,
            duration_ms=120.5,
            cache_hit=True,
            memory_used_mb=20.0,
            output_size_bytes=8192,
            metadata={"format": "html"}
        )
        
        assert len(collector._render_metrics) == 1
        
        metric = collector._render_metrics[0]
        assert metric.render_type == "preview_page"
        assert metric.cards_count == 25
        assert metric.page_number == 3
        assert metric.duration_ms == 120.5
        assert metric.cache_hit is True
        assert metric.memory_used_mb == 20.0
        assert metric.output_size_bytes == 8192
        assert metric.metadata["format"] == "html"
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_performance_summary(self, mock_feature_flag):
        """Test performance summary generation."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Add some test data
        timing_id = collector.start_timing("test_op", TimingPhase.RENDER_PREVIEW)
        time.sleep(0.01)
        collector.finish_timing(timing_id)
        
        collector.record_cache_operation("preview", "get", True)
        collector.record_cache_operation("preview", "get", False)
        
        collector.record_render_operation("preview", 10, 1, 80.0, True)
        
        # Get summary
        summary = collector.get_performance_summary()
        
        assert "timing_analysis" in summary
        assert "cache_analysis" in summary
        assert "render_analysis" in summary
        assert "performance_targets" in summary
        assert "statistics" in summary
        
        # Check cache analysis
        cache_analysis = summary["cache_analysis"]
        assert cache_analysis["count"] == 2
        assert cache_analysis["overall_hit_rate"] == 0.5
        
        # Check performance targets
        targets = summary["performance_targets"]
        assert "cache_hit_rate" in targets
        assert "memory_usage" in targets
        assert "render_performance" in targets
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_metrics_data_retrieval(self, mock_feature_flag):
        """Test metrics data retrieval."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Add test data
        timing_id = collector.start_timing("test", TimingPhase.CACHE_OPERATION)
        collector.finish_timing(timing_id)
        collector.record_cache_operation("test", "get", True)
        
        # Get all data
        data = collector.get_metrics_data()
        assert "timing" in data
        assert "cache" in data
        assert len(data["timing"]) == 1
        assert len(data["cache"]) == 1
        
        # Get specific type
        timing_data = collector.get_metrics_data(MetricType.TIMING)
        assert "timing" in timing_data
        assert "cache" not in timing_data
        
        # Get limited data
        limited_data = collector.get_metrics_data(limit=1)
        assert len(limited_data["timing"]) <= 1
        
        # Cleanup
        collector.shutdown()
    
    @patch('services.metrics.get_feature_flag')
    def test_performance_target_violations(self, mock_feature_flag):
        """Test performance target violation detection."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Record slow render (should violate target)
        timing_id = collector.start_timing("slow_render", TimingPhase.RENDER_PREVIEW)
        time.sleep(0.01)  # Small delay
        # Manually set a high duration to simulate slow operation
        timing = collector._active_timings[timing_id]
        timing.start_time = time.time() - 0.6  # 600ms ago
        collector.finish_timing(timing_id)
        
        # Should have recorded a violation
        assert collector._stats['performance_violations'] > 0
        
        # Cleanup
        collector.shutdown()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.metrics.get_metrics_collector')
    def test_start_timing_function(self, mock_get_collector):
        """Test start timing convenience function."""
        mock_collector = Mock()
        mock_collector.start_timing.return_value = "timing_123"
        mock_get_collector.return_value = mock_collector
        
        timing_id = start_timing("test_op", TimingPhase.DATA_PROCESSING, {"test": "data"})
        
        assert timing_id == "timing_123"
        mock_collector.start_timing.assert_called_once_with(
            "test_op", TimingPhase.DATA_PROCESSING, {"test": "data"}
        )
    
    @patch('services.metrics.get_metrics_collector')
    def test_finish_timing_function(self, mock_get_collector):
        """Test finish timing convenience function."""
        mock_collector = Mock()
        mock_collector.finish_timing.return_value = 150.5
        mock_get_collector.return_value = mock_collector
        
        duration = finish_timing("timing_123", success=True, metadata={"result": "ok"})
        
        assert duration == 150.5
        mock_collector.finish_timing.assert_called_once_with(
            "timing_123", True, {"result": "ok"}
        )
    
    @patch('services.metrics.get_metrics_collector')
    def test_record_cache_operation_function(self, mock_get_collector):
        """Test record cache operation convenience function."""
        mock_collector = Mock()
        mock_get_collector.return_value = mock_collector
        
        record_cache_operation("preview", "set", False, key_size_bytes=256)
        
        mock_collector.record_cache_operation.assert_called_once_with(
            "preview", "set", False, key_size_bytes=256
        )


class TestTimingContext:
    """Test timing context manager."""
    
    @patch('services.metrics.get_metrics_collector')
    def test_timing_context_success(self, mock_get_collector):
        """Test timing context manager success case."""
        mock_collector = Mock()
        mock_collector.start_timing.return_value = "timing_456"
        mock_get_collector.return_value = mock_collector
        
        with timing_context("test_operation", TimingPhase.LAYOUT_COMPUTATION, {"test": "data"}):
            pass  # Simulate work
        
        mock_collector.start_timing.assert_called_once_with(
            "test_operation", TimingPhase.LAYOUT_COMPUTATION, {"test": "data"}
        )
        mock_collector.finish_timing.assert_called_once_with("timing_456", True, {})
    
    @patch('services.metrics.get_metrics_collector')
    def test_timing_context_exception(self, mock_get_collector):
        """Test timing context manager exception handling."""
        mock_collector = Mock()
        mock_collector.start_timing.return_value = "timing_789"
        mock_get_collector.return_value = mock_collector
        
        try:
            with timing_context("failing_operation", TimingPhase.EXPORT_GENERATION):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Should have called finish_timing with success=False and error metadata
        mock_collector.finish_timing.assert_called_once()
        call_args = mock_collector.finish_timing.call_args
        assert call_args[0][0] == "timing_789"  # timing_id
        assert call_args[0][1] is False  # success
        assert "error_type" in call_args[0][2]  # error metadata
        assert call_args[0][2]["error_type"] == "ValueError"


class TestTimedOperationDecorator:
    """Test timed operation decorator."""
    
    @patch('services.metrics.get_metrics_collector')
    def test_timed_operation_decorator(self, mock_get_collector):
        """Test timed operation decorator."""
        mock_collector = Mock()
        mock_collector.start_timing.return_value = "timing_decorated"
        mock_get_collector.return_value = mock_collector
        
        @timed_operation("decorated_function", TimingPhase.DATA_PROCESSING)
        def test_function(x, y):
            return x + y
        
        result = test_function(5, 3)
        
        assert result == 8
        mock_collector.start_timing.assert_called_once()
        mock_collector.finish_timing.assert_called_once()
        
        # Check that function name is in metadata
        start_call_args = mock_collector.start_timing.call_args
        assert start_call_args[0][0] == "decorated_function"
        assert start_call_args[0][1] == TimingPhase.DATA_PROCESSING
        assert start_call_args[0][2]["function"] == "test_function"


class TestIntegration:
    """Test integration scenarios."""
    
    @patch('services.metrics.get_feature_flag')
    def test_full_metrics_workflow(self, mock_feature_flag):
        """Test complete metrics collection workflow."""
        mock_feature_flag.return_value = True
        collector = MetricsCollector()
        
        # Simulate a complete operation workflow
        
        # 1. Start timing for overall operation
        main_timing = collector.start_timing("full_operation", TimingPhase.RENDER_PREVIEW)
        
        # 2. Record cache operations
        collector.record_cache_operation("preview", "get", False)  # Cache miss
        
        # 3. Start sub-operation timing
        layout_timing = collector.start_timing("layout_calc", TimingPhase.LAYOUT_COMPUTATION)
        time.sleep(0.01)
        collector.finish_timing(layout_timing)
        
        # 4. Record render operation
        collector.record_render_operation("preview_page", 15, 1, 95.0, False, memory_used_mb=18.5)
        
        # 5. Record successful cache store
        collector.record_cache_operation("preview", "set", True, value_size_bytes=4096)
        
        # 6. Finish main timing
        time.sleep(0.01)
        collector.finish_timing(main_timing)
        
        # Verify collected metrics
        assert len(collector._timing_metrics) == 2  # main + layout
        assert len(collector._cache_metrics) == 2   # get + set
        assert len(collector._render_metrics) == 1  # render
        
        # Get performance summary
        summary = collector.get_performance_summary()
        
        # Verify summary contains expected data
        assert summary["timing_analysis"]["count"] == 2
        assert summary["cache_analysis"]["count"] == 2
        assert summary["cache_analysis"]["overall_hit_rate"] == 0.5  # 1 hit out of 2
        assert summary["render_analysis"]["count"] == 1
        
        # Verify statistics
        stats = summary["statistics"]
        assert stats["timing_measurements"] == 2
        assert stats["cache_operations"] == 2
        assert stats["render_operations"] == 1
        
        # Cleanup
        collector.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
