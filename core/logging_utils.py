"""
Logging utilities with session generation and request ID correlation.
Provides structured logging with proper context propagation.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from functools import wraps
from contextlib import contextmanager

# Import session generation function
import importlib.util
import os
spec = importlib.util.spec_from_file_location("ui_state_module", os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "state.py"))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)


class SessionAwareFormatter(logging.Formatter):
    """Custom formatter that includes session generation and request ID."""
    
    def format(self, record):
        # Add session context to log record
        try:
            record.session_generation = ui_state_module.get_session_generation()
        except Exception:
            record.session_generation = "unknown"
        
        # Add request ID if available
        if not hasattr(record, 'request_id'):
            record.request_id = getattr(_current_request_context, 'request_id', None) or "no-request"
        
        # Add component name if available
        if not hasattr(record, 'component'):
            record.component = getattr(_current_request_context, 'component', None) or record.name
        
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat() + 'Z'
        
        return super().format(record)


class StructuredFormatter(SessionAwareFormatter):
    """JSON formatter for structured logging."""
    
    def format(self, record):
        # Call parent to add session context
        super().format(record)
        
        log_entry = {
            'timestamp': record.timestamp,
            'level': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'component': record.component,
            'session_generation': record.session_generation,
            'request_id': record.request_id,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in log_entry and not key.startswith('_'):
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                              'filename', 'module', 'lineno', 'funcName', 'created', 
                              'msecs', 'relativeCreated', 'thread', 'threadName', 
                              'processName', 'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_entry[key] = value
        
        return json.dumps(log_entry, default=str)


class RequestContext:
    """Context for tracking request-specific information."""
    
    def __init__(self):
        self.request_id: Optional[str] = None
        self.component: Optional[str] = None
        self.operation: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.metadata: Dict[str, Any] = {}


# Global request context
_current_request_context = RequestContext()


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())[:8]  # Short ID for readability


@contextmanager
def request_context(component: str, operation: str = None, request_id: str = None, **metadata):
    """
    Context manager for request-scoped logging context.
    
    Args:
        component: Component name (e.g., 'ui.preview', 'services.export')
        operation: Operation name (e.g., 'render_cards', 'compute_digest')
        request_id: Optional request ID (generated if not provided)
        **metadata: Additional metadata to include in logs
    """
    global _current_request_context
    
    # Save previous context
    previous_context = RequestContext()
    previous_context.request_id = _current_request_context.request_id
    previous_context.component = _current_request_context.component
    previous_context.operation = _current_request_context.operation
    previous_context.start_time = _current_request_context.start_time
    previous_context.metadata = _current_request_context.metadata.copy()
    
    # Set new context
    _current_request_context.request_id = request_id or generate_request_id()
    _current_request_context.component = component
    _current_request_context.operation = operation
    _current_request_context.start_time = datetime.utcnow()
    _current_request_context.metadata = metadata
    
    try:
        # Log operation start
        logger = logging.getLogger(component)
        logger.info(f"Starting operation: {operation or 'unknown'}", extra={
            'operation': operation,
            'metadata': metadata
        })
        
        yield _current_request_context
        
        # Log operation completion
        duration = (datetime.utcnow() - _current_request_context.start_time).total_seconds()
        logger.info(f"Completed operation: {operation or 'unknown'}", extra={
            'operation': operation,
            'duration_seconds': duration,
            'metadata': metadata
        })
        
    except Exception as e:
        # Log operation failure
        duration = (datetime.utcnow() - _current_request_context.start_time).total_seconds()
        logger = logging.getLogger(component)
        logger.error(f"Failed operation: {operation or 'unknown'}", extra={
            'operation': operation,
            'duration_seconds': duration,
            'error': str(e),
            'metadata': metadata
        }, exc_info=True)
        raise
        
    finally:
        # Restore previous context
        _current_request_context.request_id = previous_context.request_id
        _current_request_context.component = previous_context.component
        _current_request_context.operation = previous_context.operation
        _current_request_context.start_time = previous_context.start_time
        _current_request_context.metadata = previous_context.metadata


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with session-aware formatting.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Configure handler if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        # Use structured logging in production, simple format in development
        try:
            # Check if we're in development mode
            import os
            if os.environ.get('ENVIRONMENT') == 'development':
                formatter = SessionAwareFormatter(
                    '%(timestamp)s [%(levelname)s] %(component)s:%(funcName)s:%(lineno)d '
                    '[req:%(request_id)s] [session:%(session_generation)s] %(message)s'
                )
            else:
                formatter = StructuredFormatter()
        except Exception:
            # Fallback to simple formatter
            formatter = SessionAwareFormatter(
                '%(asctime)s [%(levelname)s] %(name)s [session:%(session_generation)s] %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_session_event(event_type: str, **event_data):
    """
    Log a session-level event with proper context.
    
    Args:
        event_type: Type of event (e.g., 'session_start', 'cache_miss', 'error')
        **event_data: Additional event data
    """
    logger = get_logger('session_events')
    
    event_info = {
        'event_type': event_type,
        'session_info': ui_state_module.get_session_generation_info(),
        **event_data
    }
    
    logger.info(f"Session event: {event_type}", extra=event_info)


def log_performance_metric(metric_name: str, value: float, unit: str = None, **metadata):
    """
    Log a performance metric with session context.
    
    Args:
        metric_name: Name of the metric (e.g., 'render_time', 'cache_hit_rate')
        value: Metric value
        unit: Unit of measurement (e.g., 'ms', 'percent', 'bytes')
        **metadata: Additional metadata
    """
    logger = get_logger('performance')
    
    metric_info = {
        'metric_name': metric_name,
        'metric_value': value,
        'metric_unit': unit,
        **metadata
    }
    
    logger.info(f"Performance metric: {metric_name}={value}{unit or ''}", extra=metric_info)


def log_cache_event(cache_name: str, event_type: str, key: str = None, **event_data):
    """
    Log a cache-related event with session context.
    
    Args:
        cache_name: Name of the cache (e.g., 'preview', 'export')
        event_type: Type of event (e.g., 'hit', 'miss', 'eviction', 'clear')
        key: Cache key (optional)
        **event_data: Additional event data
    """
    logger = get_logger('cache_events')
    
    cache_info = {
        'cache_name': cache_name,
        'cache_event_type': event_type,
        'cache_key': key,
        **event_data
    }
    
    logger.info(f"Cache event: {cache_name}.{event_type}", extra=cache_info)


def operation_logger(component: str, operation: str = None):
    """
    Decorator for automatic operation logging with session context.
    
    Args:
        component: Component name
        operation: Operation name (defaults to function name)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            with request_context(component, op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_current_request_context() -> RequestContext:
    """Get the current request context."""
    return _current_request_context


def setup_logging(level: str = "INFO", structured: bool = None):
    """
    Set up logging configuration for the application.
    
    Args:
        level: Logging level
        structured: Whether to use structured logging (auto-detected if None)
    """
    import os
    
    # Auto-detect structured logging based on environment
    if structured is None:
        structured = os.environ.get('ENVIRONMENT') != 'development'
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add new handler with appropriate formatter
    handler = logging.StreamHandler()
    
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = SessionAwareFormatter(
            '%(timestamp)s [%(levelname)s] %(component)s [req:%(request_id)s] [session:%(session_generation)s] %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Log setup completion
    logger = get_logger(__name__)
    logger.info(f"Logging configured: level={level}, structured={structured}")
