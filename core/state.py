"""
State management for the Chinese Character Learning Cards application.
Centralized session state initialization and access patterns.
"""

import re
import streamlit as st
from typing import List, Dict, Any
from src.dict_utils import create_default_dict
from core.constants import (
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR, DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL
)


def initialize_session_state() -> None:
    """Initialize all session state variables with default values."""
    # Dictionary and data
    if 'dictionary' not in st.session_state:
        st.session_state.dictionary = create_default_dict("data")
    
    # Export tracking
    if 'export_history' not in st.session_state:
        st.session_state.export_history = []
    if 'total_cards_generated' not in st.session_state:
        st.session_state.total_cards_generated = 0
    
    # Text processing
    if 'segmented_text' not in st.session_state:
        st.session_state.segmented_text = ""
    if 'use_segmented' not in st.session_state:
        st.session_state.use_segmented = False
    
    # Pagination
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'last_params' not in st.session_state:
        st.session_state.last_params = {}
    
    # Card data
    if 'processed_cards' not in st.session_state:
        st.session_state.processed_cards = []
    if 'cards_source' not in st.session_state:
        st.session_state.cards_source = ""
    
    # Export state
    if 'export_ready' not in st.session_state:
        st.session_state.export_ready = {}
    if 'export_data' not in st.session_state:
        st.session_state.export_data = {}
    
    # UI preferences
    if 'hanzi_font' not in st.session_state:
        st.session_state.hanzi_font = DEFAULT_HANZI_FONT
    if 'background_color' not in st.session_state:
        st.session_state.background_color = DEFAULT_BACKGROUND_COLOR
    
    # Validate background color
    _validate_background_color()
    
    # Layout settings
    if 'rows' not in st.session_state:
        st.session_state.rows = DEFAULT_ROWS
    if 'cols' not in st.session_state:
        st.session_state.cols = DEFAULT_COLS
    if 'auto_fill' not in st.session_state:
        st.session_state.auto_fill = DEFAULT_AUTO_FILL


def _validate_background_color() -> None:
    """Ensure background_color is a valid hex string."""
    try:
        bg = st.session_state.background_color
        if not isinstance(bg, str) or not re.fullmatch(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})", bg.strip()):
            st.session_state.background_color = DEFAULT_BACKGROUND_COLOR
    except Exception:
        st.session_state.background_color = DEFAULT_BACKGROUND_COLOR


# Internal safe getter to avoid KeyError in bare/unit test contexts
_def_sentinel = object()

def _ss_get(key: str, default=_def_sentinel):
    try:
        # getattr allows a default; SessionStateProxy raises AttributeError for missing keys
        return getattr(st.session_state, key, default)
    except Exception:
        return default

# Getter functions for clean access
def get_dictionary():
    """Get the dictionary instance."""
    val = _ss_get('dictionary', None)
    return val


def get_processed_cards() -> List[Dict[str, str]]:
    """Get the current processed cards."""
    return st.session_state.processed_cards


def get_current_page() -> int:
    """Get the current page number."""
    return st.session_state.current_page


def get_layout_settings() -> Dict[str, Any]:
    """Get current layout settings. Safe for bare/unit-test contexts (defaults)."""
    rows = _ss_get('rows', DEFAULT_ROWS)
    cols = _ss_get('cols', DEFAULT_COLS)
    auto_fill = _ss_get('auto_fill', DEFAULT_AUTO_FILL)
    return {
        'rows': rows if rows is not None else DEFAULT_ROWS,
        'cols': cols if cols is not None else DEFAULT_COLS,
        'auto_fill': bool(auto_fill) if isinstance(auto_fill, (bool, int)) else DEFAULT_AUTO_FILL,
    }


def get_ui_preferences() -> Dict[str, str]:
    """Get current UI preferences. Safe for bare/unit-test contexts (defaults)."""
    hanzi_font = _ss_get('hanzi_font', DEFAULT_HANZI_FONT)
    background_color = _ss_get('background_color', DEFAULT_BACKGROUND_COLOR)
    return {
        'hanzi_font': hanzi_font if hanzi_font else DEFAULT_HANZI_FONT,
        'background_color': background_color if background_color else DEFAULT_BACKGROUND_COLOR,
    }


def get_export_state() -> Dict[str, Any]:
    """Get current export state."""
    return {
        'ready': st.session_state.export_ready,
        'data': st.session_state.export_data,
        'history': st.session_state.export_history,
        'total_generated': st.session_state.total_cards_generated
    }


# Setter functions for clean updates
def set_processed_cards(cards: List[Dict[str, str]], source: str = "") -> None:
    """Set processed cards and update source tracking."""
    st.session_state.processed_cards = cards
    st.session_state.cards_source = source


def set_current_page(page: int) -> None:
    """Set the current page number."""
    st.session_state.current_page = max(0, page)


def clear_export_data() -> None:
    """Clear export data when parameters change."""
    st.session_state.export_ready = {}
    st.session_state.export_data = {}


def update_last_params(params: Dict[str, Any]) -> None:
    """Update the last parameters for change detection."""
    st.session_state.last_params = params


def check_params_changed(current_params: Dict[str, Any]) -> bool:
    """Check if parameters have changed since last update. Safe for missing state."""
    last = _ss_get('last_params', {})
    try:
        return last != current_params
    except Exception:
        return True


def clear_processed_cards() -> None:
    """Clear processed cards and source."""
    st.session_state.processed_cards = []
    st.session_state.cards_source = ""


def update_layout_settings(rows: int = None, cols: int = None, auto_fill: bool = None) -> None:
    """Update layout settings."""
    if rows is not None:
        st.session_state.rows = int(rows)
    if cols is not None:
        st.session_state.cols = int(cols)
    if auto_fill is not None:
        st.session_state.auto_fill = bool(auto_fill)


def update_ui_preferences(hanzi_font: str = None, background_color: str = None) -> None:
    """Update UI preferences."""
    if hanzi_font is not None:
        st.session_state.hanzi_font = hanzi_font
    if background_color is not None:
        st.session_state.background_color = background_color
        _validate_background_color()


def add_export_record(format_type: str, card_count: int) -> None:
    """Add a record to export history."""
    import time
    st.session_state.export_history.append({
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'format': format_type,
        'cards': card_count
    })
    st.session_state.total_cards_generated += card_count


def set_export_ready(format_type: str, file_content: bytes, filename: str) -> None:
    """Mark export as ready and store data."""
    st.session_state.export_data[format_type] = {
        'content': file_content,
        'filename': filename
    }
    st.session_state.export_ready[format_type] = True


def is_export_ready(format_type: str) -> bool:
    """Check if export is ready for download."""
    return format_type in st.session_state.export_ready and st.session_state.export_ready[format_type]


def get_export_data(format_type: str) -> Dict[str, Any]:
    """Get export data for a specific format."""
    return st.session_state.export_data.get(format_type, {})


# Enhanced parameter management functions
def get_all_ui_params(card_size: float, gap: float, margin: float, page_size: str,
                     font_hanzi: int, font_pinyin: int, font_english: int,
                     processed_cards: List[Dict[str, str]]) -> Dict[str, Any]:
    """Get all UI parameters for change detection in a unified way."""
    layout = get_layout_settings()
    prefs = get_ui_preferences()

    return {
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'page_size': page_size,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'hanzi_font': prefs['hanzi_font'],
        'background_color': prefs['background_color'],
        'rows': layout['rows'],
        'cols': layout['cols'],
        'auto_fill': layout['auto_fill'],
        'total_cards': len(processed_cards)
    }


def handle_param_changes(current_params: Dict[str, Any]) -> bool:
    """Handle parameter changes and return True if changes were detected."""
    if check_params_changed(current_params):
        set_current_page(0)
        update_last_params(current_params)
        clear_export_data()
        return True
    return False
