"""
UI State Service - Centralized state management for the UI refactor.
Single write barrier with rules, batching, digests, invalidation, and persistence.
"""

import json
import hashlib
import uuid
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
import streamlit as st

from core.feature_flags import use_state_service


@dataclass
class ChangeSet:
    """Represents the impact of state changes across domains."""
    affects_processing: bool = False
    affects_layout: bool = False
    affects_style: bool = False
    affects_navigation: bool = False
    affects_export: bool = False
    nav_reset_required: bool = False


@dataclass
class SessionGeneration:
    """Session generation tracking for cache isolation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.utcnow)


# Global session generation (persists across reruns within same browser session)
_session_generation: Optional[SessionGeneration] = None


def get_session_generation() -> str:
    """Get current session generation ID."""
    global _session_generation
    if _session_generation is None:
        _session_generation = SessionGeneration()
    return _session_generation.id


def reset_session_generation() -> str:
    """Reset session generation (for new sessions)."""
    global _session_generation
    _session_generation = SessionGeneration()
    return _session_generation.id


class StateService:
    """Centralized state management service."""
    
    def __init__(self):
        self.pending_changes: Dict[str, Any] = {}
        self.last_digests: Dict[str, str] = {}
        
    def set_option(self, key: str, value: Any) -> bool:
        """
        Set a single option. Returns True if value changed.
        Accumulates changes for batch processing.
        """
        if not use_state_service():
            # Fallback to direct session state
            current = getattr(st.session_state, key, None)
            if current != value:
                setattr(st.session_state, key, value)
                return True
            return False
        
        # Get current value
        current = self._get_current_value(key)
        if current == value:
            return False
        
        # Store in pending changes
        self.pending_changes[key] = value
        return True
    
    def set_options_batch(self, changes: Dict[str, Any]) -> ChangeSet:
        """
        Apply multiple changes atomically with rule engine normalization.
        Returns ChangeSet indicating which domains were affected.
        """
        if not use_state_service():
            # Fallback to direct session state updates
            changeset = ChangeSet()
            for key, value in changes.items():
                if self.set_option(key, value):
                    # Simple heuristic for fallback mode
                    if key in ['rows', 'cols', 'card_size', 'gap_cm', 'margin_cm', 'auto_fill']:
                        changeset.affects_layout = True
                    elif key in ['font_hanzi', 'font_pinyin', 'font_english', 'hanzi_font', 'background_color']:
                        changeset.affects_style = True
                    elif key in ['current_page']:
                        changeset.affects_navigation = True
            return changeset
        
        # Merge with pending changes
        self.pending_changes.update(changes)
        
        # Apply rule engine normalization
        normalized_changes = self._apply_rule_engine(self.pending_changes.copy())
        
        # Compute change set
        changeset = self._compute_changeset(normalized_changes)
        
        # Apply changes to session state
        for key, value in normalized_changes.items():
            setattr(st.session_state, key, value)
        
        # Clear pending changes
        self.pending_changes.clear()
        
        # Handle navigation reset if required
        if changeset.nav_reset_required:
            self._reset_navigation()
        
        return changeset
    
    def invalidate_preview_cache(self, reason: str = "") -> None:
        """Invalidate preview cache and export buffers."""
        # Clear preview-related session state
        if hasattr(st.session_state, 'export_ready'):
            st.session_state.export_ready = {}
        if hasattr(st.session_state, 'export_data'):
            st.session_state.export_data = {}

        # Clear last params for legacy compatibility
        if hasattr(st.session_state, 'last_params'):
            st.session_state.last_params = {}
        if hasattr(st.session_state, 'last_preview_params'):
            del st.session_state.last_preview_params

        # Clear services cache (current implementation)
        try:
            from services.cache import clear_preview_cache
            clear_preview_cache()
        except ImportError:
            pass

        # Clear cache_v2 when available (P2 implementation)
        try:
            from core.feature_flags import use_cache_v2
            if use_cache_v2():
                from services.cache_v2 import clear_preview_cache_v2
                clear_preview_cache_v2()
        except ImportError:
            pass

        # Log invalidation for debugging
        try:
            import logging
            logger = logging.getLogger('ui.state')
            logger.debug(f"Preview cache invalidated: {reason}, session: {get_session_generation()}")
        except Exception:
            pass
        
    def _get_current_value(self, key: str) -> Any:
        """Get current value from session state or pending changes."""
        if key in self.pending_changes:
            return self.pending_changes[key]
        return getattr(st.session_state, key, None)
    
    def _apply_rule_engine(self, changes: Dict[str, Any]) -> Dict[str, Any]:
        """Apply rule engine to normalize and constrain changes."""
        normalized = changes.copy()
        
        # Rule 1: Manual card_size adjustment → auto_fill=False
        if 'card_size' in changes and 'auto_fill' not in changes:
            current_auto_fill = self._get_current_value('auto_fill')
            if current_auto_fill:
                normalized['auto_fill'] = False
        
        # Rule 2: auto_fill=True → recompute card_size
        if changes.get('auto_fill') is True:
            card_size = self._compute_auto_card_size(normalized)
            if card_size is not None:
                normalized['card_size'] = card_size

        # Rule 3: Page size/layout changes with auto_fill=True → recompute card_size
        layout_keys = {'rows', 'cols', 'page_size', 'gap_cm', 'margin_cm'}
        if any(key in changes for key in layout_keys):
            auto_fill = normalized.get('auto_fill', self._get_current_value('auto_fill'))
            if auto_fill:
                card_size = self._compute_auto_card_size(normalized)
                if card_size is not None:
                    normalized['card_size'] = card_size

        return normalized

    def _compute_auto_card_size(self, changes: Dict[str, Any] = None) -> Optional[float]:
        """Compute automatic card size based on layout parameters."""
        try:
            # Get current or changed values
            def get_value(key: str, default: Any) -> Any:
                if changes and key in changes:
                    return changes[key]
                return self._get_current_value(key) or default

            rows = get_value('rows', 2)
            cols = get_value('cols', 3)
            gap_cm = get_value('gap_cm', 0.5)
            margin_cm = get_value('margin_cm', 1.0)
            page_size = get_value('page_size', 'A4')

            # Import layout computation (will be moved to services/layout.py in P6)
            from services.layout import compute_auto_card_size_cm
            return compute_auto_card_size_cm(page_size, margin_cm, gap_cm, rows, cols)
        except ImportError:
            # Fallback calculation if services/layout not available yet
            return self._fallback_compute_card_size(
                get_value('rows', 2), get_value('cols', 3),
                get_value('gap_cm', 0.5), get_value('margin_cm', 1.0),
                get_value('page_size', 'A4')
            )
        except Exception:
            # Return None if computation fails
            return None

    def _fallback_compute_card_size(self, rows: int, cols: int, gap_cm: float,
                                   margin_cm: float, page_size: str) -> float:
        """Fallback card size computation."""
        # Simple A4 calculation (21cm x 29.7cm)
        if page_size == 'A4':
            usable_width = 21.0 - (2 * margin_cm) - ((cols - 1) * gap_cm)
            usable_height = 29.7 - (2 * margin_cm) - ((rows - 1) * gap_cm)
        else:
            # Default to A4 if unknown page size
            usable_width = 21.0 - (2 * margin_cm) - ((cols - 1) * gap_cm)
            usable_height = 29.7 - (2 * margin_cm) - ((rows - 1) * gap_cm)

        card_width = usable_width / cols
        card_height = usable_height / rows

        # Return the smaller dimension to ensure cards fit
        return min(card_width, card_height)
    
    def _compute_changeset(self, changes: Dict[str, Any]) -> ChangeSet:
        """Compute which domains are affected by the changes."""
        changeset = ChangeSet()
        
        # Processing domain
        processing_keys = {'input_text', 'auto_pinyin', 'auto_translate', 'translate_order'}
        if any(key in changes for key in processing_keys):
            changeset.affects_processing = True
        
        # Layout domain
        layout_keys = {'rows', 'cols', 'gap_cm', 'margin_cm', 'page_size', 'auto_fill', 'card_size'}
        if any(key in changes for key in layout_keys):
            changeset.affects_layout = True
            # Check if navigation reset is required
            if 'rows' in changes or 'cols' in changes:
                changeset.nav_reset_required = True
        
        # Style domain
        style_keys = {'font_hanzi', 'font_pinyin', 'font_english', 'hanzi_font', 'background_color'}
        if any(key in changes for key in style_keys):
            changeset.affects_style = True
        
        # Navigation domain
        if 'current_page' in changes:
            changeset.affects_navigation = True
        
        # Export is affected by processing, layout, or style changes
        if changeset.affects_processing or changeset.affects_layout or changeset.affects_style:
            changeset.affects_export = True
        
        return changeset
    
    def _reset_navigation(self) -> None:
        """Reset navigation to page 0."""
        st.session_state.current_page = 0


# Global state service instance
_state_service: Optional[StateService] = None


def get_state_service() -> StateService:
    """Get the global state service instance."""
    global _state_service
    if _state_service is None:
        _state_service = StateService()
    return _state_service


# Digest computation functions
def normalize_for_digest(obj: Any) -> Any:
    """Normalize object for stable digest computation."""
    if isinstance(obj, dict):
        # Sort keys and recursively normalize values
        return {k: normalize_for_digest(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, list):
        return [normalize_for_digest(item) for item in obj]
    elif isinstance(obj, set):
        return sorted([normalize_for_digest(item) for item in obj])
    elif isinstance(obj, float):
        # Round to 4 decimal places for stability
        return round(obj, 4)
    elif hasattr(obj, '__dict__'):
        # Handle dataclasses and objects
        return normalize_for_digest(obj.__dict__)
    else:
        return obj


def stable_digest(obj: Any) -> str:
    """Compute stable SHA256 digest of an object."""
    normalized = normalize_for_digest(obj)
    json_str = json.dumps(normalized, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()[:16]  # Use first 16 chars


def compute_processing_digest() -> str:
    """Compute digest for processing domain."""
    processing_data = {
        'input_text': getattr(st.session_state, 'input_text', ''),
        'auto_pinyin': getattr(st.session_state, 'auto_pinyin', False),
        'auto_translate': getattr(st.session_state, 'auto_translate', False),
        'translate_order': getattr(st.session_state, 'translate_order', 'pinyin_first'),
    }
    return stable_digest(processing_data)


def compute_layout_digest() -> str:
    """Compute digest for layout domain."""
    # Support both old and new field names for backward compatibility
    gap_cm = getattr(st.session_state, 'gap_cm', None)
    if gap_cm is None:
        gap_cm = getattr(st.session_state, 'gap', 0.5)

    margin_cm = getattr(st.session_state, 'margin_cm', None)
    if margin_cm is None:
        margin_cm = getattr(st.session_state, 'margin', 1.0)

    layout_data = {
        'rows': getattr(st.session_state, 'rows', 2),
        'cols': getattr(st.session_state, 'cols', 3),
        'gap_cm': gap_cm,
        'margin_cm': margin_cm,
        'page_size': getattr(st.session_state, 'page_size', 'A4'),
        'auto_fill': getattr(st.session_state, 'auto_fill', True),
        'card_size': getattr(st.session_state, 'card_size', 5.5),
    }
    return stable_digest(layout_data)


def compute_style_digest() -> str:
    """Compute digest for style domain."""
    style_data = {
        'font_hanzi': getattr(st.session_state, 'font_hanzi', 48),
        'font_pinyin': getattr(st.session_state, 'font_pinyin', 18),
        'font_english': getattr(st.session_state, 'font_english', 14),
        'hanzi_font': getattr(st.session_state, 'hanzi_font', 'SimHei'),
        'background_color': getattr(st.session_state, 'background_color', '#ffffff'),
    }
    return stable_digest(style_data)


def compute_preview_params_digest(cards_count: int) -> str:
    """Compute digest for preview parameters."""
    # Schema version for cache invalidation
    PREVIEW_CACHE_SCHEMA_VERSION = "v1.0.0"
    
    preview_data = {
        'layout_digest': compute_layout_digest(),
        'style_digest': compute_style_digest(),
        'preview_mode': getattr(st.session_state, 'preview_mode', '📄 完整页面'),
        'cards_count': cards_count,
        'schema_version': PREVIEW_CACHE_SCHEMA_VERSION,
        'session_generation': get_session_generation(),
    }
    return stable_digest(preview_data)


def compute_export_key(export_params: Dict[str, Any], cards_count: int, content_version_signal: str = None) -> str:
    """Compute stable export cache key."""
    # Schema version for cache invalidation
    EXPORT_SCHEMA_VERSION = "v1.0.0"
    
    export_data = {
        'params': normalize_for_digest(export_params),
        'cards_count': cards_count,
        'schema_version': EXPORT_SCHEMA_VERSION,
        'session_generation': get_session_generation(),
    }
    
    # Include content version signal if provided (for P5 implementation)
    if content_version_signal:
        export_data['content_version_signal'] = content_version_signal
    
    return stable_digest(export_data)

# Convenience functions for state access
def set_option(key: str, value: Any) -> bool:
    """Set a single option through the state service."""
    return get_state_service().set_option(key, value)


def set_options_batch(changes: Dict[str, Any]) -> ChangeSet:
    """Set multiple options through the state service."""
    return get_state_service().set_options_batch(changes)


def invalidate_preview_cache(reason: str = "") -> None:
    """Invalidate preview cache through the state service."""
    get_state_service().invalidate_preview_cache(reason)
