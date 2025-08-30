"""
UI State management package.

This package provides modular state management with proper separation of concerns:
- store.py: Core state storage and access
- rules.py: State validation and business rules  
- digest.py: State change detection and hashing
- invalidations.py: Cache invalidation logic
- nav.py: Navigation state management
- ports.py: State service interfaces
"""

from .store import StateStore, get_state_store
from .rules import StateRules, validate_state_change
from .digest import StateDigest, compute_state_digest
from .invalidations import InvalidationService, invalidate_preview_cache
from .nav import NavigationState, get_navigation_state
from .ports import StateServicePort, get_state_service

__all__ = [
    'StateStore', 'get_state_store',
    'StateRules', 'validate_state_change',
    'StateDigest', 'compute_state_digest',
    'InvalidationService', 'invalidate_preview_cache',
    'NavigationState', 'get_navigation_state',
    'StateServicePort', 'get_state_service'
]
