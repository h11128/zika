"""
Centralized Cache Management System.

This module provides a unified interface for all cache operations,
eliminating scattered cache clearing calls throughout the codebase.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time

from core.feature_flags import get_feature_flag


class CacheType(Enum):
    """Types of caches in the system."""
    PREVIEW = "preview"
    EXPORT = "export"
    STATE = "state"
    SESSION = "session"
    ALL = "all"


@dataclass
class CacheInvalidationEvent:
    """Record of a cache invalidation event."""
    cache_type: CacheType
    reason: str
    timestamp: float = field(default_factory=time.time)
    triggered_by: str = ""
    affected_keys: List[str] = field(default_factory=list)


class CacheManager:
    """Centralized cache management system."""
    
    def __init__(self):
        self._invalidation_history: List[CacheInvalidationEvent] = []
        self._max_history = 100
        self._cache_handlers: Dict[CacheType, List[Callable[[], None]]] = {
            CacheType.PREVIEW: [],
            CacheType.EXPORT: [],
            CacheType.STATE: [],
            CacheType.SESSION: [],
            CacheType.ALL: []
        }
        self._setup_default_handlers()
        
    def register_cache_handler(self, cache_type: CacheType, handler: Callable[[], None]) -> None:
        """Register a cache clearing handler for a specific cache type."""
        if cache_type not in self._cache_handlers:
            self._cache_handlers[cache_type] = []
        self._cache_handlers[cache_type].append(handler)
        
    def invalidate_cache(self, cache_type: CacheType, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate specific cache type with centralized logging."""
        event = CacheInvalidationEvent(
            cache_type=cache_type,
            reason=reason,
            triggered_by=triggered_by
        )
        
        # Execute cache clearing handlers
        handlers = self._cache_handlers.get(cache_type, [])
        for handler in handlers:
            try:
                handler()
            except Exception as e:
                logging.warning(f"Cache handler failed for {cache_type.value}: {e}")
        
        # If invalidating ALL, also run specific handlers
        if cache_type == CacheType.ALL:
            for specific_type in [CacheType.PREVIEW, CacheType.EXPORT, CacheType.STATE, CacheType.SESSION]:
                specific_handlers = self._cache_handlers.get(specific_type, [])
                for handler in specific_handlers:
                    try:
                        handler()
                    except Exception as e:
                        logging.warning(f"Cache handler failed for {specific_type.value}: {e}")
        
        # Record event
        self._record_invalidation(event)
        
        # Log for debugging
        logging.debug(f"Cache invalidated: {cache_type.value}, reason: {reason}, triggered_by: {triggered_by}")

        # Record observability metrics
        try:
            from services.observability import record_cache_miss
            record_cache_miss(cache_type.value)
        except ImportError:
            pass
    
    def invalidate_preview_cache(self, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate preview-related caches."""
        self.invalidate_cache(CacheType.PREVIEW, reason, triggered_by)
    
    def invalidate_export_cache(self, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate export-related caches."""
        self.invalidate_cache(CacheType.EXPORT, reason, triggered_by)
    
    def invalidate_state_cache(self, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate state-related caches."""
        self.invalidate_cache(CacheType.STATE, reason, triggered_by)
    
    def invalidate_session_cache(self, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate session-related caches."""
        self.invalidate_cache(CacheType.SESSION, reason, triggered_by)
    
    def invalidate_all_caches(self, reason: str = "", triggered_by: str = "") -> None:
        """Invalidate all caches."""
        self.invalidate_cache(CacheType.ALL, reason, triggered_by)
    
    def get_invalidation_history(self, limit: int = 20) -> List[CacheInvalidationEvent]:
        """Get recent cache invalidation history."""
        return self._invalidation_history[-limit:]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            'total_invalidations': len(self._invalidation_history),
            'recent_invalidations': len([e for e in self._invalidation_history 
                                       if time.time() - e.timestamp < 300]),  # Last 5 minutes
            'handlers_registered': {
                cache_type.value: len(handlers) 
                for cache_type, handlers in self._cache_handlers.items()
            }
        }
        
        # Add cache-specific stats if available
        try:
            if get_feature_flag('cache_v2', False):
                from services.cache_v2 import get_cache_stats
                stats['cache_v2'] = get_cache_stats()
        except ImportError:
            pass
        
        return stats
    
    def _setup_default_handlers(self) -> None:
        """Setup default cache clearing handlers."""
        # Preview cache handlers
        self.register_cache_handler(CacheType.PREVIEW, self._clear_legacy_preview_cache)
        self.register_cache_handler(CacheType.PREVIEW, self._clear_v2_preview_cache)
        self.register_cache_handler(CacheType.PREVIEW, self._clear_session_preview_data)
        
        # Export cache handlers
        self.register_cache_handler(CacheType.EXPORT, self._clear_v2_export_cache)
        self.register_cache_handler(CacheType.EXPORT, self._clear_session_export_data)
        
        # State cache handlers
        self.register_cache_handler(CacheType.STATE, self._clear_state_cache)
        
        # Session cache handlers
        self.register_cache_handler(CacheType.SESSION, self._clear_session_params)
    
    def _clear_legacy_preview_cache(self) -> None:
        """Clear legacy preview cache."""
        try:
            from services.cache_v2 import clear_preview_cache
            clear_preview_cache()
        except ImportError:
            pass
    
    def _clear_v2_preview_cache(self) -> None:
        """Clear v2 preview cache."""
        try:
            if get_feature_flag('cache_v2', False):
                from services.cache_v2 import clear_preview_cache_v2
                clear_preview_cache_v2()
        except ImportError:
            pass
    
    def _clear_v2_export_cache(self) -> None:
        """Clear v2 export cache."""
        try:
            if get_feature_flag('cache_v2', False):
                from services.cache_v2 import clear_export_cache_v2
                clear_export_cache_v2()
        except ImportError:
            pass
    
    def _clear_session_preview_data(self) -> None:
        """Clear session preview data."""
        try:
            from ui.state_bridge import state_set
            state_set('export_ready', {})
            state_set('export_data', {})
            state_set('last_params', {})
        except ImportError:
            # Fallback to direct session state access
            try:
                import streamlit as st
                if hasattr(st.session_state, 'export_ready'):
                    st.session_state.export_ready = {}
                if hasattr(st.session_state, 'export_data'):
                    st.session_state.export_data = {}
                if hasattr(st.session_state, 'last_params'):
                    st.session_state.last_params = {}
            except ImportError:
                pass
    
    def _clear_session_export_data(self) -> None:
        """Clear session export data."""
        try:
            from ui.state_bridge import state_set
            state_set('export_ready', {})
            state_set('export_data', {})
        except ImportError:
            try:
                import streamlit as st
                if hasattr(st.session_state, 'export_ready'):
                    st.session_state.export_ready = {}
                if hasattr(st.session_state, 'export_data'):
                    st.session_state.export_data = {}
            except ImportError:
                pass
    
    def _clear_state_cache(self) -> None:
        """Clear state-related cache."""
        try:
            from ui.state_bridge import state_delete
            # Clear computed state caches
            state_delete('last_preview_params')
            state_delete('computed_digest')
        except ImportError:
            pass
    
    def _clear_session_params(self) -> None:
        """Clear session parameter cache."""
        try:
            from ui.state_bridge import state_set
            state_set('last_params', {})
            state_set('last_preview_params', {})
        except ImportError:
            try:
                import streamlit as st
                if hasattr(st.session_state, 'last_params'):
                    st.session_state.last_params = {}
                if hasattr(st.session_state, 'last_preview_params'):
                    del st.session_state.last_preview_params
            except ImportError:
                pass
    
    def _record_invalidation(self, event: CacheInvalidationEvent) -> None:
        """Record invalidation event in history."""
        self._invalidation_history.append(event)
        
        # Trim history if too long
        if len(self._invalidation_history) > self._max_history:
            self._invalidation_history = self._invalidation_history[-self._max_history:]


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Convenience functions for common operations
def invalidate_preview_cache(reason: str = "", triggered_by: str = "") -> None:
    """Invalidate preview cache through centralized manager."""
    get_cache_manager().invalidate_preview_cache(reason, triggered_by)


def invalidate_export_cache(reason: str = "", triggered_by: str = "") -> None:
    """Invalidate export cache through centralized manager."""
    get_cache_manager().invalidate_export_cache(reason, triggered_by)


def invalidate_all_caches(reason: str = "", triggered_by: str = "") -> None:
    """Invalidate all caches through centralized manager."""
    get_cache_manager().invalidate_all_caches(reason, triggered_by)


# Export main classes and functions
__all__ = [
    'CacheManager', 'CacheType', 'CacheInvalidationEvent',
    'get_cache_manager', 'invalidate_preview_cache', 'invalidate_export_cache', 'invalidate_all_caches'
]
