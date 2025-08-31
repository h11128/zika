import ui.sections as us
from typing import Any, Dict


def test_color_change_does_not_reset_preview_font_sizes(monkeypatch):
    # Prepare session state with custom font sizes (non-default)
    us.st.session_state.clear()
    us.st.session_state.hanzi_font_size = 26
    us.st.session_state.pinyin_font_size = 12
    us.st.session_state.english_font_size = 14
    us.st.session_state.card_size_cm = 5.5
    us.st.session_state.gap_cm = 0.5
    us.st.session_state.margin_cm = 1.0
    us.st.session_state.page_size = 'A4'
    us.st.session_state.hanzi_font_family = 'SimHei'
    us.st.session_state.background_color = '#ffffff'
    us.st.session_state.layout_rows = 2
    us.st.session_state.layout_cols = 3
    us.st.session_state.layout_auto_fill = True
    # Ensure comparison key exists to avoid AttributeError in wrapper
    us.st.session_state.last_params = {}

    # Capture what preview receives
    captured: Dict[str, Any] = {}

    def capture_preview(processed_cards, preview_mode, card_size, gap, margin,
                        hanzi_font_size, pinyin_font_size, english_font_size,
                        page_size, hanzi_font_family, background_color,
                        layout_rows, layout_cols, auto_fill):
        captured['hanzi_font_size'] = hanzi_font_size
        captured['pinyin_font_size'] = pinyin_font_size
        captured['english_font_size'] = english_font_size
        captured['background_color'] = background_color
        # No real rendering in test
        return None

    monkeypatch.setattr(us, 'render_preview_section', capture_preview)

    # Change color and simulate an upstream bug passing default fonts into the wrapper
    us.st.session_state.background_color = '#ffcc00'

    # Call wrapper that collects values and renders preview, intentionally passing defaults
    us.render_preview_section_wrapper(
        processed_cards=[{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}],
        card_size_cm=us.st.session_state.card_size_cm,
        gap_cm=us.st.session_state.gap_cm,
        margin_cm=us.st.session_state.margin_cm,
        hanzi_font_size=48,  # simulate wrong default passed from upstream after color change
        pinyin_font_size=18,
        english_font_size=14,
        page_size=us.st.session_state.page_size,
        hanzi_font_family=us.st.session_state.hanzi_font_family,
        background_color=us.st.session_state.background_color,
        layout_rows=us.st.session_state.layout_rows,
        layout_cols=us.st.session_state.layout_cols,
        layout_auto_fill=us.st.session_state.layout_auto_fill,
    )

    # Assert: preview should receive the chosen font sizes from session_state, not passed defaults
    assert captured['hanzi_font_size'] == 26
    assert captured['pinyin_font_size'] == 12
    assert captured['english_font_size'] == 14
    assert captured['background_color'] == '#ffcc00'

