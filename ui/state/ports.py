"""
State service ports and interfaces.

Defines the contracts for state management services.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class StateChangeType(Enum):
    """Types of state changes."""
    SET = "set"
    UPDATE = "update"
    DELETE = "delete"
    BATCH = "batch"


@dataclass
class StateChange:
    """Represents a state change."""
    change_type: StateChangeType
    key: str
    old_value: Any
    new_value: Any
    timestamp: float


class StateServicePort(ABC):
    """Port for state management services."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get state value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set state value."""
        pass
    
    @abstractmethod
    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple state values."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete state value."""
        pass
    
    @abstractmethod
    def subscribe(self, key: str, callback: Callable[[StateChange], None]) -> str:
        """Subscribe to state changes."""
        pass
    
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from state changes."""
        pass


class StateValidationPort(ABC):
    """Port for state validation."""
    
    @abstractmethod
    def validate_change(self, change: StateChange) -> bool:
        """Validate a state change."""
        pass
    
    @abstractmethod
    def get_validation_errors(self, change: StateChange) -> List[str]:
        """Get validation errors for a change."""
        pass


class StateDigestPort(ABC):
    """Port for state digest computation."""
    
    @abstractmethod
    def compute_digest(self, state: Dict[str, Any]) -> str:
        """Compute state digest."""
        pass
    
    @abstractmethod
    def has_changed(self, old_digest: str, new_digest: str) -> bool:
        """Check if state has changed."""
        pass


class InvalidationPort(ABC):
    """Port for cache invalidation."""
    
    @abstractmethod
    def invalidate(self, reason: str, affected_keys: List[str] = None) -> None:
        """Invalidate caches."""
        pass
    
    @abstractmethod
    def should_invalidate(self, change: StateChange) -> bool:
        """Check if change should trigger invalidation."""
        pass


# Global state service instance
_state_service: Optional[StateServicePort] = None


def get_state_service() -> StateServicePort:
    """Get the global state service."""
    global _state_service
    
    if _state_service is None:
        from .store import StateStore
        _state_service = StateStore()
    
    return _state_service


def set_state_service(service: StateServicePort) -> None:
    """Set the global state service (for testing)."""
    global _state_service
    _state_service = service
