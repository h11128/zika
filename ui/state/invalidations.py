"""
Cache invalidation logic.

Handles cache invalidation based on state changes.
"""

import time
from typing import List, Set, Dict, Any, Callable
from dataclasses import dataclass, field

from .ports import InvalidationPort, StateChange, StateChangeType


@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    key_pattern: str  # State key pattern that triggers invalidation
    cache_keys: List[str]  # Cache keys to invalidate
    reason: str  # Reason for invalidation


@dataclass
class InvalidationEvent:
    """Record of a cache invalidation."""
    reason: str
    affected_keys: List[str]
    timestamp: float = field(default_factory=time.time)
    triggered_by: str = ""  # State key that triggered it


class InvalidationService(InvalidationPort):
    """Cache invalidation service implementation."""
    
    def __init__(self):
        self._rules: List[InvalidationRule] = []
        self._history: List[InvalidationEvent] = []
        self._max_history = 50
        self._invalidation_callbacks: Dict[str, Callable[[InvalidationEvent], None]] = {}
        self._setup_default_rules()
    
    def invalidate(self, reason: str, affected_keys: List[str] = None) -> None:
        """Invalidate caches."""
        if affected_keys is None:
            affected_keys = ["*"]  # Invalidate all
        
        event = InvalidationEvent(
            reason=reason,
            affected_keys=affected_keys
        )
        
        self._record_invalidation(event)
        self._execute_invalidation(event)
    
    def should_invalidate(self, change: StateChange) -> bool:
        """Check if change should trigger invalidation."""
        for rule in self._rules:
            if self._key_matches_pattern(change.key, rule.key_pattern):
                return True
        return False
    
    def invalidate_for_change(self, change: StateChange) -> None:
        """Invalidate caches based on state change."""
        for rule in self._rules:
            if self._key_matches_pattern(change.key, rule.key_pattern):
                event = InvalidationEvent(
                    reason=rule.reason,
                    affected_keys=rule.cache_keys,
                    triggered_by=change.key
                )
                
                self._record_invalidation(event)
                self._execute_invalidation(event)
    
    def add_rule(self, key_pattern: str, cache_keys: List[str], reason: str) -> None:
        """Add invalidation rule."""
        rule = InvalidationRule(
            key_pattern=key_pattern,
            cache_keys=cache_keys,
            reason=reason
        )
        self._rules.append(rule)
    
    def remove_rules(self, key_pattern: str) -> None:
        """Remove invalidation rules for key pattern."""
        self._rules = [rule for rule in self._rules if rule.key_pattern != key_pattern]
    
    def register_callback(self, cache_key: str, callback: Callable[[InvalidationEvent], None]) -> None:
        """Register callback for cache invalidation."""
        self._invalidation_callbacks[cache_key] = callback
    
    def unregister_callback(self, cache_key: str) -> None:
        """Unregister invalidation callback."""
        self._invalidation_callbacks.pop(cache_key, None)
    
    def get_invalidation_history(self) -> List[InvalidationEvent]:
        """Get invalidation history."""
        return self._history.copy()
    
    def clear_history(self) -> None:
        """Clear invalidation history."""
        self._history.clear()
    
    def _setup_default_rules(self) -> None:
        """Setup default invalidation rules."""
        # Preview cache invalidation
        preview_keys = ["preview_cache", "preview_html", "preview_params"]
        
        self.add_rule("card_size", preview_keys, "Card size changed")
        self.add_rule("gap_cm", preview_keys, "Gap changed")
        self.add_rule("margin_cm", preview_keys, "Margin changed")
        self.add_rule("font_*", preview_keys, "Font settings changed")
        self.add_rule("page_size", preview_keys, "Page size changed")
        self.add_rule("hanzi_font", preview_keys, "Font family changed")
        self.add_rule("background_color", preview_keys, "Background color changed")
        self.add_rule("rows", preview_keys, "Layout rows changed")
        self.add_rule("cols", preview_keys, "Layout columns changed")
        self.add_rule("auto_fill", preview_keys, "Auto fill setting changed")
        self.add_rule("preview_mode", preview_keys, "Preview mode changed")
        self.add_rule("processed_cards", preview_keys, "Card content changed")
        
        # Export cache invalidation
        export_keys = ["export_cache", "export_data", "export_ready"]
        
        self.add_rule("card_size", export_keys, "Card size changed")
        self.add_rule("gap_cm", export_keys, "Gap changed")
        self.add_rule("margin_cm", export_keys, "Margin changed")
        self.add_rule("font_*", export_keys, "Font settings changed")
        self.add_rule("page_size", export_keys, "Page size changed")
        self.add_rule("hanzi_font", export_keys, "Font family changed")
        self.add_rule("background_color", export_keys, "Background color changed")
        self.add_rule("rows", export_keys, "Layout rows changed")
        self.add_rule("cols", export_keys, "Layout columns changed")
        self.add_rule("auto_fill", export_keys, "Auto fill setting changed")
        self.add_rule("processed_cards", export_keys, "Card content changed")
    
    def _key_matches_pattern(self, key: str, pattern: str) -> bool:
        """Check if key matches pattern."""
        if pattern == "*":
            return True
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            return key.startswith(prefix)
        elif pattern.startswith("*"):
            suffix = pattern[1:]
            return key.endswith(suffix)
        else:
            return key == pattern
    
    def _record_invalidation(self, event: InvalidationEvent) -> None:
        """Record invalidation event."""
        self._history.append(event)
        
        # Trim history if too long
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def _execute_invalidation(self, event: InvalidationEvent) -> None:
        """Execute cache invalidation."""
        for cache_key in event.affected_keys:
            # Call registered callbacks
            if cache_key in self._invalidation_callbacks:
                try:
                    self._invalidation_callbacks[cache_key](event)
                except Exception as e:
                    print(f"Error in invalidation callback for {cache_key}: {e}")
            
            # Global invalidation for "*"
            if cache_key == "*" and "*" in self._invalidation_callbacks:
                try:
                    self._invalidation_callbacks["*"](event)
                except Exception as e:
                    print(f"Error in global invalidation callback: {e}")


# Global invalidation service
_invalidation_service: InvalidationService = None


def get_invalidation_service() -> InvalidationService:
    """Get the global invalidation service."""
    global _invalidation_service
    
    if _invalidation_service is None:
        _invalidation_service = InvalidationService()
    
    return _invalidation_service


def invalidate_preview_cache(reason: str) -> None:
    """Invalidate preview cache."""
    service = get_invalidation_service()
    service.invalidate(reason, ["preview_cache", "preview_html", "preview_params"])


def invalidate_export_cache(reason: str) -> None:
    """Invalidate export cache."""
    service = get_invalidation_service()
    service.invalidate(reason, ["export_cache", "export_data", "export_ready"])
