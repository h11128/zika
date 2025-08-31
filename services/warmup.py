"""
Cache Warmup Strategy for Preview Pages.
Implements intelligent cache warming for nav_index±1 pages with memory-aware limits and cancellation.
"""

import threading
import time
import weakref
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from core.feature_flags import get_feature_flag
from services.prefetch import get_prefetch_manager, PrefetchTask, PrefetchType, PrefetchPriority
from services.cache_v2_strategy import get_preview_cache, CacheLevel
from services.performance_monitor import measure_performance, benchmark
from services.layout import paginate
from services.observability import record_cache_hit, record_cache_miss


class WarmupStrategy(Enum):
    """Cache warmup strategies."""
    ADJACENT_PAGES = "adjacent_pages"      # Warm nav_index±1
    PREDICTIVE = "predictive"              # Based on user patterns
    SEQUENTIAL = "sequential"              # Sequential page access
    SMART = "smart"                        # Combination of strategies


@dataclass
class WarmupConfig:
    """Configuration for cache warmup."""
    enabled: bool = True
    strategy: WarmupStrategy = WarmupStrategy.SMART
    max_pages_ahead: int = 2
    max_pages_behind: int = 1
    max_memory_mb: float = 50.0
    max_concurrent_warmups: int = 2
    warmup_timeout_seconds: float = 10.0
    cancel_outdated: bool = True
    
    # Pattern learning
    enable_pattern_learning: bool = True
    pattern_window_minutes: int = 10
    min_pattern_confidence: float = 0.7


@dataclass
class WarmupRequest:
    """Request for cache warmup."""
    request_id: str
    cards: List[Dict[str, str]]
    current_page: int
    total_pages: int
    preview_params: Dict[str, Any]
    priority: PrefetchPriority = PrefetchPriority.NORMAL
    strategy: WarmupStrategy = WarmupStrategy.ADJACENT_PAGES
    created_at: float = field(default_factory=time.time)


@dataclass
class WarmupResult:
    """Result of warmup operation."""
    request_id: str
    pages_warmed: List[int]
    pages_failed: List[int]
    cache_hits: int
    cache_misses: int
    duration_ms: float
    memory_used_mb: float


class PageAccessTracker:
    """Tracks page access patterns for predictive warmup."""
    
    def __init__(self, window_minutes: int = 10):
        self._window_minutes = window_minutes
        self._access_history: List[Tuple[int, float]] = []  # (page, timestamp)
        self._transition_counts: Dict[Tuple[int, int], int] = {}  # (from_page, to_page) -> count
        self._lock = threading.RLock()
    
    def record_page_access(self, page: int) -> None:
        """Record page access for pattern learning."""
        with self._lock:
            current_time = time.time()
            
            # Record transition if we have previous access
            if self._access_history:
                last_page = self._access_history[-1][0]
                if last_page != page:  # Only record actual transitions
                    transition = (last_page, page)
                    self._transition_counts[transition] = self._transition_counts.get(transition, 0) + 1
            
            # Add current access
            self._access_history.append((page, current_time))
            
            # Clean old history
            cutoff_time = current_time - (self._window_minutes * 60)
            self._access_history = [(p, t) for p, t in self._access_history if t >= cutoff_time]
    
    def predict_next_pages(self, current_page: int, max_predictions: int = 3) -> List[Tuple[int, float]]:
        """Predict next likely pages with confidence scores."""
        with self._lock:
            predictions = []
            
            # Find transitions from current page
            for (from_page, to_page), count in self._transition_counts.items():
                if from_page == current_page:
                    # Calculate confidence based on frequency
                    total_from_current = sum(
                        c for (f, t), c in self._transition_counts.items() if f == current_page
                    )
                    confidence = count / max(1, total_from_current)
                    predictions.append((to_page, confidence))
            
            # Sort by confidence and return top predictions
            predictions.sort(key=lambda x: x[1], reverse=True)
            return predictions[:max_predictions]
    
    def get_access_frequency(self, page: int) -> float:
        """Get access frequency for a page (accesses per minute)."""
        with self._lock:
            current_time = time.time()
            cutoff_time = current_time - (self._window_minutes * 60)
            
            recent_accesses = [t for p, t in self._access_history if p == page and t >= cutoff_time]
            return len(recent_accesses) / self._window_minutes


class CacheWarmupManager:
    """Manages cache warmup operations with memory awareness and cancellation."""
    
    def __init__(self, config: Optional[WarmupConfig] = None):
        self.config = config or WarmupConfig()
        
        # State management
        self._active_requests: Dict[str, WarmupRequest] = {}
        self._active_tasks: Dict[str, List[str]] = {}  # request_id -> task_ids
        self._completed_requests: Dict[str, WarmupResult] = {}
        self._cancelled_requests: Set[str] = set()
        
        # Pattern tracking
        self._access_tracker = PageAccessTracker(self.config.pattern_window_minutes)
        
        # Memory tracking
        self._estimated_memory_mb = 0.0
        self._page_size_estimates: Dict[str, float] = {}  # cache_key -> size_mb
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Integration
        self._prefetch_manager = get_prefetch_manager()
        self._preview_cache = get_preview_cache()
        
        # Statistics
        self._stats = {
            'requests_submitted': 0,
            'requests_completed': 0,
            'requests_cancelled': 0,
            'pages_warmed': 0,
            'cache_hits': 0,
            'memory_saved_mb': 0.0
        }
    
    def warmup_pages(self, cards: List[Dict[str, str]], current_page: int, 
                    total_pages: int, preview_params: Dict[str, Any],
                    strategy: Optional[WarmupStrategy] = None) -> str:
        """
        Request cache warmup for pages around current page.
        
        Args:
            cards: List of card data
            current_page: Current page index
            total_pages: Total number of pages
            preview_params: Preview rendering parameters
            strategy: Warmup strategy to use
        
        Returns:
            Request ID for tracking
        """
        if not self.config.enabled or not get_feature_flag('cache_warmup', True):
            return ""
        
        # Generate request ID
        import uuid
        request_id = str(uuid.uuid4())[:8]
        
        # Create warmup request
        request = WarmupRequest(
            request_id=request_id,
            cards=cards,
            current_page=current_page,
            total_pages=total_pages,
            preview_params=preview_params,
            strategy=strategy or self.config.strategy
        )
        
        with self._lock:
            self._active_requests[request_id] = request
            self._stats['requests_submitted'] += 1
        
        # Record page access for pattern learning
        if self.config.enable_pattern_learning:
            self._access_tracker.record_page_access(current_page)
        
        # Start warmup in background
        threading.Thread(
            target=self._execute_warmup,
            args=(request,),
            daemon=True
        ).start()
        
        return request_id
    
    def cancel_warmup(self, request_id: str) -> bool:
        """Cancel a warmup request."""
        with self._lock:
            if request_id in self._active_requests:
                self._cancelled_requests.add(request_id)
                
                # Cancel associated prefetch tasks
                if request_id in self._active_tasks:
                    for task_id in self._active_tasks[request_id]:
                        self._prefetch_manager.cancel_task(task_id)
                    del self._active_tasks[request_id]
                
                del self._active_requests[request_id]
                self._stats['requests_cancelled'] += 1
                return True
        
        return False
    
    def cancel_outdated_warmups(self, current_request_id: str) -> int:
        """Cancel outdated warmup requests."""
        if not self.config.cancel_outdated:
            return 0
        
        cancelled_count = 0
        with self._lock:
            # Cancel all requests except the current one
            to_cancel = [rid for rid in self._active_requests.keys() if rid != current_request_id]
            
            for request_id in to_cancel:
                if self.cancel_warmup(request_id):
                    cancelled_count += 1
        
        return cancelled_count
    
    def get_warmup_result(self, request_id: str) -> Optional[WarmupResult]:
        """Get result of a warmup request."""
        with self._lock:
            return self._completed_requests.get(request_id)
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage estimates."""
        with self._lock:
            return {
                'estimated_mb': self._estimated_memory_mb,
                'limit_mb': self.config.max_memory_mb,
                'utilization_percent': (self._estimated_memory_mb / self.config.max_memory_mb * 100)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get warmup statistics."""
        with self._lock:
            stats = dict(self._stats)
            stats.update({
                'active_requests': len(self._active_requests),
                'completed_requests': len(self._completed_requests),
                'memory_usage': self.get_memory_usage(),
                'pattern_transitions': len(self._access_tracker._transition_counts)
            })
            return stats
    
    def _execute_warmup(self, request: WarmupRequest) -> None:
        """Execute warmup request."""
        start_time = time.time()
        
        try:
            # Check if request was cancelled
            if request.request_id in self._cancelled_requests:
                return
            
            # Determine pages to warm
            pages_to_warm = self._determine_pages_to_warm(request)
            
            # Check memory limits
            if not self._check_memory_limits(len(pages_to_warm)):
                logging.warning(f"Warmup {request.request_id} cancelled due to memory limits")
                return
            
            # Submit prefetch tasks
            task_ids = self._submit_warmup_tasks(request, pages_to_warm)
            
            with self._lock:
                self._active_tasks[request.request_id] = task_ids
            
            # Wait for completion or timeout
            self._wait_for_completion(request, task_ids)
            
        except Exception as e:
            logging.error(f"Error executing warmup {request.request_id}: {e}")
        finally:
            # Cleanup
            with self._lock:
                if request.request_id in self._active_requests:
                    del self._active_requests[request.request_id]
                if request.request_id in self._active_tasks:
                    del self._active_tasks[request.request_id]
                self._cancelled_requests.discard(request.request_id)
    
    def _determine_pages_to_warm(self, request: WarmupRequest) -> List[int]:
        """Determine which pages to warm based on strategy."""
        pages = []
        
        if request.strategy == WarmupStrategy.ADJACENT_PAGES:
            # Warm adjacent pages
            for offset in range(-self.config.max_pages_behind, self.config.max_pages_ahead + 1):
                page = request.current_page + offset
                if 0 <= page < request.total_pages and page != request.current_page:
                    pages.append(page)
        
        elif request.strategy == WarmupStrategy.PREDICTIVE:
            # Use pattern prediction
            predictions = self._access_tracker.predict_next_pages(
                request.current_page, max_predictions=3
            )
            for page, confidence in predictions:
                if confidence >= self.config.min_pattern_confidence:
                    if 0 <= page < request.total_pages:
                        pages.append(page)
        
        elif request.strategy == WarmupStrategy.SEQUENTIAL:
            # Warm next few pages in sequence
            for i in range(1, self.config.max_pages_ahead + 1):
                page = request.current_page + i
                if page < request.total_pages:
                    pages.append(page)
        
        elif request.strategy == WarmupStrategy.SMART:
            # Combine strategies
            # Start with adjacent pages
            adjacent_pages = []
            for offset in range(-self.config.max_pages_behind, self.config.max_pages_ahead + 1):
                page = request.current_page + offset
                if 0 <= page < request.total_pages and page != request.current_page:
                    adjacent_pages.append(page)
            
            # Add predictive pages if they're not already included
            predictions = self._access_tracker.predict_next_pages(request.current_page, 2)
            for page, confidence in predictions:
                if confidence >= self.config.min_pattern_confidence:
                    if 0 <= page < request.total_pages and page not in adjacent_pages:
                        adjacent_pages.append(page)
            
            pages = adjacent_pages[:self.config.max_pages_ahead + self.config.max_pages_behind]
        
        return pages
    
    def _check_memory_limits(self, num_pages: int) -> bool:
        """Check if warmup would exceed memory limits."""
        # Estimate memory needed (rough estimate: 1MB per page)
        estimated_needed_mb = num_pages * 1.0
        
        with self._lock:
            if self._estimated_memory_mb + estimated_needed_mb > self.config.max_memory_mb:
                return False
        
        return True
    
    def _submit_warmup_tasks(self, request: WarmupRequest, pages: List[int]) -> List[str]:
        """Submit prefetch tasks for pages."""
        task_ids = []
        
        for page in pages:
            # Create cache key for this page
            cache_key = self._create_page_cache_key(page, request.preview_params)
            
            # Check if already cached
            if self._preview_cache.get(cache_key) is not None:
                continue  # Skip already cached pages
            
            # Create prefetch task
            task_id = f"warmup_{request.request_id}_{page}"
            
            task = PrefetchTask(
                task_id=task_id,
                task_type=PrefetchType.PREVIEW_PAGE,
                priority=PrefetchPriority.LOW,  # Low priority for warmup
                target_function=self._render_page_for_warmup,
                args=(request.cards, page, request.preview_params),
                kwargs={},
                cache_key=cache_key,
                tags={
                    'type': 'warmup',
                    'request_id': request.request_id,
                    'page': str(page)
                },
                timeout_seconds=self.config.warmup_timeout_seconds
            )
            
            if self._prefetch_manager.submit_task(task):
                task_ids.append(task_id)
        
        return task_ids
    
    def _wait_for_completion(self, request: WarmupRequest, task_ids: List[str]) -> None:
        """Wait for warmup tasks to complete."""
        timeout = self.config.warmup_timeout_seconds
        start_time = time.time()
        
        pages_warmed = []
        pages_failed = []
        cache_hits = 0
        cache_misses = 0
        
        while task_ids and (time.time() - start_time) < timeout:
            # Check if request was cancelled
            if request.request_id in self._cancelled_requests:
                break
            
            # Check completed tasks
            completed_tasks = []
            for task_id in task_ids:
                result = self._prefetch_manager.get_task_result(task_id)
                if result is not None:
                    completed_tasks.append(task_id)
                    
                    # Extract page number from task_id
                    page_str = task_id.split('_')[-1]
                    try:
                        page = int(page_str)
                        if result.success:
                            pages_warmed.append(page)
                            if result.cache_hit:
                                cache_hits += 1
                            else:
                                cache_misses += 1
                        else:
                            pages_failed.append(page)
                    except ValueError:
                        pass
            
            # Remove completed tasks
            for task_id in completed_tasks:
                task_ids.remove(task_id)
            
            if task_ids:
                time.sleep(0.1)  # Small delay before checking again
        
        # Create result
        duration_ms = (time.time() - start_time) * 1000
        result = WarmupResult(
            request_id=request.request_id,
            pages_warmed=pages_warmed,
            pages_failed=pages_failed,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            duration_ms=duration_ms,
            memory_used_mb=len(pages_warmed) * 1.0  # Rough estimate
        )
        
        with self._lock:
            self._completed_requests[request.request_id] = result
            self._stats['requests_completed'] += 1
            self._stats['pages_warmed'] += len(pages_warmed)
            self._stats['cache_hits'] += cache_hits
    
    def _render_page_for_warmup(self, cards: List[Dict[str, str]], 
                               page: int, preview_params: Dict[str, Any]) -> str:
        """Render a page for warmup (placeholder implementation)."""
        # This would integrate with the actual preview rendering pipeline
        # For now, return a placeholder
        return f"<html>Warmed page {page} with {len(cards)} cards</html>"
    
    def _create_page_cache_key(self, page: int, preview_params: Dict[str, Any]) -> str:
        """Create cache key for a page."""
        import hashlib
        import json
        
        key_data = {
            'page': page,
            'params': preview_params
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()


# Global warmup manager
_warmup_manager: Optional[CacheWarmupManager] = None


def get_warmup_manager() -> CacheWarmupManager:
    """Get global warmup manager instance."""
    global _warmup_manager
    if _warmup_manager is None:
        _warmup_manager = CacheWarmupManager()
    return _warmup_manager


# Convenience functions
def warmup_adjacent_pages(cards: List[Dict[str, str]], current_page: int,
                         total_pages: int, preview_params: Dict[str, Any]) -> str:
    """Warmup adjacent pages around current page."""
    return get_warmup_manager().warmup_pages(
        cards, current_page, total_pages, preview_params, WarmupStrategy.ADJACENT_PAGES
    )


def warmup_predictive_pages(cards: List[Dict[str, str]], current_page: int,
                           total_pages: int, preview_params: Dict[str, Any]) -> str:
    """Warmup pages based on predictive patterns."""
    return get_warmup_manager().warmup_pages(
        cards, current_page, total_pages, preview_params, WarmupStrategy.PREDICTIVE
    )


def cancel_outdated_warmups(current_request_id: str) -> int:
    """Cancel outdated warmup requests."""
    return get_warmup_manager().cancel_outdated_warmups(current_request_id)


def get_warmup_stats() -> Dict[str, Any]:
    """Get warmup statistics."""
    return get_warmup_manager().get_stats()
