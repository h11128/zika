"""
Debug panel and logging for digest computation.
Development-only tooling to aid cache miss diagnosis.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime

import streamlit as st

from core.feature_flags import get_feature_flag
from ui.ports import get_ui_adapter, ComponentConfig
from ui.error_boundaries import with_error_boundary
from core.version import get_code_version
# Import from the main ui.state module (not the package)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("ui_state_module", os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "state.py"))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)


logger = logging.getLogger(__name__)


@dataclass
class DigestDebugInfo:
    """Debug information for a digest computation."""
    domain: str
    raw_inputs: Dict[str, Any]
    normalized_inputs: Dict[str, Any]
    digest: str
    timestamp: str
    session_generation: str
    code_version: str


class DigestDebugCollector:
    """Collects digest debug information for development."""
    
    def __init__(self):
        self._debug_entries: List[DigestDebugInfo] = []
        self._max_entries = 50  # Keep last 50 entries
    
    def record_digest(self, domain: str, raw_inputs: Dict[str, Any], digest: str) -> None:
        """Record a digest computation for debugging."""
        if not self._is_debug_enabled():
            return
        
        try:
            normalized_inputs = ui_state_module.normalize_for_digest(raw_inputs)
            
            debug_info = DigestDebugInfo(
                domain=domain,
                raw_inputs=raw_inputs.copy(),
                normalized_inputs=normalized_inputs,
                digest=digest,
                timestamp=datetime.now().isoformat(),
                session_generation=ui_state_module.get_session_generation(),
                code_version=get_code_version()
            )
            
            self._debug_entries.append(debug_info)
            
            # Keep only the last N entries
            if len(self._debug_entries) > self._max_entries:
                self._debug_entries = self._debug_entries[-self._max_entries:]
            
            # Log the digest computation
            self._log_digest_computation(debug_info)
            
        except Exception as e:
            logger.warning(f"Failed to record digest debug info: {e}")
    
    def get_debug_entries(self) -> List[DigestDebugInfo]:
        """Get all debug entries."""
        return self._debug_entries.copy()
    
    def clear_debug_entries(self) -> None:
        """Clear all debug entries."""
        self._debug_entries.clear()
    
    def _is_debug_enabled(self) -> bool:
        """Check if digest debugging is enabled."""
        return get_feature_flag('ENABLE_DIGEST_DEBUG', default=False)
    
    def _log_digest_computation(self, debug_info: DigestDebugInfo) -> None:
        """Log digest computation details."""
        logger.debug(
            f"Digest computed - Domain: {debug_info.domain}, "
            f"Digest: {debug_info.digest}, "
            f"Session: {debug_info.session_generation}, "
            f"Inputs: {len(debug_info.raw_inputs)} keys"
        )


# Global debug collector instance
_debug_collector = DigestDebugCollector()


def record_digest_debug(domain: str, raw_inputs: Dict[str, Any], digest: str) -> None:
    """Record digest computation for debugging."""
    _debug_collector.record_digest(domain, raw_inputs, digest)


def get_digest_debug_entries() -> List[DigestDebugInfo]:
    """Get digest debug entries."""
    return _debug_collector.get_debug_entries()


def clear_digest_debug() -> None:
    """Clear digest debug entries."""
    _debug_collector.clear_debug_entries()


@with_error_boundary("digest_debug_panel")
def render_digest_debug_panel() -> None:
    """Render digest debug panel in Streamlit."""
    if not get_feature_flag('ENABLE_DIGEST_DEBUG', default=False):
        return
    
    st.subheader("🔍 Digest Debug Panel")
    st.caption("Development-only debug information for digest computation")
    
    debug_entries = get_digest_debug_entries()
    
    if not debug_entries:
        st.info("No digest computations recorded yet. Interact with the UI to see digest debug information.")
        return
    
    # Control buttons
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("🗑️ Clear Debug Data"):
            clear_digest_debug()
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    with col3:
        st.caption(f"Showing {len(debug_entries)} digest computations")
    
    # Display debug entries
    for i, entry in enumerate(reversed(debug_entries)):  # Show newest first
        with st.expander(f"{entry.domain} - {entry.digest} ({entry.timestamp})", expanded=(i == 0)):
            _render_digest_entry(entry)


@with_error_boundary("digest_entry")
def _render_digest_entry(entry: DigestDebugInfo) -> None:
    """Render a single digest debug entry."""
    # Basic info
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Domain:**", entry.domain)
        st.write("**Digest:**", f"`{entry.digest}`")
        st.write("**Session:**", entry.session_generation)
    
    with col2:
        st.write("**Timestamp:**", entry.timestamp)
        st.write("**Code Version:**", entry.code_version)
        st.write("**Input Keys:**", len(entry.raw_inputs))
    
    # Raw inputs
    st.write("**Raw Inputs:**")
    try:
        raw_json = json.dumps(entry.raw_inputs, indent=2, default=str)
        st.code(raw_json, language="json")
    except Exception as e:
        st.error(f"Failed to display raw inputs: {e}")
        st.write(entry.raw_inputs)
    
    # Normalized inputs
    st.write("**Normalized Inputs:**")
    try:
        normalized_json = json.dumps(entry.normalized_inputs, indent=2, default=str)
        st.code(normalized_json, language="json")
    except Exception as e:
        st.error(f"Failed to display normalized inputs: {e}")
        st.write(entry.normalized_inputs)
    
    # Digest verification
    try:
        recomputed_digest = ui_state_module.stable_digest(entry.normalized_inputs)
        if recomputed_digest == entry.digest:
            st.success("✅ Digest verification passed")
        else:
            st.error(f"❌ Digest mismatch! Expected: {entry.digest}, Got: {recomputed_digest}")
    except Exception as e:
        st.warning(f"⚠️ Could not verify digest: {e}")


def compute_processing_digest_debug() -> str:
    """Compute processing digest with debug recording."""
    raw_inputs = {
        'input_text': getattr(st.session_state, 'input_text', ''),
        'auto_pinyin': getattr(st.session_state, 'auto_pinyin', False),
        'auto_translate': getattr(st.session_state, 'auto_translate', False),
        'translate_order': getattr(st.session_state, 'translate_order', 'pinyin_first'),
    }

    digest = ui_state_module.stable_digest(raw_inputs)
    record_digest_debug('processing', raw_inputs, digest)
    return digest


def compute_layout_digest_debug() -> str:
    """Compute layout digest with debug recording."""
    raw_inputs = {
        'layout_rows': getattr(st.session_state, 'layout_rows', 4),
        'layout_cols': getattr(st.session_state, 'layout_cols', 2),
        'gap_cm': getattr(st.session_state, 'gap_cm', 0.5),
        'margin_cm': getattr(st.session_state, 'margin_cm', 1.0),
        'page_size': getattr(st.session_state, 'page_size', 'A4'),
        'layout_auto_fill': getattr(st.session_state, 'layout_auto_fill', True),
        'card_size_cm': getattr(st.session_state, 'card_size_cm', 'auto'),
    }

    digest = ui_state_module.stable_digest(raw_inputs)
    record_digest_debug('layout', raw_inputs, digest)
    return digest


def compute_style_digest_debug() -> str:
    """Compute style digest with debug recording."""
    raw_inputs = {
        'hanzi_font_size': getattr(st.session_state, 'hanzi_font_size', 48),
        'pinyin_font_size': getattr(st.session_state, 'pinyin_font_size', 18),
        'english_font_size': getattr(st.session_state, 'english_font_size', 14),
        'hanzi_font_family': getattr(st.session_state, 'hanzi_font_family', 'SimHei'),
        'background_color': getattr(st.session_state, 'background_color', '#ffffff'),
    }

    digest = ui_state_module.stable_digest(raw_inputs)
    record_digest_debug('style', raw_inputs, digest)
    return digest


def compute_preview_params_digest_debug(cards_count: int) -> str:
    """Compute preview params digest with debug recording."""
    PREVIEW_CACHE_SCHEMA_VERSION = "v1.0.0"
    
    raw_inputs = {
        'layout_digest': compute_layout_digest_debug(),
        'style_digest': compute_style_digest_debug(),
        'preview_mode': getattr(st.session_state, 'preview_mode', '📄 完整页面'),
        'cards_count': cards_count,
        'schema_version': PREVIEW_CACHE_SCHEMA_VERSION,
        'session_generation': ui_state_module.get_session_generation(),
        'code_version': get_code_version(),
    }

    digest = ui_state_module.stable_digest(raw_inputs)
    record_digest_debug('preview_params', raw_inputs, digest)
    return digest


def enable_digest_debug() -> None:
    """Enable digest debugging for the current session."""
    st.session_state['ENABLE_DIGEST_DEBUG'] = True


def disable_digest_debug() -> None:
    """Disable digest debugging for the current session."""
    st.session_state['ENABLE_DIGEST_DEBUG'] = False


def is_digest_debug_enabled() -> bool:
    """Check if digest debugging is enabled."""
    return get_feature_flag('ENABLE_DIGEST_DEBUG', default=False)
