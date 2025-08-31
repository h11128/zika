"""
Comprehensive Performance Monitoring System.
Provides benchmarking, regression detection, and performance analytics.
"""

import time
import threading
import statistics
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, deque
import json
import logging

from core.feature_flags import get_feature_flag
from services.observability import record_render_time, record_error


class PerformanceLevel(Enum):
    """Performance level classifications."""
    EXCELLENT = "excellent"    # < 100ms
    GOOD = "good"             # 100-300ms
    ACCEPTABLE = "acceptable"  # 300-500ms
    SLOW = "slow"             # 500-1000ms
    CRITICAL = "critical"     # > 1000ms


class BenchmarkType(Enum):
    """Types of benchmarks."""
    RENDER = "render"
    CACHE = "cache"
    EXPORT = "export"
    LAYOUT = "layout"
    PROCESSING = "processing"


@dataclass
class PerformanceBenchmark:
    """Performance benchmark definition."""
    name: str
    type: BenchmarkType
    target_ms: float
    warning_ms: float
    critical_ms: float
    description: str = ""
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMeasurement:
    """Single performance measurement."""
    benchmark_name: str
    duration_ms: float
    timestamp: float
    level: PerformanceLevel
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'benchmark_name': self.benchmark_name,
            'duration_ms': self.duration_ms,
            'timestamp': self.timestamp,
            'level': self.level.value,
            'metadata': self.metadata
        }


@dataclass
class PerformanceStats:
    """Performance statistics for a benchmark."""
    benchmark_name: str
    count: int
    avg_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    current_level: PerformanceLevel
    trend: str  # "improving", "stable", "degrading"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'benchmark_name': self.benchmark_name,
            'count': self.count,
            'avg_ms': self.avg_ms,
            'min_ms': self.min_ms,
            'max_ms': self.max_ms,
            'p50_ms': self.p50_ms,
            'p95_ms': self.p95_ms,
            'p99_ms': self.p99_ms,
            'current_level': self.current_level.value,
            'trend': self.trend
        }


@dataclass
class RegressionAlert:
    """Performance regression alert."""
    benchmark_name: str
    current_avg_ms: float
    baseline_avg_ms: float
    regression_percent: float
    severity: str  # "warning", "critical"
    timestamp: float
    details: str = ""


class PerformanceMonitor:
    """Comprehensive performance monitoring system."""
    
    def __init__(self, max_measurements: int = 10000):
        self._benchmarks: Dict[str, PerformanceBenchmark] = {}
        self._measurements: deque = deque(maxlen=max_measurements)
        self._measurements_by_benchmark: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._baselines: Dict[str, float] = {}
        self._alerts: List[RegressionAlert] = []
        self._lock = threading.RLock()
        
        # Configuration
        self._regression_threshold = 20.0  # 20% regression threshold
        self._min_measurements_for_baseline = 10
        self._baseline_window_hours = 24
        
        # Setup default benchmarks
        self._setup_default_benchmarks()
    
    def register_benchmark(self, benchmark: PerformanceBenchmark) -> None:
        """Register a performance benchmark."""
        with self._lock:
            self._benchmarks[benchmark.name] = benchmark
    
    def measure(self, benchmark_name: str, duration_ms: float, 
               metadata: Optional[Dict[str, Any]] = None) -> PerformanceMeasurement:
        """Record a performance measurement."""
        with self._lock:
            if benchmark_name not in self._benchmarks:
                # Auto-register basic benchmark
                self._auto_register_benchmark(benchmark_name, duration_ms)
            
            benchmark = self._benchmarks[benchmark_name]
            level = self._classify_performance(duration_ms, benchmark)
            
            measurement = PerformanceMeasurement(
                benchmark_name=benchmark_name,
                duration_ms=duration_ms,
                timestamp=time.time(),
                level=level,
                metadata=metadata or {}
            )
            
            # Store measurement
            self._measurements.append(measurement)
            self._measurements_by_benchmark[benchmark_name].append(measurement)
            
            # Check for regressions
            self._check_regression(benchmark_name, duration_ms)
            
            # Record to observability system
            if get_feature_flag('performance_monitoring', True):
                record_render_time(duration_ms, benchmark_name)
            
            return measurement
    
    def get_stats(self, benchmark_name: str, hours: int = 24) -> Optional[PerformanceStats]:
        """Get performance statistics for a benchmark."""
        with self._lock:
            measurements = self._get_recent_measurements(benchmark_name, hours)
            if not measurements:
                return None
            
            durations = [m.duration_ms for m in measurements]
            
            # Calculate statistics
            avg_ms = statistics.mean(durations)
            min_ms = min(durations)
            max_ms = max(durations)
            
            # Percentiles
            sorted_durations = sorted(durations)
            p50_ms = statistics.median(sorted_durations)
            p95_ms = self._percentile(sorted_durations, 95)
            p99_ms = self._percentile(sorted_durations, 99)
            
            # Current level
            benchmark = self._benchmarks.get(benchmark_name)
            current_level = self._classify_performance(avg_ms, benchmark) if benchmark else PerformanceLevel.ACCEPTABLE
            
            # Trend analysis
            trend = self._analyze_trend(benchmark_name, hours)
            
            return PerformanceStats(
                benchmark_name=benchmark_name,
                count=len(measurements),
                avg_ms=avg_ms,
                min_ms=min_ms,
                max_ms=max_ms,
                p50_ms=p50_ms,
                p95_ms=p95_ms,
                p99_ms=p99_ms,
                current_level=current_level,
                trend=trend
            )
    
    def get_all_stats(self, hours: int = 24) -> Dict[str, PerformanceStats]:
        """Get statistics for all benchmarks."""
        with self._lock:
            stats = {}
            for benchmark_name in self._benchmarks.keys():
                stat = self.get_stats(benchmark_name, hours)
                if stat:
                    stats[benchmark_name] = stat
            return stats
    
    def get_alerts(self, hours: int = 24) -> List[RegressionAlert]:
        """Get recent regression alerts."""
        with self._lock:
            cutoff_time = time.time() - (hours * 3600)
            return [alert for alert in self._alerts if alert.timestamp >= cutoff_time]
    
    def set_baseline(self, benchmark_name: str, baseline_ms: Optional[float] = None) -> None:
        """Set performance baseline for a benchmark."""
        with self._lock:
            if baseline_ms is None:
                # Calculate baseline from recent measurements
                measurements = self._get_recent_measurements(benchmark_name, self._baseline_window_hours)
                if len(measurements) >= self._min_measurements_for_baseline:
                    durations = [m.duration_ms for m in measurements]
                    baseline_ms = statistics.mean(durations)
                else:
                    # If not enough recent measurements, use all available measurements
                    all_measurements = self._measurements_by_benchmark.get(benchmark_name, [])
                    if len(all_measurements) >= 3:  # Minimum 3 measurements
                        durations = [m.duration_ms for m in all_measurements]
                        baseline_ms = statistics.mean(durations)
                    else:
                        return  # Not enough data

            self._baselines[benchmark_name] = baseline_ms
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        with self._lock:
            all_stats = self.get_all_stats()
            alerts = self.get_alerts()
            
            # Overall health
            total_measurements = len(self._measurements)
            critical_count = sum(1 for s in all_stats.values() if s.current_level == PerformanceLevel.CRITICAL)
            slow_count = sum(1 for s in all_stats.values() if s.current_level in [PerformanceLevel.SLOW, PerformanceLevel.CRITICAL])
            
            health_status = "healthy"
            if critical_count > 0:
                health_status = "critical"
            elif slow_count > len(all_stats) * 0.3:  # More than 30% slow
                health_status = "warning"
            
            return {
                'health_status': health_status,
                'total_benchmarks': len(self._benchmarks),
                'total_measurements': total_measurements,
                'critical_benchmarks': critical_count,
                'slow_benchmarks': slow_count,
                'active_alerts': len(alerts),
                'benchmarks': {name: stats.to_dict() for name, stats in all_stats.items()},
                'alerts': [alert.__dict__ for alert in alerts],
                'baselines': dict(self._baselines)
            }
    
    def benchmark_function(self, benchmark_name: str, metadata: Optional[Dict[str, Any]] = None):
        """Decorator to benchmark function execution."""
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    self.measure(benchmark_name, duration_ms, metadata)
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    error_metadata = dict(metadata or {})
                    error_metadata['error'] = str(e)
                    self.measure(f"{benchmark_name}_error", duration_ms, error_metadata)
                    raise
            return wrapper
        return decorator
    
    def _setup_default_benchmarks(self) -> None:
        """Setup default performance benchmarks."""
        default_benchmarks = [
            PerformanceBenchmark(
                name="preview_render",
                type=BenchmarkType.RENDER,
                target_ms=200.0,
                warning_ms=500.0,
                critical_ms=1000.0,
                description="Preview rendering performance"
            ),
            PerformanceBenchmark(
                name="export_pdf",
                type=BenchmarkType.EXPORT,
                target_ms=1000.0,
                warning_ms=3000.0,
                critical_ms=5000.0,
                description="PDF export performance"
            ),
            PerformanceBenchmark(
                name="export_pptx",
                type=BenchmarkType.EXPORT,
                target_ms=1500.0,
                warning_ms=4000.0,
                critical_ms=6000.0,
                description="PPTX export performance"
            ),
            PerformanceBenchmark(
                name="layout_computation",
                type=BenchmarkType.LAYOUT,
                target_ms=50.0,
                warning_ms=200.0,
                critical_ms=500.0,
                description="Layout computation performance"
            ),
            PerformanceBenchmark(
                name="cache_operation",
                type=BenchmarkType.CACHE,
                target_ms=10.0,
                warning_ms=50.0,
                critical_ms=100.0,
                description="Cache operation performance"
            )
        ]
        
        for benchmark in default_benchmarks:
            self._benchmarks[benchmark.name] = benchmark
    
    def _auto_register_benchmark(self, name: str, duration_ms: float) -> None:
        """Auto-register a benchmark based on first measurement."""
        # Estimate thresholds based on duration
        target_ms = max(duration_ms * 0.8, 10.0)
        warning_ms = duration_ms * 2.0
        critical_ms = duration_ms * 5.0
        
        benchmark = PerformanceBenchmark(
            name=name,
            type=BenchmarkType.PROCESSING,
            target_ms=target_ms,
            warning_ms=warning_ms,
            critical_ms=critical_ms,
            description=f"Auto-registered benchmark for {name}"
        )
        
        self._benchmarks[name] = benchmark
    
    def _classify_performance(self, duration_ms: float, benchmark: Optional[PerformanceBenchmark]) -> PerformanceLevel:
        """Classify performance level based on duration and benchmark."""
        if not benchmark:
            # Default classification
            if duration_ms < 100:
                return PerformanceLevel.EXCELLENT
            elif duration_ms < 300:
                return PerformanceLevel.GOOD
            elif duration_ms < 500:
                return PerformanceLevel.ACCEPTABLE
            elif duration_ms < 1000:
                return PerformanceLevel.SLOW
            else:
                return PerformanceLevel.CRITICAL
        
        # Benchmark-based classification
        if duration_ms <= benchmark.target_ms:
            return PerformanceLevel.EXCELLENT
        elif duration_ms <= benchmark.warning_ms:
            return PerformanceLevel.GOOD if duration_ms <= benchmark.target_ms * 1.5 else PerformanceLevel.ACCEPTABLE
        elif duration_ms <= benchmark.critical_ms:
            return PerformanceLevel.SLOW
        else:
            return PerformanceLevel.CRITICAL
    
    def _get_recent_measurements(self, benchmark_name: str, hours: int) -> List[PerformanceMeasurement]:
        """Get recent measurements for a benchmark."""
        cutoff_time = time.time() - (hours * 3600)
        measurements = self._measurements_by_benchmark.get(benchmark_name, [])
        return [m for m in measurements if m.timestamp >= cutoff_time]
    
    def _check_regression(self, benchmark_name: str, current_duration_ms: float) -> None:
        """Check for performance regression."""
        if benchmark_name not in self._baselines:
            return
        
        baseline_ms = self._baselines[benchmark_name]
        if baseline_ms <= 0:
            return
        
        regression_percent = ((current_duration_ms - baseline_ms) / baseline_ms) * 100
        
        if regression_percent >= self._regression_threshold:
            severity = "critical" if regression_percent >= self._regression_threshold * 2 else "warning"
            
            alert = RegressionAlert(
                benchmark_name=benchmark_name,
                current_avg_ms=current_duration_ms,
                baseline_avg_ms=baseline_ms,
                regression_percent=regression_percent,
                severity=severity,
                timestamp=time.time(),
                details=f"Performance regression detected: {regression_percent:.1f}% slower than baseline"
            )
            
            self._alerts.append(alert)
            
            # Keep only recent alerts
            cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days
            self._alerts = [a for a in self._alerts if a.timestamp >= cutoff_time]
            
            # Log the regression
            if get_feature_flag('performance_monitoring', True):
                record_error("performance_regression", f"{benchmark_name}: {regression_percent:.1f}% regression")
    
    def _analyze_trend(self, benchmark_name: str, hours: int) -> str:
        """Analyze performance trend."""
        measurements = self._get_recent_measurements(benchmark_name, hours)
        if len(measurements) < 5:
            return "stable"
        
        # Split into two halves and compare
        mid_point = len(measurements) // 2
        first_half = [m.duration_ms for m in measurements[:mid_point]]
        second_half = [m.duration_ms for m in measurements[mid_point:]]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        change_percent = ((second_avg - first_avg) / first_avg) * 100
        
        if change_percent < -5:  # 5% improvement
            return "improving"
        elif change_percent > 5:  # 5% degradation
            return "degrading"
        else:
            return "stable"
    
    def _percentile(self, sorted_data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not sorted_data:
            return 0.0
        
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_data) - 1)
        
        if lower_index == upper_index:
            return sorted_data[lower_index]
        
        # Linear interpolation
        weight = index - lower_index
        return sorted_data[lower_index] * (1 - weight) + sorted_data[upper_index] * weight


# Global performance monitor
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


# Convenience functions
def measure_performance(benchmark_name: str, duration_ms: float, 
                       metadata: Optional[Dict[str, Any]] = None) -> PerformanceMeasurement:
    """Record a performance measurement."""
    return get_performance_monitor().measure(benchmark_name, duration_ms, metadata)


def benchmark(name: str, metadata: Optional[Dict[str, Any]] = None):
    """Decorator to benchmark function performance."""
    return get_performance_monitor().benchmark_function(name, metadata)


def get_performance_summary() -> Dict[str, Any]:
    """Get comprehensive performance summary."""
    return get_performance_monitor().get_performance_summary()


def set_performance_baseline(benchmark_name: str, baseline_ms: Optional[float] = None) -> None:
    """Set performance baseline."""
    get_performance_monitor().set_baseline(benchmark_name, baseline_ms)
