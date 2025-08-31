"""
UI State Service - Centralized state management for the UI refactor.
Single write barrier with rules, batching, digests, invalidation, and persistence.
"""

import json
import hashlib
import uuid
import logging
from typing import Dict, Any, List, Optional, Set, Union
from dataclasses import dataclass, field
from datetime import datetime
import streamlit as st

# State service is now always enabled - no feature flag needed
from core.version import get_code_version
from core.field_migration import resolve_field_value

# Initialize logger
logger = logging.getLogger(__name__)


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
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    rerun_count: int = 0
    is_new_session: bool = True


def get_session_generation() -> str:
    """
    Get current session generation ID with proper lifecycle management.

    Session generation lifecycle:
    - Create: Generated on first access in a new session
    - Persist: Maintained across reruns within the same browser session
    - Reset: On page reload or new session start

    Returns:
        Session generation ID string
    """
    # Use Streamlit session state to persist across reruns
    if 'session_generation_data' not in st.session_state:
        # New session - create session generation
        session_gen = SessionGeneration()
        st.session_state.session_generation_data = {
            'id': session_gen.id,
            'created_at': session_gen.created_at.isoformat(),
            'last_accessed': session_gen.last_accessed.isoformat(),
            'rerun_count': 0,
            'is_new_session': True
        }
        logger.info(f"Created new session generation: {session_gen.id}")
    else:
        # Existing session - update access time and rerun count
        session_data = st.session_state.session_generation_data
        session_data['last_accessed'] = datetime.utcnow().isoformat()
        session_data['rerun_count'] += 1
        session_data['is_new_session'] = False

        # Log session activity (debug level to avoid spam)
        logger.debug(f"Session generation accessed: {session_data['id']}, rerun #{session_data['rerun_count']}")

    return st.session_state.session_generation_data['id']


def reset_session_generation() -> str:
    """
    Reset session generation (for new sessions or explicit reset).

    Returns:
        New session generation ID
    """
    session_gen = SessionGeneration()
    st.session_state.session_generation_data = {
        'id': session_gen.id,
        'created_at': session_gen.created_at.isoformat(),
        'last_accessed': session_gen.last_accessed.isoformat(),
        'rerun_count': 0,
        'is_new_session': True
    }

    logger.info(f"Reset session generation: {session_gen.id}")
    return session_gen.id


def get_session_generation_info() -> Dict[str, Any]:
    """
    Get detailed session generation information for debugging.

    Returns:
        Dictionary with session generation details
    """
    if 'session_generation_data' not in st.session_state:
        # Initialize if not exists
        get_session_generation()

    session_data = st.session_state.session_generation_data.copy()

    # Add computed fields
    created_at = datetime.fromisoformat(session_data['created_at'])
    last_accessed = datetime.fromisoformat(session_data['last_accessed'])
    session_data['session_duration_seconds'] = (last_accessed - created_at).total_seconds()
    session_data['is_active'] = (datetime.utcnow() - last_accessed).total_seconds() < 300  # 5 minutes

    return session_data


def validate_session_generation_lifecycle() -> Dict[str, Any]:
    """
    Validate session generation lifecycle and return status.

    Returns:
        Dictionary with validation results
    """
    validation_result = {
        'is_valid': True,
        'errors': [],
        'warnings': [],
        'session_info': {}
    }

    try:
        # Check if session generation exists
        if 'session_generation_data' not in st.session_state:
            validation_result['warnings'].append("No session generation found, will be created on next access")
            return validation_result

        session_data = st.session_state.session_generation_data
        validation_result['session_info'] = session_data.copy()

        # Validate session ID format
        session_id = session_data.get('id', '')
        if not session_id or len(session_id) < 10:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Invalid session ID format: {session_id}")

        # Validate timestamps
        try:
            created_at = datetime.fromisoformat(session_data['created_at'])
            last_accessed = datetime.fromisoformat(session_data['last_accessed'])

            if last_accessed < created_at:
                validation_result['is_valid'] = False
                validation_result['errors'].append("Last accessed time is before created time")

            # Check for reasonable session duration (not more than 24 hours)
            duration = (datetime.utcnow() - created_at).total_seconds()
            if duration > 86400:  # 24 hours
                validation_result['warnings'].append(f"Session duration is very long: {duration/3600:.1f} hours")

        except ValueError as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Invalid timestamp format: {e}")

        # Validate rerun count
        rerun_count = session_data.get('rerun_count', 0)
        if rerun_count < 0:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Invalid rerun count: {rerun_count}")
        elif rerun_count > 10000:
            validation_result['warnings'].append(f"Very high rerun count: {rerun_count}")

    except Exception as e:
        validation_result['is_valid'] = False
        validation_result['errors'].append(f"Validation error: {e}")

    return validation_result


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
        # State service is always enabled
        
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
        # State service is always enabled
        
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
        """Invalidate preview cache through centralized cache manager."""
        try:
            from ui.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            cache_manager.invalidate_preview_cache(
                reason=reason or "State service invalidation",
                triggered_by=f"session_{get_session_generation()}"
            )
        except ImportError:
            # Fallback to legacy implementation
            self._legacy_invalidate_preview_cache(reason)

    def _legacy_invalidate_preview_cache(self, reason: str = "") -> None:
        """Legacy preview cache invalidation (fallback)."""
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
            from services.cache_v2 import clear_preview_cache
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
        
        # Rule 1: Manual card_size adjustment → layout_auto_fill=False
        if 'card_size_cm' in changes and 'layout_auto_fill' not in changes:
            current_auto_fill = self._get_current_value('layout_auto_fill')
            if current_auto_fill:
                normalized['layout_auto_fill'] = False
        
        # Rule 2: layout_auto_fill=True → recompute card_size
        if changes.get('layout_auto_fill') is True:
            card_size_cm = self._compute_auto_card_size(normalized)
            if card_size is not None:
                normalized['card_size_cm'] = card_size

        # Rule 3: Page size/layout changes with layout_auto_fill=True → recompute card_size
        layout_keys = {'layout_rows', 'layout_cols', 'page_size', 'gap_cm', 'margin_cm'}
        if any(key in changes for key in layout_keys):
            layout_auto_fill = normalized.get('layout_auto_fill', self._get_current_value('layout_auto_fill'))
            if layout_auto_fill:
                card_size_cm = self._compute_auto_card_size(normalized)
                if card_size is not None:
                    normalized['card_size_cm'] = card_size

        return normalized

    def _compute_auto_card_size(self, changes: Dict[str, Any] = None) -> Optional[float]:
        """Compute automatic card size based on layout parameters."""
        try:
            # Get current or changed values
            def get_value(key: str, default: Any) -> Any:
                if changes and key in changes:
                    return changes[key]
                return self._get_current_value(key) or default

            layout_rows = get_value('layout_rows', 2)
            layout_cols = get_value('layout_cols', 3)
            gap_cm = get_value('gap_cm', 0.5)
            margin_cm = get_value('margin_cm', 1.0)
            page_size = get_value('page_size', 'A4')

            # Import layout computation (will be moved to services/layout.py in P6)
            from services.layout import compute_auto_card_size_cm
            return compute_auto_card_size_cm(page_size, margin_cm, gap_cm, layout_rows, cols)
        except ImportError:
            # Fallback calculation if services/layout not available yet
            return self._fallback_compute_card_size(
                get_value('layout_rows', 2), get_value('layout_cols', 3),
                get_value('gap_cm', 0.5), get_value('margin_cm', 1.0),
                get_value('page_size', 'A4')
            )
        except Exception:
            # Return None if computation fails
            return None

    def _fallback_compute_card_size(self, layout_rows: int, layout_cols: int, gap_cm: float,
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
            # Processing changes affect cards count, so navigation reset may be required
            changeset.nav_reset_required = True

        # Layout domain
        layout_keys = {'layout_rows', 'layout_cols', 'gap_cm', 'margin_cm', 'page_size', 'layout_auto_fill', 'card_size_cm'}
        if any(key in changes for key in layout_keys):
            changeset.affects_layout = True
            # Check if navigation reset is required (only for cards_per_page affecting changes)
            if 'layout_rows' in changes or 'layout_cols' in changes:
                changeset.nav_reset_required = True

        # Style domain (does NOT require navigation reset)
        style_keys = {'hanzi_font_size', 'pinyin_font_size', 'english_font_size', 'hanzi_font_family', 'background_color'}
        if any(key in changes for key in style_keys):
            changeset.affects_style = True
            # Style changes do NOT reset navigation - this is the key fix

        # Navigation domain
        if 'current_page' in changes:
            changeset.affects_navigation = True

        # Cards changes require navigation reset
        if 'cards' in changes or 'processed_cards' in changes:
            changeset.nav_reset_required = True

        # Export is affected by processing, layout, or style changes
        if changeset.affects_processing or changeset.affects_layout or changeset.affects_style:
            changeset.affects_export = True

        return changeset
    
    def _reset_navigation(self) -> None:
        """Reset navigation to page 0."""
        st.session_state.current_page = 0

    def _apply_changeset(self, changeset: ChangeSet) -> None:
        """Apply changeset effects like navigation reset."""
        if changeset.nav_reset_required:
            self._reset_navigation()


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
    # Use field migration system for backward compatibility
    session_data = {
        attr: getattr(st.session_state, attr, None)
        for attr in ['gap_cm', 'gap_cm', 'margin_cm', 'margin_cm', 'layout_rows', 'layout_cols', 'page_size', 'layout_auto_fill', 'card_size_cm']
        if hasattr(st.session_state, attr)
    }

    gap_cm = resolve_field_value(session_data, 'gap_cm', 0.5)
    margin_cm = resolve_field_value(session_data, 'margin_cm', 1.0)

    layout_data = {
        'layout_rows': getattr(st.session_state, 'layout_rows', 2),
        'layout_cols': getattr(st.session_state, 'layout_cols', 3),
        'gap_cm': gap_cm,
        'margin_cm': margin_cm,
        'page_size': getattr(st.session_state, 'page_size', 'A4'),
        'layout_auto_fill': getattr(st.session_state, 'layout_auto_fill', True),
        'card_size_cm': getattr(st.session_state, 'card_size_cm', 5.5),
    }
    return stable_digest(layout_data)


def compute_style_digest() -> str:
    """Compute digest for style domain."""
    style_data = {
        'hanzi_font_size': getattr(st.session_state, 'hanzi_font_size', 48),
        'pinyin_font_size': getattr(st.session_state, 'pinyin_font_size', 18),
        'english_font_size': getattr(st.session_state, 'english_font_size', 14),
        'hanzi_font_family': getattr(st.session_state, 'hanzi_font_family', 'SimHei'),
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


def compute_export_key(export_params: Dict[str, Any], cards_count: int,
                      content_version_signal: str = None,
                      export_schema_version: str = None,
                      preview_theme_version: str = None) -> str:
    """
    Compute stable export cache key with content version signal.

    Args:
        export_params: Export configuration parameters
        cards_count: Number of cards being exported
        content_version_signal: Content version signal (hash of (uuid, version) tuples or snapshot_last_modified)
        export_schema_version: Export schema version (defaults to current)
        preview_theme_version: Preview theme version for consistency

    Returns:
        Stable cache key string
    """
    # Schema version for cache invalidation
    EXPORT_SCHEMA_VERSION = export_schema_version or "v1.1.0"  # Updated for content versioning

    export_data = {
        'params': normalize_for_digest(export_params),
        'cards_count': cards_count,
        'schema_version': EXPORT_SCHEMA_VERSION,
        'code_version': get_code_version(),
        'session_generation': get_session_generation(),
    }

    # Include content version signal - this is critical for cache invalidation
    # when card content changes but count remains the same
    if content_version_signal:
        export_data['content_version_signal'] = content_version_signal

    # Include preview theme version for consistency between preview and export
    if preview_theme_version:
        export_data['preview_theme_version'] = preview_theme_version

    return stable_digest(export_data)


def compute_cards_content_version_signal(cards: List[Dict[str, Any]]) -> str:
    """
    Compute content version signal from cards list.

    Creates a hash of ordered (uuid, version) tuples to detect content changes
    without hashing full content. This ensures cache invalidation when card
    content changes but count remains the same.

    Args:
        cards: List of card dictionaries with 'id' and 'version' fields

    Returns:
        Content version signal string
    """
    if not cards:
        return "empty"

    # Extract (uuid, version) tuples and sort by UUID for deterministic ordering
    version_tuples = []
    for card in cards:
        card_id = card.get('id')
        version = card.get('version', 1)  # Default version for legacy cards

        # Generate UUID for legacy cards without ID
        if not card_id:
            import hashlib
            import json
            # Use content hash as stable ID for legacy cards
            content = {
                'hanzi': card.get('hanzi', ''),
                'pinyin': card.get('pinyin', ''),
                'english': card.get('english', '')
            }
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
            card_id = hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]

        version_tuples.append((card_id, version))

    # Sort by UUID for deterministic ordering
    version_tuples.sort(key=lambda x: x[0])

    # Create hash of the ordered tuples
    import json
    import hashlib
    tuples_str = json.dumps(version_tuples, sort_keys=True)
    return hashlib.sha256(tuples_str.encode('utf-8')).hexdigest()[:16]


def compute_snapshot_content_version_signal(snapshot_last_modified: str) -> str:
    """
    Compute content version signal from snapshot last modified timestamp.

    Args:
        snapshot_last_modified: ISO-8601 timestamp string

    Returns:
        Content version signal string
    """
    if not snapshot_last_modified:
        return "no_timestamp"

    import hashlib
    return hashlib.sha256(snapshot_last_modified.encode('utf-8')).hexdigest()[:16]


def get_content_version_signal(cards: List[Dict[str, Any]] = None,
                              snapshot_last_modified: str = None) -> str:
    """
    Get content version signal using the best available method.

    Priority:
    1. Cards with UUID/version if available
    2. Snapshot last modified timestamp
    3. Fallback to current timestamp

    Args:
        cards: List of card dictionaries
        snapshot_last_modified: ISO-8601 timestamp string

    Returns:
        Content version signal string
    """
    # Try cards-based version signal first (most precise)
    if cards:
        # Check if cards have proper ID/version structure
        has_proper_structure = any(
            card.get('id') and card.get('version') for card in cards
        )
        if has_proper_structure:
            return compute_cards_content_version_signal(cards)

    # Fall back to snapshot timestamp
    if snapshot_last_modified:
        return compute_snapshot_content_version_signal(snapshot_last_modified)

    # Final fallback - use current timestamp
    from datetime import datetime, timezone
    current_time = datetime.now(timezone.utc).isoformat()
    return compute_snapshot_content_version_signal(current_time)

# Convenience functions for state access
def set_option(key: str, value: Any) -> bool:
    """Set a single option through the state service."""
    return get_state_service().set_option(key, value)


def set_options_batch(changes: Dict[str, Any]) -> ChangeSet:
    """Set multiple options through the state service."""
    return get_state_service().set_options_batch(changes)


def invalidate_preview_cache(reason: str = "") -> None:
    """Invalidate preview cache through centralized cache manager."""
    try:
        from ui.cache_manager import invalidate_preview_cache as cache_invalidate
        cache_invalidate(reason, "ui.state.convenience_function")
    except ImportError:
        # Fallback to state service
        get_state_service().invalidate_preview_cache(reason)
