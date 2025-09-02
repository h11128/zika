"""
Performance optimization utilities for UI components.
"""

import time
import threading
from typing import Any, Callable, Dict, Optional
from functools import wraps
from collections import defaultdict
import logging

from core.feature_flags import get_feature_flag


class PerformanceOptimizer:
    """Utility class for performance optimizations."""

    def __init__(self):
        self._debounce_timers: Dict[str, threading.Timer] = {}
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger('ui.performance_utils')

    def debounce(self, key: str, delay_ms: int = 250):
        """Debounce decorator to prevent rapid successive calls."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self._lock:
                    # Cancel existing timer
                    if key in self._debounce_timers:
                        self._logger.debug(f"[debounce] Cancel existing timer for key={key}")
                        self._debounce_timers[key].cancel()

                    # Create new timer
                    self._logger.debug(f"[debounce] Schedule timer for key={key}, delay_ms={delay_ms}")
                    timer = threading.Timer(
                        delay_ms / 1000.0,
                        lambda: self._execute_debounced(func, key, args, kwargs)
                    )
                    timer.daemon = True
                    self._debounce_timers[key] = timer
                    timer.start()

            def _execute_debounced(self, func: Callable, key: str, args, kwargs):
                try:
                    self._logger.debug(f"[debounce] Executing debounced func for key={key}")
                    func(*args, **kwargs)
                finally:
                    # Clear timer reference after execution
                    with self._lock:
                        if key in self._debounce_timers:
                            self._logger.debug(f"[debounce] Clearing timer for key={key}")
                            self._debounce_timers.pop(key, None)


            return wrapper
        return decorator

    def memoize(self, key: str, ttl_seconds: int = 300):
        """Memoization decorator with TTL."""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                cache_key = f"{key}_{hash((args, tuple(sorted(kwargs.items()))))}"

                with self._lock:
                    # Check if cached and not expired
                    if (cache_key in self._cache and
                        cache_key in self._cache_timestamps and
                        time.time() - self._cache_timestamps[cache_key] < ttl_seconds):
                        return self._cache[cache_key]

                    # Compute and cache result
                    result = func(*args, **kwargs)
                    self._cache[cache_key] = result
                    self._cache_timestamps[cache_key] = time.time()

                    return result

            return wrapper
        return decorator

    def throttle(self, key: str, min_interval_ms: int = 100):
        """Throttle decorator to limit call frequency."""
        last_call_times = defaultdict(float)

        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                current_time = time.time()
                last_call = last_call_times[key]

                if current_time - last_call >= min_interval_ms / 1000.0:
                    last_call_times[key] = current_time
                    return func(*args, **kwargs)
                # Skip call if too frequent
                return None

            return wrapper
        return decorator

    def clear_cache(self, pattern: Optional[str] = None):
        """Clear cache entries, optionally matching a pattern."""
        with self._lock:
            if pattern is None:
                self._cache.clear()
                self._cache_timestamps.clear()
            else:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._cache_timestamps.pop(key, None)

    def cleanup(self):
        """Clean up resources."""
        with self._lock:
            # Cancel all timers
            for timer in self._debounce_timers.values():
                timer.cancel()
            self._debounce_timers.clear()

            # Clear caches
            self._cache.clear()
            self._cache_timestamps.clear()


# Global performance optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None


def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance."""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer


def debounce_ui_operation(key: str, delay_ms: int = 250):
    """Debounce UI operations to improve performance."""
    if get_feature_flag('performance_optimization', True):
        return get_performance_optimizer().debounce(key, delay_ms)
    else:
        # No-op decorator when optimization disabled
        def decorator(func):
            return func
        return decorator


def memoize_ui_computation(key: str, ttl_seconds: int = 300):
    """Memoize expensive UI computations."""
    if get_feature_flag('performance_optimization', True):
        return get_performance_optimizer().memoize(key, ttl_seconds)
    else:
        # No-op decorator when optimization disabled
        def decorator(func):
            return func
        return decorator


def throttle_ui_updates(key: str, min_interval_ms: int = 100):
    """Throttle UI updates to prevent excessive rendering."""
    if get_feature_flag('performance_optimization', True):
        return get_performance_optimizer().throttle(key, min_interval_ms)
    else:
        # No-op decorator when optimization disabled
        def decorator(func):
            return func
        return decorator


class LazyLoader:
    """Lazy loader for expensive resources."""

    def __init__(self, loader_func: Callable[[], Any]):
        self._loader_func = loader_func
        self._loaded = False
        self._value = None
        self._lock = threading.Lock()

    def get(self) -> Any:
        """Get the loaded value, loading if necessary."""
        if not self._loaded:
            with self._lock:
                if not self._loaded:  # Double-check locking
                    self._value = self._loader_func()
                    self._loaded = True
        return self._value

    def reset(self):
        """Reset the loader to force reload on next access."""
        with self._lock:
            self._loaded = False
            self._value = None


def create_lazy_loader(loader_func: Callable[[], Any]) -> LazyLoader:
    """Create a lazy loader for expensive resources."""
    return LazyLoader(loader_func)


class BatchProcessor:
    """Batch processor for UI operations."""

    def __init__(self, batch_size: int = 10, flush_interval_ms: int = 100):
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self._batch = []
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def add(self, operation: Callable[[], Any]):
        """Add an operation to the batch."""
        flush_now = False
        with self._lock:
            self._batch.append(operation)
            self._logger = logging.getLogger('ui.performance_utils')
            self._logger.debug(f"[batch] Added operation, size={len(self._batch)}")

            # Auto-flush if batch is full
            if len(self._batch) >= self.batch_size:
                # Defer actual flush until after releasing the lock to avoid deadlock
                self._logger.debug("[batch] Threshold reached, scheduling immediate flush")
                flush_now = True
            else:
                # Schedule flush if not already scheduled
                if self._timer is None:
                    self._logger.debug(f"[batch] Scheduling timer flush in {self.flush_interval_ms}ms")
                    self._timer = threading.Timer(
                        self.flush_interval_ms / 1000.0,
                        self._flush_batch
                    )
                    self._timer.daemon = True
                    self._timer.start()

        if flush_now:
            # Perform flush outside the lock to avoid re-entrant deadlocks
            self._flush_batch()

    def _flush_batch(self):
        """Flush the current batch."""
        # Copy and clear under lock, but execute operations outside lock
        with self._lock:
            if self._timer:
                self._logger.debug("[batch] Cancelling pending timer before flush")
                self._timer.cancel()
                self._timer = None

            if not self._batch:
                self._logger.debug("[batch] No operations to flush")
                return

            batch_to_process = self._batch.copy()
            self._batch.clear()
            self._logger.debug(f"[batch] Flushing {len(batch_to_process)} operations")

        # Process batch outside of lock
        for operation in batch_to_process:
            try:
                operation()
            except Exception as e:
                # Log error but continue processing
                if get_feature_flag('performance_monitoring', True):
                    try:
                        from services.performance_monitor import measure_performance
                        measure_performance("batch_operation_error", 0.0, {
                            'error': str(e)
                        })
                    except ImportError:
                        pass

    def flush(self):
        """Manually flush the batch."""
        self._flush_batch()

    def cleanup(self):
        """Clean up resources."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self._batch.clear()


def create_batch_processor(batch_size: int = 10, flush_interval_ms: int = 100) -> BatchProcessor:
    """Create a batch processor for UI operations."""
    return BatchProcessor(batch_size, flush_interval_ms)


# Cleanup function for performance utilities
def cleanup_performance_utils():
    """Clean up all performance optimization resources."""
    global _performance_optimizer
    if _performance_optimizer:
        _performance_optimizer.cleanup()
        _performance_optimizer = None


# Export main utilities
__all__ = [
    'PerformanceOptimizer',
    'get_performance_optimizer',
    'debounce_ui_operation',
    'memoize_ui_computation',
    'throttle_ui_updates',
    'LazyLoader',
    'create_lazy_loader',
    'BatchProcessor',
    'create_batch_processor',
    'cleanup_performance_utils'
]
