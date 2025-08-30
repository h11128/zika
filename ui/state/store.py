"""
Core state storage implementation.

Provides the main state store with subscription and change tracking.
"""

import time
import uuid
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field

from .ports import StateServicePort, StateChange, StateChangeType


@dataclass
class Subscription:
    """State change subscription."""
    id: str
    key: str
    callback: Callable[[StateChange], None]
    created_at: float = field(default_factory=time.time)


class StateStore(StateServicePort):
    """Core state store implementation."""
    
    def __init__(self):
        self._state: Dict[str, Any] = {}
        self._subscriptions: Dict[str, Subscription] = {}
        self._change_history: List[StateChange] = []
        self._max_history = 100
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set state value."""
        old_value = self._state.get(key)
        self._state[key] = value
        
        # Record change
        change = StateChange(
            change_type=StateChangeType.SET,
            key=key,
            old_value=old_value,
            new_value=value,
            timestamp=time.time()
        )
        
        self._record_change(change)
        self._notify_subscribers(change)
    
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values."""
        changes = []
        
        for key, value in updates.items():
            old_value = self._state.get(key)
            self._state[key] = value
            
            change = StateChange(
                change_type=StateChangeType.UPDATE,
                key=key,
                old_value=old_value,
                new_value=value,
                timestamp=time.time()
            )
            changes.append(change)
        
        # Record all changes
        for change in changes:
            self._record_change(change)
            self._notify_subscribers(change)
    
    def delete(self, key: str) -> None:
        """Delete state value."""
        if key in self._state:
            old_value = self._state.pop(key)
            
            change = StateChange(
                change_type=StateChangeType.DELETE,
                key=key,
                old_value=old_value,
                new_value=None,
                timestamp=time.time()
            )
            
            self._record_change(change)
            self._notify_subscribers(change)
    
    def subscribe(self, key: str, callback: Callable[[StateChange], None]) -> str:
        """Subscribe to state changes."""
        subscription_id = str(uuid.uuid4())
        subscription = Subscription(
            id=subscription_id,
            key=key,
            callback=callback
        )
        
        self._subscriptions[subscription_id] = subscription
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from state changes."""
        self._subscriptions.pop(subscription_id, None)
    
    def get_all_state(self) -> Dict[str, Any]:
        """Get all state (for debugging/testing)."""
        return self._state.copy()
    
    def get_change_history(self) -> List[StateChange]:
        """Get change history."""
        return self._change_history.copy()
    
    def clear_history(self) -> None:
        """Clear change history."""
        self._change_history.clear()
    
    def _record_change(self, change: StateChange) -> None:
        """Record a state change."""
        self._change_history.append(change)
        
        # Trim history if too long
        if len(self._change_history) > self._max_history:
            self._change_history = self._change_history[-self._max_history:]
    
    def _notify_subscribers(self, change: StateChange) -> None:
        """Notify subscribers of state changes."""
        for subscription in self._subscriptions.values():
            if subscription.key == change.key or subscription.key == "*":
                try:
                    subscription.callback(change)
                except Exception as e:
                    # Log error but don't break other subscribers
                    print(f"Error in state subscription callback: {e}")


# Global store instance
_state_store: Optional[StateStore] = None


def get_state_store() -> StateStore:
    """Get the global state store."""
    global _state_store
    
    if _state_store is None:
        _state_store = StateStore()
    
    return _state_store
