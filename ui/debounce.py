"""
Debouncing system for UI interactions.
Provides form semantics and atomic commits with configurable debouncing.
"""

import time
import threading
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import streamlit as st

from core.feature_flags import get_feature_flag
try:
    from ui.state import set_options_batch, ChangeSet
except ImportError:
    # Fallback for compatibility
    from dataclasses import dataclass

    @dataclass
    class ChangeSet:
        """Compatibility ChangeSet for tests."""
        affects_processing: bool = False
        affects_layout: bool = False
        affects_style: bool = False
        affects_navigation: bool = False
        affects_export: bool = False
        nav_reset_required: bool = False

    def set_options_batch(changes):
        """Compatibility function for tests."""
        import streamlit as st
        for key, value in changes.items():
            setattr(st.session_state, key, value)
        return ChangeSet()
from ui.ports import get_ui_adapter, ComponentConfig


@dataclass
class PendingChange:
    """Represents a pending UI change."""
    key: str
    value: Any
    timestamp: datetime
    source: str = "user_input"
    callback: Optional[callable] = None


@dataclass
class DebounceConfig:
    """Configuration for debouncing behavior."""
    immediate_delay_ms: int = 150  # For immediate interactions (sliders, etc.)
    form_delay_ms: int = 250      # For form inputs (text, numbers)
    batch_delay_ms: int = 500     # For batch operations
    max_pending_changes: int = 50  # Prevent memory issues


class DebounceManager:
    """Manages debounced UI changes with form semantics."""
    
    def __init__(self, config: DebounceConfig = None):
        self.config = config or DebounceConfig()
        self.pending_changes: Dict[str, PendingChange] = {}
        self.last_flush_time: Optional[datetime] = None
        self.flush_timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()
    
    def schedule_change(self, key: str, value: Any, delay_ms: Optional[int] = None,
                       source: str = "user_input") -> None:
        """
        Schedule a change to be applied after debounce delay.
        
        Args:
            key: State key to change
            value: New value
            delay_ms: Custom delay, or use config default
            source: Source of the change for debugging
        """
        if not get_feature_flag('ui_debouncing', True):
            # Fallback to immediate application
            self._apply_changes_immediate({key: value})
            return
        
        try:
            with self.lock:
                # Add to pending changes
                change = PendingChange(
                    key=key,
                    value=value,
                    timestamp=datetime.utcnow(),
                    source=source
                )
                self.pending_changes[key] = change
                
                # Limit pending changes to prevent memory issues
                if len(self.pending_changes) > self.config.max_pending_changes:
                    self._flush_oldest_changes()
                
                # Determine delay
                if delay_ms is None:
                    if source == "immediate":
                        delay_ms = self.config.immediate_delay_ms
                    elif source == "form":
                        delay_ms = self.config.form_delay_ms
                    else:
                        delay_ms = self.config.batch_delay_ms
                
                # Cancel existing timer
                if self.flush_timer:
                    try:
                        self.flush_timer.cancel()
                    except Exception:
                        pass  # Timer might already be cancelled
                
                # Schedule new flush
                try:
                    self.flush_timer = threading.Timer(
                        delay_ms / 1000.0,  # Convert to seconds
                        self._flush_pending_changes
                    )
                    self.flush_timer.start()
                except Exception as e:
                    # Fallback to immediate application if timer fails
                    self._log_error(f"Timer scheduling failed: {e}")
                    self._apply_changes_immediate({key: value})
        except Exception as e:
            # Fallback to immediate application if lock fails
            self._log_error(f"Debounce scheduling failed: {e}")
            self._apply_changes_immediate({key: value})    
    def schedule_immediate(self, key: str, value: Any) -> None:
        """Schedule an immediate change (sliders, toggles)."""
        self.schedule_change(key, value, source="immediate")
    
    def schedule_form_input(self, key: str, value: Any) -> None:
        """Schedule a form input change (text inputs, numbers)."""
        self.schedule_change(key, value, source="form")
    
    def schedule_batch(self, changes: Dict[str, Any]) -> None:
        """Schedule multiple changes as a batch."""
        for key, value in changes.items():
            self.schedule_change(key, value, source="batch")

    def debounce_update(self, key: str, value: Any, callback: Optional[callable] = None) -> None:
        """Schedule a debounced update with optional callback."""
        self.schedule_change(key, value, source="update")
        if callback:
            # Store callback in the pending change for later execution
            with self.lock:
                if key in self.pending_changes:
                    self.pending_changes[key].callback = callback

    def is_pending(self, key: str) -> bool:
        """Check if a key has pending changes."""
        with self.lock:
            return key in self.pending_changes

    def flush_key(self, key: str) -> None:
        """Flush a specific key immediately."""
        with self.lock:
            if key in self.pending_changes:
                change = self.pending_changes.pop(key)
                self._apply_changes_immediate({key: change.value})
                # Execute callback if present
                if change.callback:
                    try:
                        change.callback(key, change.value)
                    except Exception as e:
                        self._log_error(f"Callback execution failed for {key}: {e}")

    def flush_now(self) -> ChangeSet:
        """Immediately flush all pending changes."""
        with self.lock:
            if self.flush_timer:
                self.flush_timer.cancel()
                self.flush_timer = None
            
            return self._flush_pending_changes()
    
    def has_pending_changes(self) -> bool:
        """Check if there are pending changes."""
        with self.lock:
            return len(self.pending_changes) > 0
    
    def get_pending_change(self, key: str) -> Optional[Any]:
        """Get pending value for a key, or None if not pending."""
        with self.lock:
            change = self.pending_changes.get(key)
            return change.value if change else None
    
    def cancel_pending(self, key: str) -> bool:
        """Cancel a pending change."""
        with self.lock:
            if key in self.pending_changes:
                del self.pending_changes[key]
                return True
            return False
    
    def _flush_pending_changes(self) -> ChangeSet:
        """Flush all pending changes to state service."""
        with self.lock:
            if not self.pending_changes:
                return ChangeSet()
            
            # Collect changes
            changes = {key: change.value for key, change in self.pending_changes.items()}
            
            # Clear pending
            self.pending_changes.clear()
            self.last_flush_time = datetime.utcnow()
            
            # Apply through state service
            try:
                changeset = set_options_batch(changes)
                
                # Log for debugging
                self._log_flush(changes, changeset)
                
                return changeset
            except Exception as e:
                # Fallback to immediate application
                self._apply_changes_immediate(changes)
                return ChangeSet()
    
    def _flush_oldest_changes(self) -> None:
        """Flush oldest changes when limit exceeded."""
        if len(self.pending_changes) <= self.config.max_pending_changes:
            return
        
        # Sort by timestamp and flush oldest half
        sorted_changes = sorted(
            self.pending_changes.items(),
            key=lambda x: x[1].timestamp
        )
        
        flush_count = len(sorted_changes) // 2
        changes_to_flush = dict(sorted_changes[:flush_count])
        
        # Remove from pending
        for key in changes_to_flush:
            del self.pending_changes[key]
        
        # Apply immediately
        self._apply_changes_immediate(changes_to_flush)
    
    def _apply_changes_immediate(self, changes: Dict[str, Any]) -> None:
        """Apply changes immediately without debouncing."""
        try:
            set_options_batch(changes)
        except Exception:
            # Fallback to direct session state
            for key, value in changes.items():
                setattr(st.session_state, key, value)
    
    def _log_flush(self, changes: Dict[str, Any], changeset: ChangeSet) -> None:
        """Log flush operation for debugging."""
        try:
            import logging
            logger = logging.getLogger('ui.debounce')
            logger.debug(
                f"Flushed {len(changes)} changes: {list(changes.keys())}, "
                f"affects: layout={changeset.affects_layout}, "
                f"style={changeset.affects_style}, "
                f"processing={changeset.affects_processing}"
            )
        except Exception:
            pass
    
    def _log_error(self, message: str) -> None:
        """Log error message for debugging."""
        try:
            import logging
            logger = logging.getLogger('ui.debounce')
            logger.error(f"Debounce error: {message}")
        except Exception:
            pass

# Global debounce manager
_debounce_manager: Optional[DebounceManager] = None


def get_debounce_manager() -> DebounceManager:
    """Get or create the global debounce manager."""
    global _debounce_manager
    if _debounce_manager is None:
        _debounce_manager = DebounceManager()
    return _debounce_manager


# Convenience functions
def debounce_immediate(key: str, value: Any) -> None:
    """Schedule an immediate debounced change."""
    get_debounce_manager().schedule_immediate(key, value)


def debounce_form_input(key: str, value: Any) -> None:
    """Schedule a form input debounced change."""
    get_debounce_manager().schedule_form_input(key, value)


def debounce_batch(changes: Dict[str, Any]) -> None:
    """Schedule multiple debounced changes."""
    get_debounce_manager().schedule_batch(changes)


def debounce_state_update(key: str, value: Any) -> None:
    """Schedule a state update with debouncing."""
    get_debounce_manager().schedule_form_input(key, value)


def debounce_batch_update(changes: Dict[str, Any]) -> None:
    """Schedule multiple state updates with debouncing."""
    get_debounce_manager().schedule_batch(changes)


def flush_debounced_updates() -> ChangeSet:
    """Flush all pending debounced updates."""
    return get_debounce_manager().flush_now()


def flush_debounced_changes() -> ChangeSet:
    """Flush all pending debounced changes."""
    return get_debounce_manager().flush_now()


def has_pending_changes() -> bool:
    """Check if there are pending debounced changes."""
    return get_debounce_manager().has_pending_changes()


def get_pending_value(key: str, default: Any = None) -> Any:
    """Get pending value for a key, or current session state value."""
    pending = get_debounce_manager().get_pending_change(key)
    if pending is not None:
        return pending
    return getattr(st.session_state, key, default)


# Form semantics helpers
class FormContext:
    """Context manager for form-like interactions."""
    
    def __init__(self, auto_flush: bool = True):
        self.auto_flush = auto_flush
        self.changes: Dict[str, Any] = {}
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.auto_flush and self.changes:
            debounce_batch(self.changes)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the form context."""
        self.changes[key] = value
    
    def commit(self) -> ChangeSet:
        """Manually commit changes."""
        if self.changes:
            debounce_batch(self.changes)
            self.changes.clear()
            return flush_debounced_changes()
        return ChangeSet()


def form_context(auto_flush: bool = True) -> FormContext:
    """Create a form context for atomic commits."""
    return FormContext(auto_flush)


# Widget wrappers with debouncing
def debounced_slider(label: str, key: str, min_value: float, max_value: float,
                    value: float = None, step: float = None, **kwargs) -> float:
    """Slider with debounced state updates."""
    # Get current value (pending or committed)
    current_value = get_pending_value(key, value or min_value)
    
    # Render slider
    adapter = get_ui_adapter()
    slider_config = ComponentConfig(
        key=f"{key}_widget",
        label=label
    )
    new_value = adapter.inputs.slider(
        slider_config, min_value=min_value, max_value=max_value,
        value=current_value, step=step, **kwargs
    )
    
    # Schedule debounced update if changed
    if new_value != current_value:
        debounce_immediate(key, new_value)
    
    return new_value


def debounced_number_input(label: str, key: str, value: float = None,
                          min_value: float = None, max_value: float = None,
                          step: float = None, **kwargs) -> float:
    """Number input with debounced state updates."""
    current_value = get_pending_value(key, value or 0.0)
    
    adapter = get_ui_adapter()
    number_config = ComponentConfig(
        key=f"{key}_widget",
        label=label
    )
    new_value = adapter.inputs.number_input(
        number_config, value=current_value, min_value=min_value,
        max_value=max_value, step=step, **kwargs
    )
    
    if new_value != current_value:
        debounce_form_input(key, new_value)
    
    return new_value


def debounced_selectbox(label: str, key: str, options: list, index: int = 0,
                       **kwargs) -> Any:
    """Selectbox with debounced state updates."""
    current_value = get_pending_value(key, options[index] if options else None)
    
    try:
        current_index = options.index(current_value) if current_value in options else index
    except (ValueError, TypeError):
        current_index = index
    
    adapter = get_ui_adapter()
    selectbox_config = ComponentConfig(
        key=f"{key}_widget",
        label=label
    )
    new_value = adapter.inputs.selectbox(
        selectbox_config, options=options, index=current_index, **kwargs
    )
    
    if new_value != current_value:
        debounce_immediate(key, new_value)
    
    return new_value
