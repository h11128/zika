"""
UI segmentation behavior tests:
- Clicking segmentation uses a click-time snapshot but must NOT change the checkbox state
- Preview refresh should happen only when the segmented text actually changes
"""

import pytest

import ui.sections as us


def _setup_common_state():
    # Ensure clean state for this test run
    if hasattr(us.st, 'session_state'):
        us.st.session_state.clear()
    # Stabilize template so render_input_section won't overwrite input_text
    us.st.session_state.template_select = '自定义'
    us.st.session_state.last_template = '自定义'
    # Minimal fields used down the stack
    us.st.session_state.preview_mode = '📄 完整页面'


def test_segmentation_no_text_change_does_not_refresh_preview_nor_change_checkbox(monkeypatch):
    _setup_common_state()

    # Initial checkbox state True; but snapshot will be False, to ensure we don't overwrite checkbox
    us.st.session_state.preserve_duplicates = True

    # Input text before segmentation
    us.st.session_state.input_text = '你好 世界'

    # Simulate click-time snapshot and request segmentation
    us.st.session_state.pending_preserve_duplicates = False
    us.st.session_state.apply_segmentation = True

    # Put a marker to detect whether preview params get cleared
    us.st.session_state.last_preview_params = {'marker': 'keep'}

    # Monkeypatch auto_segment_text to return the same text (no change)
    monkeypatch.setattr(us, 'auto_segment_text', lambda text, preserve_duplicates=False: text)

    # Track whether clear_preview_cache is called
    called = {'v': False}
    def _clear_cache():
        called['v'] = True
    monkeypatch.setattr('services.cache_v2.clear_preview_cache', _clear_cache, raising=True)

    # Execute
    us.render_input_section()

    # Checkbox state should remain unchanged
    assert us.st.session_state.preserve_duplicates is True

    # No preview refresh when text unchanged
    assert called['v'] is False
    assert us.st.session_state.get('last_preview_params') == {'marker': 'keep'}

    # apply_segmentation should be reset
    assert us.st.session_state.get('apply_segmentation') is False


def test_segmentation_text_change_refreshes_preview_but_does_not_change_checkbox(monkeypatch):
    _setup_common_state()

    # Initial checkbox state False; snapshot True should NOT alter checkbox after action
    us.st.session_state.preserve_duplicates = False

    # Input text before segmentation
    us.st.session_state.input_text = '你好 世界'

    # Simulate click-time snapshot and request segmentation
    us.st.session_state.pending_preserve_duplicates = True
    us.st.session_state.apply_segmentation = True

    # Put a marker to detect whether preview params get cleared
    us.st.session_state.last_preview_params = {'marker': 'remove'}

    # Monkeypatch auto_segment_text to return a changed text
    monkeypatch.setattr(us, 'auto_segment_text', lambda text, preserve_duplicates=False: text + ' 分词')

    # Track whether clear_preview_cache is called
    called = {'v': False}
    def _clear_cache():
        called['v'] = True
    monkeypatch.setattr('services.cache_v2.clear_preview_cache', _clear_cache, raising=True)

    # Execute
    us.render_input_section()

    # Checkbox state should remain unchanged
    assert us.st.session_state.preserve_duplicates is False

    # Preview refresh when text changed
    assert called['v'] is True
    assert 'last_preview_params' not in us.st.session_state

    # apply_segmentation should be reset
    assert us.st.session_state.get('apply_segmentation') is False

