"""
Performance Metrics Collection System.
Implements Browser Performance API integration, custom timing markers, memory tracking, and cache analytics.
"""

import time
import threading
import psutil
import gc
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict, deque
import statistics

from core.feature_flags import get_feature_flag
from services.telemetry import record_performance_event, get_telemetry_collector


class MetricType(Enum):
    """Types of performance metrics."""
    TIMING = "timing"
    MEMORY = "memory"
    CACHE = "cache"
    RENDER = "render"
    NETWORK = "network"
    USER_INTERACTION = "user_interaction"


class TimingPhase(Enum):
    """Timing phases for performance measurement."""
    INITIALIZATION = "initialization"
    DATA_PROCESSING = "data_processing"
    LAYOUT_COMPUTATION = "layout_computation"
    RENDER_PREVIEW = "render_preview"
    CACHE_OPERATION = "cache_operation"
    EXPORT_GENERATION = "export_generation"
    USER_INTERACTION = "user_interaction"


@dataclass
class TimingMetric:
    """Timing performance metric."""
    name: str
    phase: TimingPhase
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def finish(self, success: bool = True, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Finish timing measurement."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success
        if metadata:
            self.metadata.update(metadata)
        return self.duration_ms
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class MemoryMetric:
    """Memory usage metric."""
    timestamp: float
    process_memory_mb: float
    system_memory_mb: float
    memory_percent: float
    gc_collections: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class CacheMetric:
    """Cache performance metric."""
    cache_type: str
    operation: str
    hit: bool
    key_size_bytes: Optional[int] = None
    value_size_bytes: Optional[int] = None
    access_time_ms: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RenderMetric:
    """Render performance metric."""
    render_type: str
    cards_count: int
    page_number: int
    duration_ms: float
    cache_hit: bool
    memory_used_mb: Optional[float] = None
    output_size_bytes: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class PerformanceTargets:
    """Performance targets and thresholds."""
    
    # Timing targets (milliseconds)
    FIRST_RENDER_MAX_MS = 500
    CACHED_RENDER_MAX_MS = 100
    LAYOUT_COMPUTATION_MAX_MS = 50
    CACHE_ACCESS_MAX_MS = 10
    
    # Memory targets
    MAX_MEMORY_MB = 50
    MEMORY_WARNING_THRESHOLD = 0.8  # 80% of max
    
    # Cache targets
    MIN_CACHE_HIT_RATE = 0.8  # 80%
    
    # Quality thresholds
    ERROR_RATE_THRESHOLD = 0.05  # 5%
    PERFORMANCE_DEGRADATION_THRESHOLD = 1.5  # 50% slower than target


class MetricsCollector:
    """Collects and analyzes performance metrics."""
    
    def __init__(self, max_metrics: int = 1000, analysis_window_minutes: int = 10):
        self._max_metrics = max_metrics
        self._analysis_window_minutes = analysis_window_minutes
        
        # Metric storage
        self._timing_metrics: deque = deque(maxlen=max_metrics)
        self._memory_metrics: deque = deque(maxlen=max_metrics)
        self._cache_metrics: deque = deque(maxlen=max_metrics)
        self._render_metrics: deque = deque(maxlen=max_metrics)
        
        # Active timings
        self._active_timings: Dict[str, TimingMetric] = {}
        
        # Statistics
        self._stats = {
            'metrics_collected': 0,
            'timing_measurements': 0,
            'memory_samples': 0,
            'cache_operations': 0,
            'render_operations': 0,
            'performance_violations': 0
        }
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Background monitoring
        self._monitor_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Configuration
        self._enabled = get_feature_flag('metrics_collection', True)
        self._memory_monitoring = get_feature_flag('memory_monitoring', True)
        self._detailed_timing = get_feature_flag('detailed_timing', True)
        
        if self._enabled:
            self._start_background_monitoring()
    
    def start_timing(self, name: str, phase: TimingPhase, 
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start timing measurement."""
        if not self._enabled:
            return ""
        
        timing_id = f"{name}_{int(time.time() * 1000)}"
        
        with self._lock:
            timing = TimingMetric(
                name=name,
                phase=phase,
                start_time=time.time(),
                metadata=metadata or {}
            )
            self._active_timings[timing_id] = timing
        
        return timing_id
    
    def finish_timing(self, timing_id: str, success: bool = True,
                     metadata: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Finish timing measurement."""
        if not self._enabled or not timing_id:
            return None
        
        with self._lock:
            if timing_id not in self._active_timings:
                return None
            
            timing = self._active_timings.pop(timing_id)
            duration_ms = timing.finish(success, metadata)
            
            # Store timing metric
            self._timing_metrics.append(timing)
            self._stats['timing_measurements'] += 1
            self._stats['metrics_collected'] += 1
            
            # Check performance targets
            self._check_timing_targets(timing)
            
            # Record to telemetry
            record_performance_event(
                operation=f"{timing.phase.value}_{timing.name}",
                duration_ms=duration_ms,
                success=success,
                metadata=timing.metadata
            )
            
            return duration_ms
    
    def record_memory_usage(self, metadata: Optional[Dict[str, Any]] = None) -> MemoryMetric:
        """Record current memory usage."""
        if not self._enabled or not self._memory_monitoring:
            return None
        
        try:
            # Get process memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            process_memory_mb = memory_info.rss / 1024 / 1024

            # Get system memory info
            system_memory = psutil.virtual_memory()
            system_memory_mb = system_memory.total / 1024 / 1024
            memory_percent = system_memory.percent

            # Get garbage collection stats
            gc_stats = {}
            for i in range(3):  # Python has 3 GC generations
                gc_stats[f"gen_{i}"] = gc.get_count()[i]

            metric = MemoryMetric(
                timestamp=time.time(),
                process_memory_mb=process_memory_mb,
                system_memory_mb=system_memory_mb,
                memory_percent=memory_percent,
                gc_collections=gc_stats,
                metadata=metadata or {}
            )
            
            with self._lock:
                self._memory_metrics.append(metric)
                self._stats['memory_samples'] += 1
                self._stats['metrics_collected'] += 1
                
                # Check memory targets
                self._check_memory_targets(metric)
            
            return metric
            
        except Exception as e:
            # Fallback for environments where psutil might not work
            return MemoryMetric(
                timestamp=time.time(),
                process_memory_mb=0.0,
                system_memory_mb=0.0,
                memory_percent=0.0,
                metadata={'error': str(e)}
            )
    
    def record_cache_operation(self, cache_type: str, operation: str, hit: bool,
                              key_size_bytes: Optional[int] = None,
                              value_size_bytes: Optional[int] = None,
                              access_time_ms: Optional[float] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record cache operation metric."""
        if not self._enabled:
            return
        
        metric = CacheMetric(
            cache_type=cache_type,
            operation=operation,
            hit=hit,
            key_size_bytes=key_size_bytes,
            value_size_bytes=value_size_bytes,
            access_time_ms=access_time_ms,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._cache_metrics.append(metric)
            self._stats['cache_operations'] += 1
            self._stats['metrics_collected'] += 1
    
    def record_render_operation(self, render_type: str, cards_count: int, page_number: int,
                               duration_ms: float, cache_hit: bool,
                               memory_used_mb: Optional[float] = None,
                               output_size_bytes: Optional[int] = None,
                               metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record render operation metric."""
        if not self._enabled:
            return
        
        metric = RenderMetric(
            render_type=render_type,
            cards_count=cards_count,
            page_number=page_number,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
            memory_used_mb=memory_used_mb,
            output_size_bytes=output_size_bytes,
            metadata=metadata or {}
        )
        
        with self._lock:
            self._render_metrics.append(metric)
            self._stats['render_operations'] += 1
            self._stats['metrics_collected'] += 1
            
            # Check render performance targets
            self._check_render_targets(metric)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and analytics."""
        with self._lock:
            current_time = time.time()
            window_start = current_time - (self._analysis_window_minutes * 60)
            
            # Filter metrics to analysis window
            recent_timings = [m for m in self._timing_metrics if m.end_time and m.end_time >= window_start]
            recent_memory = [m for m in self._memory_metrics if m.timestamp >= window_start]
            recent_cache = [m for m in self._cache_metrics if m.timestamp >= window_start]
            recent_renders = [m for m in self._render_metrics if m.timestamp >= window_start]
            
            summary = {
                'analysis_window_minutes': self._analysis_window_minutes,
                'timing_analysis': self._analyze_timing_metrics(recent_timings),
                'memory_analysis': self._analyze_memory_metrics(recent_memory),
                'cache_analysis': self._analyze_cache_metrics(recent_cache),
                'render_analysis': self._analyze_render_metrics(recent_renders),
                'performance_targets': self._check_all_targets(),
                'statistics': dict(self._stats)
            }
            
            return summary
    
    def get_metrics_data(self, metric_type: Optional[MetricType] = None,
                        limit: Optional[int] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Get raw metrics data."""
        with self._lock:
            data = {}
            
            if metric_type is None or metric_type == MetricType.TIMING:
                timings = list(self._timing_metrics)
                if limit:
                    timings = timings[-limit:]
                data['timing'] = [t.to_dict() for t in timings]
            
            if metric_type is None or metric_type == MetricType.MEMORY:
                memory = list(self._memory_metrics)
                if limit:
                    memory = memory[-limit:]
                data['memory'] = [m.to_dict() for m in memory]
            
            if metric_type is None or metric_type == MetricType.CACHE:
                cache = list(self._cache_metrics)
                if limit:
                    cache = cache[-limit:]
                data['cache'] = [c.to_dict() for c in cache]
            
            if metric_type is None or metric_type == MetricType.RENDER:
                render = list(self._render_metrics)
                if limit:
                    render = render[-limit:]
                data['render'] = [r.to_dict() for r in render]
            
            return data
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown metrics collector."""
        self._shutdown_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=timeout)
    
    def _start_background_monitoring(self) -> None:
        """Start background monitoring thread."""
        if self._memory_monitoring:
            self._monitor_thread = threading.Thread(
                target=self._background_monitor_loop,
                name="metrics_monitor",
                daemon=True
            )
            self._monitor_thread.start()
    
    def _background_monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Record memory usage periodically
                self.record_memory_usage({'source': 'background_monitor'})
                
                # Wait for next sample
                if self._shutdown_event.wait(30.0):  # Sample every 30 seconds
                    break
                    
            except Exception as e:
                # Continue monitoring even if individual samples fail
                time.sleep(5.0)
    
    def _check_timing_targets(self, timing: TimingMetric) -> None:
        """Check timing against performance targets."""
        if not timing.duration_ms or not timing.success:
            return
        
        violated = False
        
        # Check phase-specific targets
        if timing.phase == TimingPhase.RENDER_PREVIEW:
            if timing.metadata.get('cache_hit'):
                if timing.duration_ms > PerformanceTargets.CACHED_RENDER_MAX_MS:
                    violated = True
            else:
                if timing.duration_ms > PerformanceTargets.FIRST_RENDER_MAX_MS:
                    violated = True
        
        elif timing.phase == TimingPhase.LAYOUT_COMPUTATION:
            if timing.duration_ms > PerformanceTargets.LAYOUT_COMPUTATION_MAX_MS:
                violated = True
        
        elif timing.phase == TimingPhase.CACHE_OPERATION:
            if timing.duration_ms > PerformanceTargets.CACHE_ACCESS_MAX_MS:
                violated = True
        
        if violated:
            self._stats['performance_violations'] += 1
    
    def _check_memory_targets(self, metric: MemoryMetric) -> None:
        """Check memory usage against targets."""
        if metric.process_memory_mb > PerformanceTargets.MAX_MEMORY_MB:
            self._stats['performance_violations'] += 1
    
    def _check_render_targets(self, metric: RenderMetric) -> None:
        """Check render performance against targets."""
        target_ms = (PerformanceTargets.CACHED_RENDER_MAX_MS if metric.cache_hit 
                    else PerformanceTargets.FIRST_RENDER_MAX_MS)
        
        if metric.duration_ms > target_ms:
            self._stats['performance_violations'] += 1
    
    def _check_all_targets(self) -> Dict[str, Any]:
        """Check all performance targets."""
        with self._lock:
            # Calculate cache hit rate
            cache_hits = sum(1 for m in self._cache_metrics if m.hit)
            total_cache_ops = len(self._cache_metrics)
            cache_hit_rate = cache_hits / max(1, total_cache_ops)
            
            # Calculate average memory usage
            if self._memory_metrics:
                avg_memory = statistics.mean(m.process_memory_mb for m in self._memory_metrics)
            else:
                avg_memory = 0.0
            
            # Calculate render performance
            render_times = [m.duration_ms for m in self._render_metrics]
            avg_render_time = statistics.mean(render_times) if render_times else 0.0
            
            return {
                'cache_hit_rate': {
                    'current': cache_hit_rate,
                    'target': PerformanceTargets.MIN_CACHE_HIT_RATE,
                    'meets_target': cache_hit_rate >= PerformanceTargets.MIN_CACHE_HIT_RATE
                },
                'memory_usage': {
                    'current_mb': avg_memory,
                    'target_mb': PerformanceTargets.MAX_MEMORY_MB,
                    'meets_target': avg_memory <= PerformanceTargets.MAX_MEMORY_MB
                },
                'render_performance': {
                    'avg_duration_ms': avg_render_time,
                    'target_ms': PerformanceTargets.FIRST_RENDER_MAX_MS,
                    'meets_target': avg_render_time <= PerformanceTargets.FIRST_RENDER_MAX_MS
                },
                'total_violations': self._stats['performance_violations']
            }
    
    def _analyze_timing_metrics(self, timings: List[TimingMetric]) -> Dict[str, Any]:
        """Analyze timing metrics."""
        if not timings:
            return {'count': 0}
        
        durations = [t.duration_ms for t in timings if t.duration_ms]
        phases = defaultdict(list)
        
        for timing in timings:
            if timing.duration_ms:
                phases[timing.phase.value].append(timing.duration_ms)
        
        analysis = {
            'count': len(timings),
            'total_duration_ms': sum(durations),
            'avg_duration_ms': statistics.mean(durations) if durations else 0,
            'median_duration_ms': statistics.median(durations) if durations else 0,
            'max_duration_ms': max(durations) if durations else 0,
            'min_duration_ms': min(durations) if durations else 0,
            'phases': {}
        }
        
        for phase, phase_durations in phases.items():
            analysis['phases'][phase] = {
                'count': len(phase_durations),
                'avg_ms': statistics.mean(phase_durations),
                'max_ms': max(phase_durations),
                'min_ms': min(phase_durations)
            }
        
        return analysis
    
    def _analyze_memory_metrics(self, memory_metrics: List[MemoryMetric]) -> Dict[str, Any]:
        """Analyze memory metrics."""
        if not memory_metrics:
            return {'count': 0}
        
        process_memory = [m.process_memory_mb for m in memory_metrics]
        
        return {
            'count': len(memory_metrics),
            'avg_process_memory_mb': statistics.mean(process_memory),
            'max_process_memory_mb': max(process_memory),
            'min_process_memory_mb': min(process_memory),
            'current_memory_mb': process_memory[-1] if process_memory else 0
        }
    
    def _analyze_cache_metrics(self, cache_metrics: List[CacheMetric]) -> Dict[str, Any]:
        """Analyze cache metrics."""
        if not cache_metrics:
            return {'count': 0, 'hit_rate': 0.0}
        
        hits = sum(1 for m in cache_metrics if m.hit)
        hit_rate = hits / len(cache_metrics)
        
        cache_types = defaultdict(lambda: {'hits': 0, 'total': 0})
        for metric in cache_metrics:
            cache_types[metric.cache_type]['total'] += 1
            if metric.hit:
                cache_types[metric.cache_type]['hits'] += 1
        
        type_analysis = {}
        for cache_type, stats in cache_types.items():
            type_analysis[cache_type] = {
                'hit_rate': stats['hits'] / stats['total'],
                'total_operations': stats['total']
            }
        
        return {
            'count': len(cache_metrics),
            'overall_hit_rate': hit_rate,
            'cache_types': type_analysis
        }
    
    def _analyze_render_metrics(self, render_metrics: List[RenderMetric]) -> Dict[str, Any]:
        """Analyze render metrics."""
        if not render_metrics:
            return {'count': 0}
        
        durations = [m.duration_ms for m in render_metrics]
        cached_renders = [m for m in render_metrics if m.cache_hit]
        uncached_renders = [m for m in render_metrics if not m.cache_hit]
        
        analysis = {
            'count': len(render_metrics),
            'avg_duration_ms': statistics.mean(durations),
            'cache_hit_rate': len(cached_renders) / len(render_metrics),
            'cached_avg_ms': statistics.mean([m.duration_ms for m in cached_renders]) if cached_renders else 0,
            'uncached_avg_ms': statistics.mean([m.duration_ms for m in uncached_renders]) if uncached_renders else 0
        }
        
        return analysis


# Global metrics collector
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# Convenience functions and decorators
def start_timing(name: str, phase: TimingPhase, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Start timing measurement."""
    return get_metrics_collector().start_timing(name, phase, metadata)


def finish_timing(timing_id: str, success: bool = True, metadata: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Finish timing measurement."""
    return get_metrics_collector().finish_timing(timing_id, success, metadata)


def record_memory_usage(metadata: Optional[Dict[str, Any]] = None) -> Optional[MemoryMetric]:
    """Record current memory usage."""
    return get_metrics_collector().record_memory_usage(metadata)


def record_cache_operation(cache_type: str, operation: str, hit: bool, **kwargs) -> None:
    """Record cache operation."""
    get_metrics_collector().record_cache_operation(cache_type, operation, hit, **kwargs)


def record_render_operation(render_type: str, cards_count: int, page_number: int,
                           duration_ms: float, cache_hit: bool, **kwargs) -> None:
    """Record render operation."""
    get_metrics_collector().record_render_operation(
        render_type, cards_count, page_number, duration_ms, cache_hit, **kwargs
    )


def get_performance_summary() -> Dict[str, Any]:
    """Get performance summary."""
    return get_metrics_collector().get_performance_summary()


# Context manager for timing
class timing_context:
    """Context manager for timing operations."""
    
    def __init__(self, name: str, phase: TimingPhase, metadata: Optional[Dict[str, Any]] = None):
        self.name = name
        self.phase = phase
        self.metadata = metadata or {}
        self.timing_id = ""
        self.collector = get_metrics_collector()
    
    def __enter__(self):
        self.timing_id = self.collector.start_timing(self.name, self.phase, self.metadata)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        error_metadata = {}
        if exc_type:
            error_metadata['error_type'] = exc_type.__name__
            error_metadata['error_message'] = str(exc_val)
        
        self.collector.finish_timing(self.timing_id, success, error_metadata)


# Decorator for timing functions
def timed_operation(name: str, phase: TimingPhase):
    """Decorator for timing function execution."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with timing_context(name, phase, {'function': func.__name__}):
                return func(*args, **kwargs)
        return wrapper
    return decorator
