"""
Navigation state management.

Handles navigation state, page tracking, and routing.
"""

import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class NavigationEvent(Enum):
    """Types of navigation events."""
    PAGE_CHANGE = "page_change"
    TAB_CHANGE = "tab_change"
    MODAL_OPEN = "modal_open"
    MODAL_CLOSE = "modal_close"
    SECTION_EXPAND = "section_expand"
    SECTION_COLLAPSE = "section_collapse"


@dataclass
class NavigationRecord:
    """Record of a navigation event."""
    event_type: NavigationEvent
    from_location: str
    to_location: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class NavigationState:
    """Navigation state manager."""
    
    def __init__(self):
        self._current_page: str = "main"
        self._current_tab: Optional[str] = None
        self._current_section: Optional[str] = None
        self._modal_stack: List[str] = []
        self._expanded_sections: set = set()
        self._navigation_history: List[NavigationRecord] = []
        self._max_history = 100
        self._listeners: Dict[NavigationEvent, List[Callable]] = {}
    
    @property
    def current_page(self) -> str:
        """Get current page."""
        return self._current_page
    
    @property
    def current_tab(self) -> Optional[str]:
        """Get current tab."""
        return self._current_tab
    
    @property
    def current_section(self) -> Optional[str]:
        """Get current section."""
        return self._current_section
    
    @property
    def active_modal(self) -> Optional[str]:
        """Get active modal (top of stack)."""
        return self._modal_stack[-1] if self._modal_stack else None
    
    @property
    def expanded_sections(self) -> set:
        """Get expanded sections."""
        return self._expanded_sections.copy()
    
    def navigate_to_page(self, page: str, metadata: Dict[str, Any] = None) -> None:
        """Navigate to a page."""
        if page != self._current_page:
            record = NavigationRecord(
                event_type=NavigationEvent.PAGE_CHANGE,
                from_location=self._current_page,
                to_location=page,
                metadata=metadata or {}
            )
            
            self._current_page = page
            self._record_navigation(record)
            self._notify_listeners(NavigationEvent.PAGE_CHANGE, record)
    
    def switch_tab(self, tab: str, metadata: Dict[str, Any] = None) -> None:
        """Switch to a tab."""
        if tab != self._current_tab:
            record = NavigationRecord(
                event_type=NavigationEvent.TAB_CHANGE,
                from_location=self._current_tab or "",
                to_location=tab,
                metadata=metadata or {}
            )
            
            self._current_tab = tab
            self._record_navigation(record)
            self._notify_listeners(NavigationEvent.TAB_CHANGE, record)
    
    def open_modal(self, modal_id: str, metadata: Dict[str, Any] = None) -> None:
        """Open a modal."""
        record = NavigationRecord(
            event_type=NavigationEvent.MODAL_OPEN,
            from_location="",
            to_location=modal_id,
            metadata=metadata or {}
        )
        
        self._modal_stack.append(modal_id)
        self._record_navigation(record)
        self._notify_listeners(NavigationEvent.MODAL_OPEN, record)
    
    def close_modal(self, modal_id: str = None, metadata: Dict[str, Any] = None) -> None:
        """Close a modal."""
        if not self._modal_stack:
            return
        
        if modal_id is None:
            # Close top modal
            closed_modal = self._modal_stack.pop()
        else:
            # Close specific modal
            if modal_id in self._modal_stack:
                self._modal_stack.remove(modal_id)
                closed_modal = modal_id
            else:
                return
        
        record = NavigationRecord(
            event_type=NavigationEvent.MODAL_CLOSE,
            from_location=closed_modal,
            to_location="",
            metadata=metadata or {}
        )
        
        self._record_navigation(record)
        self._notify_listeners(NavigationEvent.MODAL_CLOSE, record)
    
    def expand_section(self, section_id: str, metadata: Dict[str, Any] = None) -> None:
        """Expand a section."""
        if section_id not in self._expanded_sections:
            record = NavigationRecord(
                event_type=NavigationEvent.SECTION_EXPAND,
                from_location="",
                to_location=section_id,
                metadata=metadata or {}
            )
            
            self._expanded_sections.add(section_id)
            self._record_navigation(record)
            self._notify_listeners(NavigationEvent.SECTION_EXPAND, record)
    
    def collapse_section(self, section_id: str, metadata: Dict[str, Any] = None) -> None:
        """Collapse a section."""
        if section_id in self._expanded_sections:
            record = NavigationRecord(
                event_type=NavigationEvent.SECTION_COLLAPSE,
                from_location=section_id,
                to_location="",
                metadata=metadata or {}
            )
            
            self._expanded_sections.remove(section_id)
            self._record_navigation(record)
            self._notify_listeners(NavigationEvent.SECTION_COLLAPSE, record)
    
    def is_section_expanded(self, section_id: str) -> bool:
        """Check if section is expanded."""
        return section_id in self._expanded_sections
    
    def add_listener(self, event_type: NavigationEvent, callback: Callable) -> None:
        """Add navigation event listener."""
        if event_type not in self._listeners:
            self._listeners[event_type] = []
        self._listeners[event_type].append(callback)
    
    def remove_listener(self, event_type: NavigationEvent, callback: Callable) -> None:
        """Remove navigation event listener."""
        if event_type in self._listeners:
            try:
                self._listeners[event_type].remove(callback)
            except ValueError:
                pass
    
    def get_navigation_history(self) -> List[NavigationRecord]:
        """Get navigation history."""
        return self._navigation_history.copy()
    
    def clear_history(self) -> None:
        """Clear navigation history."""
        self._navigation_history.clear()
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Get navigation state as dictionary."""
        return {
            'current_page': self._current_page,
            'current_tab': self._current_tab,
            'current_section': self._current_section,
            'modal_stack': self._modal_stack.copy(),
            'expanded_sections': list(self._expanded_sections)
        }
    
    def restore_from_dict(self, state_dict: Dict[str, Any]) -> None:
        """Restore navigation state from dictionary."""
        self._current_page = state_dict.get('current_page', 'main')
        self._current_tab = state_dict.get('current_tab')
        self._current_section = state_dict.get('current_section')
        self._modal_stack = state_dict.get('modal_stack', [])
        self._expanded_sections = set(state_dict.get('expanded_sections', []))
    
    def _record_navigation(self, record: NavigationRecord) -> None:
        """Record navigation event."""
        self._navigation_history.append(record)
        
        # Trim history if too long
        if len(self._navigation_history) > self._max_history:
            self._navigation_history = self._navigation_history[-self._max_history:]
    
    def _notify_listeners(self, event_type: NavigationEvent, record: NavigationRecord) -> None:
        """Notify event listeners."""
        if event_type in self._listeners:
            for callback in self._listeners[event_type]:
                try:
                    callback(record)
                except Exception as e:
                    print(f"Error in navigation listener: {e}")


# Global navigation state
_navigation_state: NavigationState = None


def get_navigation_state() -> NavigationState:
    """Get the global navigation state."""
    global _navigation_state
    
    if _navigation_state is None:
        _navigation_state = NavigationState()
    
    return _navigation_state
