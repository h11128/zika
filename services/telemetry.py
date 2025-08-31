"""
Telemetry and Monitoring System.
Implements structured logging, performance event schema, sampling rates, and reporting backend integration.
"""

import time
import uuid
import json
import logging
import threading
import hashlib
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import queue
from collections import defaultdict, deque

from core.feature_flags import get_feature_flag


class EventType(Enum):
    """Types of telemetry events."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEBUG = "debug"
    PERFORMANCE = "performance"
    USER_ACTION = "user_action"
    CACHE_EVENT = "cache_event"
    RENDER_EVENT = "render_event"
    EXPORT_EVENT = "export_event"


class SamplingRate(Enum):
    """Sampling rates for different event types."""
    ALWAYS = 1.0        # 100% - errors, critical events
    ROUTINE = 0.1       # 10% - routine operations
    HIGH_FREQUENCY = 0.01  # 1% - high-frequency events
    DEBUG_ONLY = 0.0    # 0% - debug events (only in dev)


@dataclass
class TelemetryContext:
    """Context information for telemetry events."""
    request_id: str
    session_generation: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    environment: str = "unknown"
    code_version: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class PerformanceEvent:
    """Performance telemetry event."""
    event_type: str
    operation: str
    duration_ms: float
    success: bool
    context: TelemetryContext
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance-specific fields
    memory_mb: Optional[float] = None
    cache_hit: Optional[bool] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['context'] = self.context.to_dict()
        return data


@dataclass
class UserActionEvent:
    """User action telemetry event."""
    action: str
    component: str
    context: TelemetryContext
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # User action specific fields
    input_type: Optional[str] = None
    value_changed: bool = False
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['context'] = self.context.to_dict()
        return data


@dataclass
class ErrorEvent:
    """Error telemetry event."""
    error_type: str
    error_message: str
    context: TelemetryContext
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Error-specific fields
    stack_trace: Optional[str] = None
    component: Optional[str] = None
    severity: str = "error"
    recoverable: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['context'] = self.context.to_dict()
        return data


class TelemetryCollector:
    """Collects and manages telemetry events with sampling and buffering."""
    
    def __init__(self, max_buffer_size: int = 1000, flush_interval_seconds: float = 30.0):
        self._max_buffer_size = max_buffer_size
        self._flush_interval_seconds = flush_interval_seconds
        
        # Event storage
        self._event_buffer: deque = deque(maxlen=max_buffer_size)
        self._event_queue: queue.Queue = queue.Queue(maxsize=max_buffer_size * 2)
        
        # Context management
        self._current_context: Optional[TelemetryContext] = None
        self._context_stack: List[TelemetryContext] = []
        
        # Sampling and filtering
        self._sampling_rates: Dict[EventType, float] = {
            EventType.ERROR: SamplingRate.ALWAYS.value,
            EventType.WARNING: SamplingRate.ALWAYS.value,
            EventType.PERFORMANCE: SamplingRate.ROUTINE.value,
            EventType.USER_ACTION: SamplingRate.ROUTINE.value,
            EventType.CACHE_EVENT: SamplingRate.HIGH_FREQUENCY.value,
            EventType.RENDER_EVENT: SamplingRate.HIGH_FREQUENCY.value,
            EventType.EXPORT_EVENT: SamplingRate.ROUTINE.value,
            EventType.INFO: SamplingRate.ROUTINE.value,
            EventType.DEBUG: SamplingRate.DEBUG_ONLY.value
        }
        
        # Statistics
        self._stats = {
            'events_collected': 0,
            'events_sampled': 0,
            'events_dropped': 0,
            'events_flushed': 0,
            'buffer_overflows': 0
        }
        
        # Background processing
        self._flush_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        
        # Reporting backends
        self._backends: List[Callable[[List[Dict[str, Any]]], None]] = []
        
        # Configuration
        self._enabled = get_feature_flag('telemetry_enabled', True)
        self._debug_mode = get_feature_flag('telemetry_debug', False)
        
        if self._enabled:
            self._start_background_processing()
    
    def set_context(self, context: TelemetryContext) -> None:
        """Set current telemetry context."""
        with self._lock:
            self._current_context = context
    
    def push_context(self, context: TelemetryContext) -> None:
        """Push context onto stack."""
        with self._lock:
            if self._current_context:
                self._context_stack.append(self._current_context)
            self._current_context = context
    
    def pop_context(self) -> Optional[TelemetryContext]:
        """Pop context from stack."""
        with self._lock:
            old_context = self._current_context
            if self._context_stack:
                self._current_context = self._context_stack.pop()
            else:
                self._current_context = None
            return old_context
    
    def record_performance(self, operation: str, duration_ms: float, 
                          success: bool = True, metadata: Optional[Dict[str, Any]] = None,
                          memory_mb: Optional[float] = None, cache_hit: Optional[bool] = None,
                          error_message: Optional[str] = None) -> None:
        """Record a performance event."""
        if not self._should_sample(EventType.PERFORMANCE):
            return
        
        context = self._get_current_context()
        event = PerformanceEvent(
            event_type="performance",
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            context=context,
            metadata=metadata or {},
            memory_mb=memory_mb,
            cache_hit=cache_hit,
            error_message=error_message
        )
        
        self._collect_event(event)
    
    def record_user_action(self, action: str, component: str,
                          metadata: Optional[Dict[str, Any]] = None,
                          input_type: Optional[str] = None,
                          value_changed: bool = False,
                          validation_errors: Optional[List[str]] = None) -> None:
        """Record a user action event."""
        if not self._should_sample(EventType.USER_ACTION):
            return
        
        context = self._get_current_context()
        event = UserActionEvent(
            action=action,
            component=component,
            context=context,
            metadata=metadata or {},
            input_type=input_type,
            value_changed=value_changed,
            validation_errors=validation_errors or []
        )

        # Add event_type field for consistency
        event_dict = event.to_dict()
        event_dict['event_type'] = 'user_action'
        self._collect_event(event_dict)
    
    def record_error(self, error_type: str, error_message: str,
                    metadata: Optional[Dict[str, Any]] = None,
                    stack_trace: Optional[str] = None,
                    component: Optional[str] = None,
                    severity: str = "error",
                    recoverable: bool = True) -> None:
        """Record an error event."""
        if not self._should_sample(EventType.ERROR):
            return
        
        context = self._get_current_context()
        event = ErrorEvent(
            error_type=error_type,
            error_message=error_message,
            context=context,
            metadata=metadata or {},
            stack_trace=stack_trace,
            component=component,
            severity=severity,
            recoverable=recoverable
        )

        # Add event_type field for consistency
        event_dict = event.to_dict()
        event_dict['event_type'] = 'error'
        self._collect_event(event_dict)
        
        # Also log to standard logging
        log_level = logging.ERROR if severity == "error" else logging.WARNING
        logging.log(log_level, f"Telemetry {severity}: {error_type} - {error_message}")
    
    def record_cache_event(self, operation: str, cache_type: str, hit: bool,
                          metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a cache event."""
        if not self._should_sample(EventType.CACHE_EVENT):
            return
        
        context = self._get_current_context()
        event = {
            'event_type': 'cache_event',
            'operation': operation,
            'cache_type': cache_type,
            'hit': hit,
            'context': context.to_dict(),
            'metadata': metadata or {}
        }
        
        self._collect_event(event)
    
    def add_backend(self, backend: Callable[[List[Dict[str, Any]]], None]) -> None:
        """Add a reporting backend."""
        with self._lock:
            self._backends.append(backend)
    
    def flush(self) -> int:
        """Manually flush events to backends."""
        with self._lock:
            events_to_flush = list(self._event_buffer)
            self._event_buffer.clear()
        
        if events_to_flush:
            self._send_to_backends(events_to_flush)
            self._stats['events_flushed'] += len(events_to_flush)
        
        return len(events_to_flush)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry statistics."""
        with self._lock:
            stats = dict(self._stats)
            stats.update({
                'buffer_size': len(self._event_buffer),
                'queue_size': self._event_queue.qsize(),
                'backends_count': len(self._backends),
                'enabled': self._enabled,
                'debug_mode': self._debug_mode
            })
            return stats
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """Shutdown telemetry collector."""
        self._shutdown_event.set()
        
        # Flush remaining events
        self.flush()
        
        # Wait for background thread
        if self._flush_thread and self._flush_thread.is_alive():
            self._flush_thread.join(timeout=timeout)
    
    def _should_sample(self, event_type: EventType) -> bool:
        """Determine if event should be sampled."""
        if not self._enabled:
            return False

        # Get sampling rate first
        rate = self._sampling_rates.get(event_type, 0.0)

        # Always sample in debug mode for debug events, but only if rate > 0
        if self._debug_mode and event_type == EventType.DEBUG and rate > 0.0:
            return True

        # Check sampling rate
        if rate >= 1.0:
            return True
        elif rate <= 0.0:
            return False
        
        # Use hash-based sampling for consistency
        context = self._get_current_context()
        sample_key = f"{context.session_generation}_{event_type.value}_{time.time():.0f}"
        hash_value = int(hashlib.md5(sample_key.encode()).hexdigest()[:8], 16)
        return (hash_value % 10000) < (rate * 10000)
    
    def _get_current_context(self) -> TelemetryContext:
        """Get current telemetry context."""
        with self._lock:
            if self._current_context:
                return self._current_context
            
            # Create default context
            return TelemetryContext(
                request_id=str(uuid.uuid4())[:8],
                session_generation=str(uuid.uuid4())[:8],
                timestamp=time.time()
            )
    
    def _collect_event(self, event: Union[PerformanceEvent, UserActionEvent, ErrorEvent, Dict[str, Any]]) -> None:
        """Collect an event for processing."""
        with self._lock:
            self._stats['events_collected'] += 1
            
            # Convert to dict if needed
            if hasattr(event, 'to_dict'):
                event_dict = event.to_dict()
            else:
                event_dict = event
            
            # Add to buffer
            try:
                self._event_buffer.append(event_dict)
                self._stats['events_sampled'] += 1
            except Exception as e:
                self._stats['events_dropped'] += 1
                if self._debug_mode:
                    logging.warning(f"Failed to buffer telemetry event: {e}")
    
    def _start_background_processing(self) -> None:
        """Start background processing thread."""
        self._flush_thread = threading.Thread(
            target=self._background_flush_loop,
            name="telemetry_flush",
            daemon=True
        )
        self._flush_thread.start()
    
    def _background_flush_loop(self) -> None:
        """Background loop for flushing events."""
        while not self._shutdown_event.is_set():
            try:
                # Wait for flush interval or shutdown
                if self._shutdown_event.wait(self._flush_interval_seconds):
                    break
                
                # Flush events
                self.flush()
                
            except Exception as e:
                if self._debug_mode:
                    logging.error(f"Error in telemetry flush loop: {e}")
                time.sleep(1.0)  # Prevent tight loop on errors
    
    def _send_to_backends(self, events: List[Dict[str, Any]]) -> None:
        """Send events to all configured backends."""
        for backend in self._backends:
            try:
                backend(events)
            except Exception as e:
                if self._debug_mode:
                    logging.error(f"Error sending events to backend: {e}")


class LoggingBackend:
    """Logging backend for telemetry events."""
    
    def __init__(self, logger_name: str = "telemetry"):
        self.logger = logging.getLogger(logger_name)
    
    def __call__(self, events: List[Dict[str, Any]]) -> None:
        """Send events to logging system."""
        for event in events:
            # Determine log level
            event_type = event.get('event_type', 'info')
            if event_type == 'error':
                level = logging.ERROR
            elif event_type == 'warning':
                level = logging.WARNING
            elif event_type == 'performance':
                level = logging.INFO
            else:
                level = logging.DEBUG
            
            # Format message
            message = self._format_event(event)
            
            # Log with structured data
            self.logger.log(level, message, extra={'telemetry_event': event})
    
    def _format_event(self, event: Dict[str, Any]) -> str:
        """Format event for logging."""
        event_type = event.get('event_type', 'unknown')
        context = event.get('context', {})
        request_id = context.get('request_id', 'unknown')
        
        if event_type == 'performance':
            operation = event.get('operation', 'unknown')
            duration = event.get('duration_ms', 0)
            success = event.get('success', True)
            return f"PERF [{request_id}] {operation}: {duration:.1f}ms {'✓' if success else '✗'}"
        
        elif event_type == 'user_action':
            action = event.get('action', 'unknown')
            component = event.get('component', 'unknown')
            return f"USER [{request_id}] {component}.{action}"
        
        elif event_type == 'error':
            error_type = event.get('error_type', 'unknown')
            error_message = event.get('error_message', 'unknown')
            return f"ERROR [{request_id}] {error_type}: {error_message}"
        
        else:
            return f"{event_type.upper()} [{request_id}] {json.dumps(event, default=str)}"


# Global telemetry collector
_telemetry_collector: Optional[TelemetryCollector] = None


def get_telemetry_collector() -> TelemetryCollector:
    """Get global telemetry collector instance."""
    global _telemetry_collector
    if _telemetry_collector is None:
        _telemetry_collector = TelemetryCollector()
        
        # Add default logging backend
        logging_backend = LoggingBackend()
        _telemetry_collector.add_backend(logging_backend)
    
    return _telemetry_collector


# Convenience functions
def set_telemetry_context(request_id: str, session_generation: str,
                         user_id: Optional[str] = None, session_id: Optional[str] = None,
                         environment: str = "unknown", code_version: str = "unknown") -> None:
    """Set telemetry context."""
    context = TelemetryContext(
        request_id=request_id,
        session_generation=session_generation,
        user_id=user_id,
        session_id=session_id,
        environment=environment,
        code_version=code_version
    )
    get_telemetry_collector().set_context(context)


def record_performance_event(operation: str, duration_ms: float, success: bool = True,
                            metadata: Optional[Dict[str, Any]] = None,
                            memory_mb: Optional[float] = None,
                            cache_hit: Optional[bool] = None) -> None:
    """Record a performance event."""
    get_telemetry_collector().record_performance(
        operation, duration_ms, success, metadata, memory_mb, cache_hit
    )


def record_user_action_event(action: str, component: str,
                            metadata: Optional[Dict[str, Any]] = None,
                            value_changed: bool = False) -> None:
    """Record a user action event."""
    get_telemetry_collector().record_user_action(
        action, component, metadata, value_changed=value_changed
    )


def record_error_event(error_type: str, error_message: str,
                      metadata: Optional[Dict[str, Any]] = None,
                      component: Optional[str] = None,
                      severity: str = "error") -> None:
    """Record an error event."""
    get_telemetry_collector().record_error(
        error_type, error_message, metadata, component=component, severity=severity
    )


def record_cache_event(operation: str, cache_type: str, hit: bool,
                      metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record a cache event."""
    get_telemetry_collector().record_cache_event(operation, cache_type, hit, metadata)


def get_telemetry_stats() -> Dict[str, Any]:
    """Get telemetry statistics."""
    return get_telemetry_collector().get_stats()


def flush_telemetry() -> int:
    """Flush telemetry events."""
    return get_telemetry_collector().flush()


# Context manager for telemetry context
class telemetry_context:
    """Context manager for telemetry context."""
    
    def __init__(self, request_id: str, session_generation: str, **kwargs):
        self.context = TelemetryContext(
            request_id=request_id,
            session_generation=session_generation,
            **kwargs
        )
        self.collector = get_telemetry_collector()
    
    def __enter__(self):
        self.collector.push_context(self.context)
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.collector.pop_context()
        
        # Record exception if one occurred
        if exc_type is not None:
            record_error_event(
                error_type=exc_type.__name__,
                error_message=str(exc_val),
                metadata={'stack_trace': str(exc_tb)},
                severity="error"
            )
