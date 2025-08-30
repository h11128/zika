"""
State bridge module for unified state access.

Provides a unified interface for accessing session state that works
with both adapters and legacy Streamlit code.
"""

from typing import Any, Dict, Optional
from core.feature_flags import get_feature_flag


class StateBridge:
    """Unified state access bridge."""
    
    def __init__(self):
        self._use_state_service = get_feature_flag('state_service', False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state."""
        if self._use_state_service:
            try:
                from ui.state import get_state_service
                service = get_state_service()
                return service.get(key, default)
            except Exception:
                pass
        
        # Fallback to session state
        import streamlit as st
        return st.session_state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in state."""
        if self._use_state_service:
            try:
                from ui.state import get_state_service
                service = get_state_service()
                service.set(key, value)
                return
            except Exception:
                pass
        
        # Fallback to session state
        import streamlit as st
        st.session_state[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple values in state."""
        if self._use_state_service:
            try:
                from ui.state import get_state_service
                service = get_state_service()
                service.update(updates)
                return
            except Exception:
                pass
        
        # Fallback to session state
        import streamlit as st
        for key, value in updates.items():
            st.session_state[key] = value
    
    def delete(self, key: str) -> None:
        """Delete a value from state."""
        if self._use_state_service:
            try:
                from ui.state import get_state_service
                service = get_state_service()
                service.delete(key)
                return
            except Exception:
                pass
        
        # Fallback to session state
        import streamlit as st
        if key in st.session_state:
            del st.session_state[key]
    
    def has(self, key: str) -> bool:
        """Check if a key exists in state."""
        if self._use_state_service:
            try:
                from ui.state import get_state_service
                service = get_state_service()
                return service.get(key) is not None
            except Exception:
                pass
        
        # Fallback to session state
        import streamlit as st
        return key in st.session_state
    
    def append_to_list(self, key: str, value: Any) -> None:
        """Append a value to a list in state."""
        current_list = self.get(key, [])
        if not isinstance(current_list, list):
            current_list = []
        current_list.append(value)
        self.set(key, current_list)
    
    def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value in state."""
        current_value = self.get(key, 0)
        new_value = current_value + amount
        self.set(key, new_value)
        return new_value
    
    @property
    def raw_session_state(self):
        """Get raw session state for compatibility."""
        import streamlit as st
        return st.session_state


# Global state bridge instance
_state_bridge = None


def get_state_bridge() -> StateBridge:
    """Get the global state bridge instance."""
    global _state_bridge
    if _state_bridge is None:
        _state_bridge = StateBridge()
    return _state_bridge


# Convenience functions
def state_get(key: str, default: Any = None) -> Any:
    """Get a value from state."""
    return get_state_bridge().get(key, default)


def state_set(key: str, value: Any) -> None:
    """Set a value in state."""
    get_state_bridge().set(key, value)


def state_update(updates: Dict[str, Any]) -> None:
    """Update multiple values in state."""
    get_state_bridge().update(updates)


def state_delete(key: str) -> None:
    """Delete a value from state."""
    get_state_bridge().delete(key)


def state_has(key: str) -> bool:
    """Check if a key exists in state."""
    return get_state_bridge().has(key)


def state_append(key: str, value: Any) -> None:
    """Append a value to a list in state."""
    get_state_bridge().append_to_list(key, value)


def state_increment(key: str, amount: int = 1) -> int:
    """Increment a numeric value in state."""
    return get_state_bridge().increment(key, amount)


# Export the main functions
__all__ = [
    'StateBridge',
    'get_state_bridge',
    'state_get',
    'state_set', 
    'state_update',
    'state_delete',
    'state_has',
    'state_append',
    'state_increment'
]
