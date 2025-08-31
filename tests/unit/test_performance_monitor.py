"""
Unit tests for services/performance_monitor.py
Tests performance monitoring, benchmarking, and regression detection.
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from services.performance_monitor import (
    PerformanceLevel, BenchmarkType, PerformanceBenchmark, PerformanceMeasurement,
    PerformanceStats, RegressionAlert, PerformanceMonitor,
    get_performance_monitor, measure_performance, benchmark, get_performance_summary,
    set_performance_baseline
)


class TestPerformanceBenchmark:
    """Test performance benchmark functionality."""
    
    def test_benchmark_creation(self):
        """Test benchmark creation."""
        benchmark = PerformanceBenchmark(
            name="test_benchmark",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0,
            description="Test benchmark"
        )
        
        assert benchmark.name == "test_benchmark"
        assert benchmark.type == BenchmarkType.RENDER
        assert benchmark.target_ms == 100.0
        assert benchmark.warning_ms == 300.0
        assert benchmark.critical_ms == 500.0


class TestPerformanceMeasurement:
    """Test performance measurement functionality."""
    
    def test_measurement_creation(self):
        """Test measurement creation."""
        measurement = PerformanceMeasurement(
            benchmark_name="test",
            duration_ms=150.0,
            timestamp=time.time(),
            level=PerformanceLevel.GOOD,
            metadata={"component": "preview"}
        )
        
        assert measurement.benchmark_name == "test"
        assert measurement.duration_ms == 150.0
        assert measurement.level == PerformanceLevel.GOOD
        assert measurement.metadata["component"] == "preview"
    
    def test_measurement_to_dict(self):
        """Test measurement serialization."""
        measurement = PerformanceMeasurement(
            benchmark_name="test",
            duration_ms=150.0,
            timestamp=time.time(),
            level=PerformanceLevel.GOOD
        )
        
        data = measurement.to_dict()
        assert data["benchmark_name"] == "test"
        assert data["duration_ms"] == 150.0
        assert data["level"] == "good"


class TestPerformanceStats:
    """Test performance statistics functionality."""
    
    def test_stats_creation(self):
        """Test stats creation."""
        stats = PerformanceStats(
            benchmark_name="test",
            count=100,
            avg_ms=150.0,
            min_ms=50.0,
            max_ms=300.0,
            p50_ms=140.0,
            p95_ms=250.0,
            p99_ms=290.0,
            current_level=PerformanceLevel.GOOD,
            trend="stable"
        )
        
        assert stats.benchmark_name == "test"
        assert stats.count == 100
        assert stats.avg_ms == 150.0
        assert stats.current_level == PerformanceLevel.GOOD
        assert stats.trend == "stable"
    
    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = PerformanceStats(
            benchmark_name="test",
            count=100,
            avg_ms=150.0,
            min_ms=50.0,
            max_ms=300.0,
            p50_ms=140.0,
            p95_ms=250.0,
            p99_ms=290.0,
            current_level=PerformanceLevel.GOOD,
            trend="stable"
        )
        
        data = stats.to_dict()
        assert data["benchmark_name"] == "test"
        assert data["count"] == 100
        assert data["current_level"] == "good"


class TestPerformanceMonitor:
    """Test performance monitor functionality."""
    
    def test_monitor_creation(self):
        """Test monitor creation."""
        monitor = PerformanceMonitor()
        assert len(monitor._benchmarks) > 0  # Should have default benchmarks
    
    def test_register_benchmark(self):
        """Test benchmark registration."""
        monitor = PerformanceMonitor()
        
        benchmark = PerformanceBenchmark(
            name="custom_test",
            type=BenchmarkType.PROCESSING,
            target_ms=100.0,
            warning_ms=200.0,
            critical_ms=500.0
        )
        
        monitor.register_benchmark(benchmark)
        assert "custom_test" in monitor._benchmarks
        assert monitor._benchmarks["custom_test"] == benchmark
    
    def test_measure_performance(self):
        """Test performance measurement."""
        monitor = PerformanceMonitor()
        
        # Register a benchmark
        benchmark = PerformanceBenchmark(
            name="test_measure",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0
        )
        monitor.register_benchmark(benchmark)
        
        # Measure performance
        measurement = monitor.measure("test_measure", 150.0, {"component": "test"})
        
        assert measurement.benchmark_name == "test_measure"
        assert measurement.duration_ms == 150.0
        assert measurement.level == PerformanceLevel.GOOD  # 150ms is between target and warning
        assert measurement.metadata["component"] == "test"
        
        # Check that measurement was stored
        assert len(monitor._measurements) == 1
        assert len(monitor._measurements_by_benchmark["test_measure"]) == 1
    
    def test_auto_register_benchmark(self):
        """Test auto-registration of benchmarks."""
        monitor = PerformanceMonitor()
        
        # Measure with unknown benchmark
        measurement = monitor.measure("unknown_benchmark", 200.0)
        
        assert measurement.benchmark_name == "unknown_benchmark"
        assert "unknown_benchmark" in monitor._benchmarks
        
        # Check auto-registered benchmark properties
        benchmark = monitor._benchmarks["unknown_benchmark"]
        assert benchmark.type == BenchmarkType.PROCESSING
        assert benchmark.target_ms <= 200.0
    
    def test_performance_classification(self):
        """Test performance level classification."""
        monitor = PerformanceMonitor()
        
        benchmark = PerformanceBenchmark(
            name="test_classify",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0
        )
        monitor.register_benchmark(benchmark)
        
        # Test different performance levels
        excellent = monitor.measure("test_classify", 80.0)  # Below target
        assert excellent.level == PerformanceLevel.EXCELLENT
        
        good = monitor.measure("test_classify", 120.0)  # Above target, below warning
        assert good.level == PerformanceLevel.GOOD
        
        slow = monitor.measure("test_classify", 400.0)  # Above warning, below critical
        assert slow.level == PerformanceLevel.SLOW
        
        critical = monitor.measure("test_classify", 600.0)  # Above critical
        assert critical.level == PerformanceLevel.CRITICAL
    
    def test_get_stats(self):
        """Test statistics calculation."""
        monitor = PerformanceMonitor()
        
        benchmark = PerformanceBenchmark(
            name="test_stats",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0
        )
        monitor.register_benchmark(benchmark)
        
        # Add multiple measurements
        durations = [80, 90, 100, 110, 120, 150, 200, 250, 300, 350]
        for duration in durations:
            monitor.measure("test_stats", duration)
        
        # Get statistics
        stats = monitor.get_stats("test_stats")
        
        assert stats is not None
        assert stats.benchmark_name == "test_stats"
        assert stats.count == len(durations)
        assert stats.avg_ms == sum(durations) / len(durations)
        assert stats.min_ms == min(durations)
        assert stats.max_ms == max(durations)
        assert stats.p50_ms == 135.0  # Median of sorted list [80,90,100,110,120,150,200,250,300,350]
    
    def test_baseline_and_regression_detection(self):
        """Test baseline setting and regression detection."""
        monitor = PerformanceMonitor()
        
        benchmark = PerformanceBenchmark(
            name="test_regression",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0
        )
        monitor.register_benchmark(benchmark)
        
        # Set baseline
        monitor.set_baseline("test_regression", 100.0)
        assert monitor._baselines["test_regression"] == 100.0
        
        # Measure within acceptable range
        monitor.measure("test_regression", 110.0)  # 10% increase, below threshold
        assert len(monitor._alerts) == 0
        
        # Measure with regression
        monitor.measure("test_regression", 130.0)  # 30% increase, above threshold
        assert len(monitor._alerts) == 1
        
        alert = monitor._alerts[0]
        assert alert.benchmark_name == "test_regression"
        assert alert.regression_percent == 30.0
        assert alert.severity == "warning"
    
    def test_trend_analysis(self):
        """Test performance trend analysis."""
        monitor = PerformanceMonitor()
        
        benchmark = PerformanceBenchmark(
            name="test_trend",
            type=BenchmarkType.RENDER,
            target_ms=100.0,
            warning_ms=300.0,
            critical_ms=500.0
        )
        monitor.register_benchmark(benchmark)
        
        # Add measurements with improving trend
        improving_durations = [200, 190, 180, 170, 160, 150, 140, 130, 120, 110]
        for duration in improving_durations:
            monitor.measure("test_trend", duration)
        
        stats = monitor.get_stats("test_trend")
        assert stats.trend == "improving"
        
        # Clear and add measurements with degrading trend
        monitor._measurements_by_benchmark["test_trend"].clear()
        degrading_durations = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
        for duration in degrading_durations:
            monitor.measure("test_trend", duration)
        
        stats = monitor.get_stats("test_trend")
        assert stats.trend == "degrading"
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        monitor = PerformanceMonitor()
        
        # Add some measurements
        monitor.measure("preview_render", 150.0)
        monitor.measure("export_pdf", 2000.0)
        
        summary = monitor.get_performance_summary()
        
        assert "health_status" in summary
        assert "total_benchmarks" in summary
        assert "total_measurements" in summary
        assert "benchmarks" in summary
        assert "alerts" in summary
        assert "baselines" in summary
        
        # Should have measurements
        assert summary["total_measurements"] >= 2
    
    def test_benchmark_decorator(self):
        """Test benchmark decorator functionality."""
        monitor = PerformanceMonitor()
        
        @monitor.benchmark_function("test_decorator")
        def test_function(duration_ms):
            time.sleep(duration_ms / 1000.0)  # Convert to seconds
            return "result"
        
        # Call the decorated function
        result = test_function(50)  # 50ms
        
        assert result == "result"
        assert len(monitor._measurements_by_benchmark["test_decorator"]) == 1
        
        measurement = monitor._measurements_by_benchmark["test_decorator"][0]
        assert measurement.benchmark_name == "test_decorator"
        assert 40 <= measurement.duration_ms <= 100  # Allow some variance
    
    def test_benchmark_decorator_with_error(self):
        """Test benchmark decorator with error handling."""
        monitor = PerformanceMonitor()
        
        @monitor.benchmark_function("test_error", {"component": "test"})
        def failing_function():
            raise ValueError("Test error")
        
        # Call the decorated function and expect error
        with pytest.raises(ValueError):
            failing_function()
        
        # Should have recorded error measurement
        assert len(monitor._measurements_by_benchmark["test_error_error"]) == 1
        
        measurement = monitor._measurements_by_benchmark["test_error_error"][0]
        assert measurement.benchmark_name == "test_error_error"
        assert measurement.metadata["component"] == "test"
        assert measurement.metadata["error"] == "Test error"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_measure_performance_function(self):
        """Test measure_performance convenience function."""
        measurement = measure_performance("test_convenience", 100.0, {"test": "data"})
        
        assert measurement.benchmark_name == "test_convenience"
        assert measurement.duration_ms == 100.0
        assert measurement.metadata["test"] == "data"
    
    def test_benchmark_decorator_function(self):
        """Test benchmark decorator convenience function."""
        @benchmark("test_decorator_convenience")
        def test_function():
            time.sleep(0.01)  # 10ms
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # Check that measurement was recorded
        monitor = get_performance_monitor()
        measurements = monitor._measurements_by_benchmark["test_decorator_convenience"]
        assert len(measurements) == 1
    
    def test_get_performance_summary_function(self):
        """Test get_performance_summary convenience function."""
        # Add a measurement
        measure_performance("test_summary", 200.0)
        
        summary = get_performance_summary()
        assert "health_status" in summary
        assert "total_measurements" in summary
        assert summary["total_measurements"] >= 1
    
    def test_set_performance_baseline_function(self):
        """Test set_performance_baseline convenience function."""
        # Add some measurements
        for duration in [90, 100, 110]:
            measure_performance("test_baseline", duration)
        
        # Set baseline from measurements
        set_performance_baseline("test_baseline")
        
        monitor = get_performance_monitor()
        assert "test_baseline" in monitor._baselines
        assert 95 <= monitor._baselines["test_baseline"] <= 105  # Should be around 100
        
        # Set explicit baseline
        set_performance_baseline("test_baseline", 150.0)
        assert monitor._baselines["test_baseline"] == 150.0


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_monitoring_workflow(self):
        """Test complete monitoring workflow."""
        monitor = PerformanceMonitor()
        
        # Register custom benchmark
        benchmark = PerformanceBenchmark(
            name="integration_test",
            type=BenchmarkType.PROCESSING,
            target_ms=100.0,
            warning_ms=200.0,
            critical_ms=400.0,
            description="Integration test benchmark"
        )
        monitor.register_benchmark(benchmark)
        
        # Set baseline
        monitor.set_baseline("integration_test", 100.0)
        
        # Add measurements over time
        measurements = [95, 105, 98, 102, 110, 115, 120, 125, 130, 140]
        for duration in measurements:
            monitor.measure("integration_test", duration)
        
        # Get statistics
        stats = monitor.get_stats("integration_test")
        assert stats is not None
        assert stats.count == len(measurements)
        assert stats.trend in ["stable", "degrading"]  # Should detect degrading trend
        
        # Check for alerts (140ms is 40% above baseline of 100ms)
        alerts = monitor.get_alerts()
        assert len(alerts) > 0
        
        # Get summary
        summary = monitor.get_performance_summary()
        assert summary["total_measurements"] >= len(measurements)
        assert "integration_test" in summary["benchmarks"]
    
    @patch('services.performance_monitor.record_render_time')
    def test_observability_integration(self, mock_record):
        """Test integration with observability system."""
        monitor = PerformanceMonitor()
        
        # Measure performance
        monitor.measure("test_observability", 150.0)
        
        # Should have called observability system
        mock_record.assert_called_once_with(150.0, "test_observability")


if __name__ == "__main__":
    pytest.main([__file__])
