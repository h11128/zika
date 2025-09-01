"""
Prefetch Mechanisms for Predictive Caching and Background Processing.
Implements intelligent prefetching for preview pages, export formats, and layout computations.
"""

import threading
import time
import queue
from typing import Dict, List, Optional, Any, Callable, Set, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
import logging
import weakref

from core.feature_flags import get_feature_flag
from services.cache_strategy import get_preview_cache, get_export_cache, CacheLevel
from services.performance_monitor import measure_performance, benchmark
from services.observability import record_error, record_cache_hit


class PrefetchPriority(Enum):
    """Prefetch priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class PrefetchType(Enum):
    """Types of prefetch operations."""
    PREVIEW_PAGE = "preview_page"
    EXPORT_FORMAT = "export_format"
    LAYOUT_COMPUTATION = "layout_computation"
    CACHE_WARMUP = "cache_warmup"


@dataclass
class PrefetchTask:
    """Prefetch task definition."""
    task_id: str
    task_type: PrefetchType
    priority: PrefetchPriority
    target_function: Callable
    args: tuple
    kwargs: dict
    cache_key: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    timeout_seconds: float = 30.0
    
    def __post_init__(self):
        if not self.task_id:
            import uuid
            self.task_id = str(uuid.uuid4())[:8]


@dataclass
class PrefetchResult:
    """Result of a prefetch operation."""
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    cache_hit: bool = False
    cached: bool = False


class PrefetchStrategy:
    """Strategy for determining what to prefetch."""
    
    def __init__(self):
        self._access_patterns: Dict[str, List[float]] = {}
        self._prediction_window = 300.0  # 5 minutes
        self._min_confidence = 0.6
    
    def record_access(self, resource_key: str) -> None:
        """Record access to a resource for pattern learning."""
        current_time = time.time()
        if resource_key not in self._access_patterns:
            self._access_patterns[resource_key] = []
        
        self._access_patterns[resource_key].append(current_time)
        
        # Keep only recent accesses
        cutoff_time = current_time - self._prediction_window
        self._access_patterns[resource_key] = [
            t for t in self._access_patterns[resource_key] if t >= cutoff_time
        ]
    
    def predict_next_accesses(self, current_context: Dict[str, Any]) -> List[str]:
        """Predict likely next resource accesses."""
        predictions = []
        current_time = time.time()
        
        # Simple prediction based on recent access frequency
        for resource_key, access_times in self._access_patterns.items():
            if len(access_times) < 2:
                continue
            
            # Calculate access frequency
            recent_accesses = [t for t in access_times if current_time - t < 60.0]  # Last minute
            if len(recent_accesses) >= 2:
                frequency = len(recent_accesses) / 60.0  # accesses per second
                confidence = min(frequency * 10, 1.0)  # Scale to 0-1
                
                if confidence >= self._min_confidence:
                    predictions.append(resource_key)
        
        return predictions
    
    def get_adjacent_pages(self, current_page: int, total_pages: int, 
                          lookahead: int = 2) -> List[int]:
        """Get adjacent pages for prefetching."""
        pages = []
        
        # Previous pages
        for i in range(max(0, current_page - lookahead), current_page):
            pages.append(i)
        
        # Next pages
        for i in range(current_page + 1, min(total_pages, current_page + lookahead + 1)):
            pages.append(i)
        
        return pages


class PrefetchManager:
    """Manages prefetch operations and background processing."""
    
    def __init__(self, max_workers: int = 3, max_queue_size: int = 100):
        self._max_workers = max_workers
        self._max_queue_size = max_queue_size
        
        # Task management
        self._task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)
        self._active_tasks: Dict[str, Future] = {}
        self._completed_tasks: Dict[str, PrefetchResult] = {}
        self._cancelled_tasks: Set[str] = set()
        
        # Thread pool
        self._executor: Optional[ThreadPoolExecutor] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        
        # Strategy and monitoring
        self._strategy = PrefetchStrategy()
        self._stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'cache_hits': 0,
            'total_duration_ms': 0.0
        }
        
        # Configuration
        self._enabled = get_feature_flag('prefetch_enabled', True)
        self._max_concurrent_tasks = 2
        self._task_counter = 0  # For priority queue ordering

        if self._enabled:
            self._start()
    
    def _start(self) -> None:
        """Start the prefetch manager."""
        with self._lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self._max_workers,
                    thread_name_prefix="prefetch"
                )
                self._worker_thread = threading.Thread(
                    target=self._worker_loop,
                    name="prefetch_manager",
                    daemon=True
                )
                self._worker_thread.start()
    
    def submit_task(self, task: PrefetchTask) -> bool:
        """Submit a prefetch task."""
        if not self._enabled:
            return False
        
        with self._lock:
            # Check if task already exists or is cancelled
            if task.task_id in self._active_tasks or task.task_id in self._cancelled_tasks:
                return False
            
            # Check queue capacity
            if self._task_queue.qsize() >= self._max_queue_size:
                # Remove lowest priority task
                self._evict_low_priority_task()
            
            try:
                # Priority queue uses tuple (priority, counter, task)
                # Counter ensures stable ordering when priorities are equal
                priority_value = -task.priority.value  # Negative for max-heap behavior
                self._task_counter += 1
                self._task_queue.put_nowait((priority_value, self._task_counter, task))
                self._stats['tasks_submitted'] += 1
                return True
            except queue.Full:
                return False
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a prefetch task."""
        with self._lock:
            # Mark as cancelled
            self._cancelled_tasks.add(task_id)
            
            # Cancel active future if exists
            if task_id in self._active_tasks:
                future = self._active_tasks[task_id]
                cancelled = future.cancel()
                if cancelled:
                    del self._active_tasks[task_id]
                    self._stats['tasks_cancelled'] += 1
                return cancelled
            
            return True
    
    def cancel_tasks_by_type(self, task_type: PrefetchType) -> int:
        """Cancel all tasks of a specific type."""
        cancelled_count = 0
        
        with self._lock:
            # Cancel active tasks
            to_cancel = []
            for task_id, future in self._active_tasks.items():
                # We need to check task type, but it's not stored in the future
                # For now, we'll cancel all active tasks when type-specific cancellation is needed
                to_cancel.append(task_id)
            
            for task_id in to_cancel:
                if self.cancel_task(task_id):
                    cancelled_count += 1
        
        return cancelled_count
    
    def get_task_result(self, task_id: str) -> Optional[PrefetchResult]:
        """Get result of a completed task."""
        with self._lock:
            return self._completed_tasks.get(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get prefetch statistics."""
        with self._lock:
            active_count = len(self._active_tasks)
            queue_size = self._task_queue.qsize()
            
            stats = dict(self._stats)
            stats.update({
                'active_tasks': active_count,
                'queued_tasks': queue_size,
                'completed_tasks': len(self._completed_tasks),
                'cancelled_tasks': len(self._cancelled_tasks),
                'avg_duration_ms': (
                    stats['total_duration_ms'] / max(1, stats['tasks_completed'])
                ),
                'success_rate': (
                    stats['tasks_completed'] / max(1, stats['tasks_submitted']) * 100
                ),
                'cache_hit_rate': (
                    stats['cache_hits'] / max(1, stats['tasks_completed']) * 100
                )
            })
            
            return stats
    
    def prefetch_preview_pages(self, cards: List[Dict[str, str]], 
                              current_page: int, total_pages: int,
                              render_params: Dict[str, Any]) -> List[str]:
        """Prefetch adjacent preview pages."""
        if not self._enabled:
            return []
        
        adjacent_pages = self._strategy.get_adjacent_pages(current_page, total_pages)
        task_ids = []
        
        for page_num in adjacent_pages:
            task_id = f"preview_page_{page_num}_{hash(str(render_params))}"
            
            task = PrefetchTask(
                task_id=task_id,
                task_type=PrefetchType.PREVIEW_PAGE,
                priority=PrefetchPriority.NORMAL,
                target_function=self._render_preview_page,
                args=(cards, page_num),
                kwargs=render_params,
                tags={'page': str(page_num), 'type': 'preview'}
            )
            
            if self.submit_task(task):
                task_ids.append(task_id)
        
        return task_ids
    
    def prefetch_export_formats(self, cards: List[Dict[str, str]], 
                               export_params: Dict[str, Any],
                               formats: List[str] = None) -> List[str]:
        """Prefetch export formats in background."""
        if not self._enabled:
            return []
        
        formats = formats or ['pdf', 'pptx']
        task_ids = []
        
        for format_type in formats:
            task_id = f"export_{format_type}_{hash(str(export_params))}"
            
            task = PrefetchTask(
                task_id=task_id,
                task_type=PrefetchType.EXPORT_FORMAT,
                priority=PrefetchPriority.LOW,
                target_function=self._prepare_export,
                args=(cards, format_type),
                kwargs=export_params,
                tags={'format': format_type, 'type': 'export'},
                timeout_seconds=60.0  # Longer timeout for exports
            )
            
            if self.submit_task(task):
                task_ids.append(task_id)
        
        return task_ids
    
    def warm_cache(self, cache_keys: List[str], 
                   warm_function: Callable) -> List[str]:
        """Warm cache with specific keys."""
        if not self._enabled:
            return []
        
        task_ids = []
        
        for cache_key in cache_keys:
            task_id = f"cache_warm_{cache_key}"
            
            task = PrefetchTask(
                task_id=task_id,
                task_type=PrefetchType.CACHE_WARMUP,
                priority=PrefetchPriority.HIGH,
                target_function=warm_function,
                args=(cache_key,),
                kwargs={},
                cache_key=cache_key,
                tags={'type': 'cache_warmup'}
            )
            
            if self.submit_task(task):
                task_ids.append(task_id)
        
        return task_ids
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown the prefetch manager."""
        with self._lock:
            self._shutdown_event.set()
            
            # Cancel all active tasks
            for task_id in list(self._active_tasks.keys()):
                self.cancel_task(task_id)
            
            # Shutdown executor
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
            
            # Wait for worker thread
            if self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=timeout)
                self._worker_thread = None
    
    def _worker_loop(self) -> None:
        """Main worker loop for processing prefetch tasks."""
        while not self._shutdown_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    priority, counter, task = self._task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Check if task was cancelled
                if task.task_id in self._cancelled_tasks:
                    self._cancelled_tasks.discard(task.task_id)
                    continue
                
                # Check concurrent task limit
                if len(self._active_tasks) >= self._max_concurrent_tasks:
                    # Put task back and wait
                    self._task_queue.put((priority, counter, task))
                    time.sleep(0.1)
                    continue
                
                # Submit task to executor
                future = self._executor.submit(self._execute_task, task)
                
                with self._lock:
                    self._active_tasks[task.task_id] = future
                
                # Monitor completion in background
                threading.Thread(
                    target=self._monitor_task_completion,
                    args=(task.task_id, future),
                    daemon=True
                ).start()
                
            except Exception as e:
                logging.error(f"Error in prefetch worker loop: {e}")
                time.sleep(1.0)
    
    def _execute_task(self, task: PrefetchTask) -> PrefetchResult:
        """Execute a prefetch task."""
        start_time = time.time()
        
        try:
            # Check cache first if cache_key is provided
            cache_hit = False
            if task.cache_key:
                cache = self._get_cache_for_task(task)
                cached_result = cache.get(task.cache_key) if cache else None
                if cached_result is not None:
                    cache_hit = True
                    result = cached_result
                else:
                    result = task.target_function(*task.args, **task.kwargs)
                    if cache:
                        cache.set(task.cache_key, result, task.tags)
            else:
                result = task.target_function(*task.args, **task.kwargs)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Record performance
            measure_performance(f"prefetch_{task.task_type.value}", duration_ms, {
                'task_id': task.task_id,
                'cache_hit': cache_hit
            })
            
            return PrefetchResult(
                task_id=task.task_id,
                success=True,
                result=result,
                duration_ms=duration_ms,
                cache_hit=cache_hit,
                cached=task.cache_key is not None
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            # Record error
            record_error(f"prefetch_{task.task_type.value}", error_msg)
            
            return PrefetchResult(
                task_id=task.task_id,
                success=False,
                error=error_msg,
                duration_ms=duration_ms
            )
    
    def _monitor_task_completion(self, task_id: str, future: Future) -> None:
        """Monitor task completion and update statistics."""
        try:
            result = future.result()
            
            with self._lock:
                # Remove from active tasks
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
                
                # Store result
                self._completed_tasks[task_id] = result
                
                # Update statistics
                if result.success:
                    self._stats['tasks_completed'] += 1
                    if result.cache_hit:
                        self._stats['cache_hits'] += 1
                else:
                    self._stats['tasks_failed'] += 1
                
                self._stats['total_duration_ms'] += result.duration_ms
                
                # Cleanup old completed tasks
                self._cleanup_completed_tasks()
                
        except Exception as e:
            logging.error(f"Error monitoring task completion: {e}")
    
    def _get_cache_for_task(self, task: PrefetchTask):
        """Get appropriate cache for task type."""
        if task.task_type == PrefetchType.PREVIEW_PAGE:
            return get_preview_cache()
        elif task.task_type == PrefetchType.EXPORT_FORMAT:
            return get_export_cache()
        else:
            return get_preview_cache()  # Default
    
    def _render_preview_page(self, cards: List[Dict[str, str]], 
                           page_num: int, **kwargs) -> str:
        """Render a preview page (placeholder implementation)."""
        # This would call the actual preview rendering function
        # For now, return a placeholder
        return f"<html>Preview page {page_num} with {len(cards)} cards</html>"
    
    def _prepare_export(self, cards: List[Dict[str, str]], 
                       format_type: str, **kwargs) -> bytes:
        """Prepare export data (placeholder implementation)."""
        # This would call the actual export functions
        # For now, return placeholder data
        return f"Export data for {format_type} with {len(cards)} cards".encode()
    
    def _evict_low_priority_task(self) -> None:
        """Evict lowest priority task from queue."""
        # This is complex with PriorityQueue, so we'll skip for now
        # In a real implementation, we might use a different data structure
        pass
    
    def _cleanup_completed_tasks(self) -> None:
        """Cleanup old completed tasks."""
        max_completed = 100
        if len(self._completed_tasks) > max_completed:
            # Remove oldest tasks
            sorted_tasks = sorted(
                self._completed_tasks.items(),
                key=lambda x: x[1].task_id  # Simple cleanup by task_id
            )
            
            to_remove = len(sorted_tasks) - max_completed
            for i in range(to_remove):
                task_id = sorted_tasks[i][0]
                del self._completed_tasks[task_id]


# Global prefetch manager
_prefetch_manager: Optional[PrefetchManager] = None


def get_prefetch_manager() -> PrefetchManager:
    """Get global prefetch manager instance."""
    global _prefetch_manager
    if _prefetch_manager is None:
        _prefetch_manager = PrefetchManager()
    return _prefetch_manager


# Convenience functions
def prefetch_preview_pages(cards: List[Dict[str, str]], current_page: int, 
                          total_pages: int, render_params: Dict[str, Any]) -> List[str]:
    """Prefetch adjacent preview pages."""
    return get_prefetch_manager().prefetch_preview_pages(
        cards, current_page, total_pages, render_params
    )


def prefetch_exports(cards: List[Dict[str, str]], export_params: Dict[str, Any],
                    formats: List[str] = None) -> List[str]:
    """Prefetch export formats."""
    return get_prefetch_manager().prefetch_export_formats(
        cards, export_params, formats
    )


def get_prefetch_stats() -> Dict[str, Any]:
    """Get prefetch statistics."""
    return get_prefetch_manager().get_stats()


def shutdown_prefetch() -> None:
    """Shutdown prefetch manager."""
    global _prefetch_manager
    if _prefetch_manager:
        _prefetch_manager.shutdown()
        _prefetch_manager = None
