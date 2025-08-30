"""
System Observability and Monitoring.

This module provides comprehensive monitoring for the UI refactor,
tracking performance metrics, error rates, and system health.
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
from datetime import datetime, timezone


class MetricType(Enum):
    """Types of metrics we collect."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class EventType(Enum):
    """Types of events we track."""
    RENDER = "render"
    CACHE = "cache"
    EXPORT = "export"
    ERROR = "error"
    USER_ACTION = "user_action"
    ADAPTER_USAGE = "adapter_usage"


@dataclass
class MetricEvent:
    """A single metric event."""
    timestamp: float
    event_type: EventType
    metric_name: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics summary."""
    render_times: List[float] = field(default_factory=list)
    cache_hit_rate: float = 0.0
    cache_miss_rate: float = 0.0
    error_rate: float = 0.0
    adapter_usage_rate: float = 0.0
    memory_usage_mb: float = 0.0
    total_events: int = 0


class ObservabilityCollector:
    """Centralized observability and metrics collection."""
    
    def __init__(self, max_events: int = 10000):
        self._events: deque = deque(maxlen=max_events)
        self._metrics: Dict[str, List[float]] = defaultdict(list)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._start_time = time.time()
        
        # Performance tracking
        self._render_times: deque = deque(maxlen=1000)
        self._cache_hits = 0
        self._cache_misses = 0
        self._error_count = 0
        self._adapter_calls = 0
        self._direct_calls = 0
        
    def record_event(self, event_type: EventType, metric_name: str, 
                    value: float = 1.0, tags: Optional[Dict[str, str]] = None,
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a metric event."""
        with self._lock:
            event = MetricEvent(
                timestamp=time.time(),
                event_type=event_type,
                metric_name=metric_name,
                value=value,
                tags=tags or {},
                metadata=metadata or {}
            )
            self._events.append(event)
            
            # Update specific counters
            if event_type == EventType.CACHE:
                if metric_name == "cache_hit":
                    self._cache_hits += 1
                elif metric_name == "cache_miss":
                    self._cache_misses += 1
            elif event_type == EventType.ERROR:
                self._error_count += 1
            elif event_type == EventType.ADAPTER_USAGE:
                if metric_name == "adapter_call":
                    self._adapter_calls += 1
                elif metric_name == "direct_call":
                    self._direct_calls += 1
            elif event_type == EventType.RENDER:
                if metric_name == "render_time":
                    self._render_times.append(value)
    
    def record_render_time(self, duration_ms: float, render_type: str = "unknown") -> None:
        """Record render timing."""
        self.record_event(
            EventType.RENDER, 
            "render_time", 
            duration_ms,
            tags={"type": render_type}
        )
    
    def record_cache_hit(self, cache_type: str = "unknown") -> None:
        """Record cache hit."""
        self.record_event(
            EventType.CACHE,
            "cache_hit",
            1.0,
            tags={"cache_type": cache_type}
        )
    
    def record_cache_miss(self, cache_type: str = "unknown") -> None:
        """Record cache miss."""
        self.record_event(
            EventType.CACHE,
            "cache_miss",
            1.0,
            tags={"cache_type": cache_type}
        )
    
    def record_error(self, error_type: str, error_message: str = "") -> None:
        """Record error occurrence."""
        self.record_event(
            EventType.ERROR,
            "error_occurred",
            1.0,
            tags={"error_type": error_type},
            metadata={"message": error_message}
        )
    
    def record_adapter_usage(self, adapter_type: str = "streamlit") -> None:
        """Record adapter usage."""
        self.record_event(
            EventType.ADAPTER_USAGE,
            "adapter_call",
            1.0,
            tags={"adapter": adapter_type}
        )
    
    def record_direct_call(self, call_type: str = "streamlit") -> None:
        """Record direct framework call (should be zero in refactored code)."""
        self.record_event(
            EventType.ADAPTER_USAGE,
            "direct_call",
            1.0,
            tags={"framework": call_type}
        )
    
    def get_performance_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics summary."""
        with self._lock:
            total_cache_ops = self._cache_hits + self._cache_misses
            cache_hit_rate = (self._cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0.0
            cache_miss_rate = (self._cache_misses / total_cache_ops * 100) if total_cache_ops > 0 else 0.0
            
            total_calls = self._adapter_calls + self._direct_calls
            adapter_usage_rate = (self._adapter_calls / total_calls * 100) if total_calls > 0 else 0.0
            
            total_events = len(self._events)
            uptime_hours = (time.time() - self._start_time) / 3600
            error_rate = (self._error_count / uptime_hours) if uptime_hours > 0 else 0.0
            
            return PerformanceMetrics(
                render_times=list(self._render_times),
                cache_hit_rate=cache_hit_rate,
                cache_miss_rate=cache_miss_rate,
                error_rate=error_rate,
                adapter_usage_rate=adapter_usage_rate,
                memory_usage_mb=self._estimate_memory_usage(),
                total_events=total_events
            )
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        metrics = self.get_performance_metrics()
        
        with self._lock:
            recent_events = [e for e in self._events if time.time() - e.timestamp < 300]  # Last 5 minutes
            
            summary = {
                "uptime_seconds": time.time() - self._start_time,
                "total_events": len(self._events),
                "recent_events": len(recent_events),
                "performance": {
                    "avg_render_time_ms": sum(metrics.render_times) / len(metrics.render_times) if metrics.render_times else 0,
                    "max_render_time_ms": max(metrics.render_times) if metrics.render_times else 0,
                    "min_render_time_ms": min(metrics.render_times) if metrics.render_times else 0,
                    "cache_hit_rate_percent": metrics.cache_hit_rate,
                    "cache_miss_rate_percent": metrics.cache_miss_rate,
                    "adapter_usage_rate_percent": metrics.adapter_usage_rate,
                    "error_rate_per_hour": metrics.error_rate,
                    "memory_usage_mb": metrics.memory_usage_mb
                },
                "counters": {
                    "cache_hits": self._cache_hits,
                    "cache_misses": self._cache_misses,
                    "errors": self._error_count,
                    "adapter_calls": self._adapter_calls,
                    "direct_calls": self._direct_calls
                },
                "health_status": self._get_health_status(metrics)
            }
            
            return summary
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # Fallback estimation
            return len(self._events) * 0.001  # Rough estimate
    
    def _get_health_status(self, metrics: PerformanceMetrics) -> str:
        """Determine overall health status."""
        issues = []
        
        # Check render performance
        if metrics.render_times:
            avg_render = sum(metrics.render_times) / len(metrics.render_times)
            if avg_render > 500:  # > 500ms
                issues.append("slow_render")
        
        # Check cache performance
        if metrics.cache_hit_rate < 80:
            issues.append("low_cache_hit_rate")
        
        # Check adapter usage
        if metrics.adapter_usage_rate < 95:  # Should be near 100% after refactor
            issues.append("direct_calls_detected")
        
        # Check error rate
        if metrics.error_rate > 1:  # > 1 error per hour
            issues.append("high_error_rate")
        
        # Check memory usage
        if metrics.memory_usage_mb > 100:  # > 100MB
            issues.append("high_memory_usage")
        
        if not issues:
            return "healthy"
        elif len(issues) <= 2:
            return "warning"
        else:
            return "critical"
    
    def export_metrics(self, format: str = "json") -> str:
        """Export metrics in specified format."""
        summary = self.get_metrics_summary()
        
        if format.lower() == "json":
            return json.dumps(summary, indent=2, default=str)
        else:
            # Simple text format
            lines = [
                f"System Health: {summary['health_status'].upper()}",
                f"Uptime: {summary['uptime_seconds']:.1f}s",
                f"Total Events: {summary['total_events']}",
                f"Avg Render Time: {summary['performance']['avg_render_time_ms']:.1f}ms",
                f"Cache Hit Rate: {summary['performance']['cache_hit_rate_percent']:.1f}%",
                f"Adapter Usage: {summary['performance']['adapter_usage_rate_percent']:.1f}%",
                f"Error Rate: {summary['performance']['error_rate_per_hour']:.2f}/hour",
                f"Memory Usage: {summary['performance']['memory_usage_mb']:.1f}MB"
            ]
            return "\n".join(lines)


# Global observability collector
_observability_collector: Optional[ObservabilityCollector] = None


def get_observability_collector() -> ObservabilityCollector:
    """Get the global observability collector."""
    global _observability_collector
    if _observability_collector is None:
        _observability_collector = ObservabilityCollector()
    return _observability_collector


# Convenience functions
def record_render_time(duration_ms: float, render_type: str = "unknown") -> None:
    """Record render timing."""
    get_observability_collector().record_render_time(duration_ms, render_type)


def record_cache_hit(cache_type: str = "unknown") -> None:
    """Record cache hit."""
    get_observability_collector().record_cache_hit(cache_type)


def record_cache_miss(cache_type: str = "unknown") -> None:
    """Record cache miss."""
    get_observability_collector().record_cache_miss(cache_type)


def record_error(error_type: str, error_message: str = "") -> None:
    """Record error occurrence."""
    get_observability_collector().record_error(error_type, error_message)


def record_adapter_usage(adapter_type: str = "streamlit") -> None:
    """Record adapter usage."""
    get_observability_collector().record_adapter_usage(adapter_type)


def record_direct_call(call_type: str = "streamlit") -> None:
    """Record direct framework call."""
    get_observability_collector().record_direct_call(call_type)


def get_metrics_summary() -> Dict[str, Any]:
    """Get comprehensive metrics summary."""
    return get_observability_collector().get_metrics_summary()


# Performance monitoring decorators
def monitor_render_performance(render_type: str = "unknown"):
    """Decorator to monitor render performance."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                record_render_time(duration_ms, render_type)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                record_render_time(duration_ms, f"{render_type}_error")
                record_error(f"render_{render_type}", str(e))
                raise
        return wrapper
    return decorator


def monitor_cache_operation(cache_type: str = "unknown"):
    """Decorator to monitor cache operations."""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                # Assume cache hit if no exception and result is not None
                if result is not None:
                    record_cache_hit(cache_type)
                else:
                    record_cache_miss(cache_type)
                return result
            except Exception as e:
                record_cache_miss(cache_type)
                record_error(f"cache_{cache_type}", str(e))
                raise
        return wrapper
    return decorator


# Export main classes and functions
__all__ = [
    'ObservabilityCollector', 'MetricEvent', 'PerformanceMetrics',
    'MetricType', 'EventType',
    'get_observability_collector', 'record_render_time', 'record_cache_hit',
    'record_cache_miss', 'record_error', 'record_adapter_usage', 'record_direct_call',
    'get_metrics_summary', 'monitor_render_performance', 'monitor_cache_operation'
]
