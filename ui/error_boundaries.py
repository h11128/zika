"""
Error boundaries and recovery mechanisms for the UI refactor.
Provides structured error handling, fallback UI, and graceful degradation.
"""

import traceback
import logging
from typing import Any, Callable, Optional, Dict, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import streamlit as st

from ui.state import get_session_generation


class ErrorType(Enum):
    """Classification of error types."""
    CRITICAL = "critical"      # Immediate action required
    WARNING = "warning"        # User action recommended
    INFO = "info"             # Background/non-critical


@dataclass
class ErrorInfo:
    """Structured error information."""
    type: ErrorType
    message: str
    context: Dict[str, Any]
    timestamp: datetime
    session_generation: str
    component_name: Optional[str] = None
    digest_context: Optional[str] = None
    stack_trace: Optional[str] = None


class ErrorBoundary:
    """Error boundary for UI components with fallback rendering."""
    
    def __init__(self, component_name: str, fallback_ui: Optional[Callable] = None):
        self.component_name = component_name
        self.fallback_ui = fallback_ui or self._default_fallback
        self.logger = logging.getLogger(f"ui.{component_name}")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with error boundary."""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return self._handle_error(e, func.__name__, args, kwargs)
        return wrapper
    
    def wrap(self, func: Callable, *args, **kwargs) -> Any:
        """Wrap a function call with error boundary."""
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return self._handle_error(e, func.__name__, args, kwargs)
    
    def _handle_error(self, error: Exception, func_name: str, args: tuple, kwargs: dict) -> Any:
        """Handle error and return fallback UI."""
        # Create error info
        error_info = ErrorInfo(
            type=self._classify_error(error),
            message=str(error),
            context={
                'function': func_name,
                'component': self.component_name,
                'args_count': len(args),
                'kwargs_keys': list(kwargs.keys()),
            },
            timestamp=datetime.utcnow(),
            session_generation=get_session_generation(),
            component_name=self.component_name,
            stack_trace=traceback.format_exc()
        )
        
        # Log error
        self._log_error(error_info)
        
        # Store error in session state for debug panel
        self._store_error(error_info)
        
        # Return fallback UI
        return self.fallback_ui(error_info)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on exception."""
        # State service failures are critical
        if 'state' in str(error).lower() or 'session' in str(error).lower():
            return ErrorType.CRITICAL
        
        # Cache/performance issues are warnings
        if 'cache' in str(error).lower() or 'timeout' in str(error).lower():
            return ErrorType.WARNING
        
        # Default to info for other errors
        return ErrorType.INFO
    
    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log structured error information."""
        log_data = {
            'error_type': error_info.type.value,
            'component': error_info.component_name,
            'session_generation': error_info.session_generation,
            'timestamp': error_info.timestamp.isoformat(),
            'message': error_info.message,
            'context': error_info.context,
        }
        
        if error_info.type == ErrorType.CRITICAL:
            self.logger.error("Critical error in component", extra=log_data)
        elif error_info.type == ErrorType.WARNING:
            self.logger.warning("Warning in component", extra=log_data)
        else:
            self.logger.info("Info error in component", extra=log_data)
    
    def _store_error(self, error_info: ErrorInfo) -> None:
        """Store error in session state for debug panel."""
        if not hasattr(st.session_state, 'ui_errors'):
            st.session_state.ui_errors = []
        
        # Keep only last 10 errors to avoid memory issues
        st.session_state.ui_errors.append(error_info)
        if len(st.session_state.ui_errors) > 10:
            st.session_state.ui_errors = st.session_state.ui_errors[-10:]
    
    def _default_fallback(self, error_info: ErrorInfo) -> None:
        """Default fallback UI for errors."""
        if error_info.type == ErrorType.CRITICAL:
            st.error(f"❌ Critical error in {self.component_name}: {error_info.message}")
            if st.button(f"Retry {self.component_name}", key=f"retry_{self.component_name}_{error_info.timestamp.timestamp()}"):
                st.rerun()
        elif error_info.type == ErrorType.WARNING:
            st.warning(f"⚠️ Warning in {self.component_name}: {error_info.message}")
        else:
            st.info(f"ℹ️ {self.component_name}: {error_info.message}")


# Pre-configured error boundaries for common components
preview_boundary = ErrorBoundary("preview", lambda e: st.error("Preview temporarily unavailable"))
editor_boundary = ErrorBoundary("editor", lambda e: st.error("Editor temporarily unavailable"))
export_boundary = ErrorBoundary("export", lambda e: st.error("Export temporarily unavailable"))
sidebar_boundary = ErrorBoundary("sidebar", lambda e: st.error("Sidebar temporarily unavailable"))


def with_error_boundary(component_name: str, fallback_ui: Optional[Callable] = None):
    """Decorator factory for error boundaries."""
    boundary = ErrorBoundary(component_name, fallback_ui)
    return boundary


def safe_call(func: Callable, *args, component_name: str = "unknown", **kwargs) -> Any:
    """Safely call a function with error boundary."""
    boundary = ErrorBoundary(component_name)
    return boundary.wrap(func, *args, **kwargs)


class GracefulDegradation:
    """Manages graceful degradation of features."""
    
    def __init__(self):
        self.disabled_features: set = set()
    
    def disable_feature(self, feature_name: str, reason: str = "") -> None:
        """Disable a feature due to errors."""
        self.disabled_features.add(feature_name)
        if not hasattr(st.session_state, 'disabled_features'):
            st.session_state.disabled_features = {}
        st.session_state.disabled_features[feature_name] = {
            'reason': reason,
            'disabled_at': datetime.utcnow().isoformat(),
            'session_generation': get_session_generation(),
        }
    
    def is_feature_disabled(self, feature_name: str) -> bool:
        """Check if a feature is disabled."""
        return feature_name in self.disabled_features
    
    def enable_feature(self, feature_name: str) -> None:
        """Re-enable a feature."""
        self.disabled_features.discard(feature_name)
        if hasattr(st.session_state, 'disabled_features'):
            st.session_state.disabled_features.pop(feature_name, None)
    
    def get_disabled_features(self) -> Dict[str, Dict[str, str]]:
        """Get list of disabled features with reasons."""
        return getattr(st.session_state, 'disabled_features', {})


# Global degradation manager
_degradation_manager = GracefulDegradation()


def disable_feature(feature_name: str, reason: str = "") -> None:
    """Disable a feature globally."""
    _degradation_manager.disable_feature(feature_name, reason)


def is_feature_disabled(feature_name: str) -> bool:
    """Check if a feature is disabled globally."""
    return _degradation_manager.is_feature_disabled(feature_name)


def enable_feature(feature_name: str) -> None:
    """Re-enable a feature globally."""
    _degradation_manager.enable_feature(feature_name)


def get_disabled_features() -> Dict[str, Dict[str, str]]:
    """Get list of disabled features."""
    return _degradation_manager.get_disabled_features()


def clear_cache_on_corruption(cache_type: str = "all") -> None:
    """Clear caches in order when corruption is detected."""
    # Clear in order: page-slice → preview → export → session (only when corruption detected)
    if cache_type in ("all", "page_slice"):
        # Clear page slice cache
        if hasattr(st.session_state, 'page_slice_cache'):
            st.session_state.page_slice_cache = {}
    
    if cache_type in ("all", "preview"):
        # Clear preview cache
        if hasattr(st.session_state, 'preview_cache'):
            st.session_state.preview_cache = {}
    
    if cache_type in ("all", "export"):
        # Clear export cache
        if hasattr(st.session_state, 'export_ready'):
            st.session_state.export_ready = {}
        if hasattr(st.session_state, 'export_data'):
            st.session_state.export_data = {}
    
    if cache_type == "session":
        # Only clear session when corruption is detected
        # This is the nuclear option
        for key in list(st.session_state.keys()):
            if key.startswith('cache_') or key.endswith('_cache'):
                del st.session_state[key]


def show_error_debug_panel() -> None:
    """Show debug panel with recent errors (for development)."""
    if not hasattr(st.session_state, 'ui_errors'):
        st.info("No recent errors")
        return
    
    errors = st.session_state.ui_errors
    if not errors:
        st.info("No recent errors")
        return
    
    st.subheader("Recent Errors")
    for i, error in enumerate(reversed(errors)):
        with st.expander(f"{error.type.value.upper()}: {error.component_name} - {error.message[:50]}..."):
            st.write(f"**Type:** {error.type.value}")
            st.write(f"**Component:** {error.component_name}")
            st.write(f"**Time:** {error.timestamp}")
            st.write(f"**Session:** {error.session_generation}")
            st.write(f"**Message:** {error.message}")
            if error.context:
                st.write("**Context:**")
                st.json(error.context)
            if error.stack_trace:
                st.write("**Stack Trace:**")
                st.code(error.stack_trace)
    
    if st.button("Clear Error History"):
        st.session_state.ui_errors = []
        st.rerun()


def show_degradation_status() -> None:
    """Show status of disabled features."""
    disabled = get_disabled_features()
    if not disabled:
        st.success("All features enabled")
        return
    
    st.warning(f"{len(disabled)} features disabled")
    for feature, info in disabled.items():
        with st.expander(f"Disabled: {feature}"):
            st.write(f"**Reason:** {info['reason']}")
            st.write(f"**Disabled at:** {info['disabled_at']}")
            if st.button(f"Re-enable {feature}", key=f"enable_{feature}"):
                enable_feature(feature)
                st.rerun()
