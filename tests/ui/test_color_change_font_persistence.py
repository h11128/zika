import ui.sections as us
from typing import Any, Dict


def test_color_change_does_not_reset_preview_font_sizes(monkeypatch):
    # Prepare session state with custom font sizes (non-default)
    us.st.session_state.clear()
    us.st.session_state.font_hanzi = 26
    us.st.session_state.font_pinyin = 12
    us.st.session_state.font_english = 14
    us.st.session_state.card_size = 5.5
    us.st.session_state.gap_cm = 0.5
    us.st.session_state.margin_cm = 1.0
    us.st.session_state.page_size = 'A4'
    us.st.session_state.hanzi_font = 'SimHei'
    us.st.session_state.background_color = '#ffffff'
    us.st.session_state.rows = 2
    us.st.session_state.cols = 3
    us.st.session_state.auto_fill = True
    # Ensure comparison key exists to avoid AttributeError in wrapper
    us.st.session_state.last_params = {}

    # Capture what preview receives
    captured: Dict[str, Any] = {}

    def capture_preview(processed_cards, preview_mode, card_size, gap, margin,
                        font_hanzi, font_pinyin, font_english,
                        page_size, hanzi_font, background_color,
                        rows, cols, auto_fill):
        captured['font_hanzi'] = font_hanzi
        captured['font_pinyin'] = font_pinyin
        captured['font_english'] = font_english
        captured['background_color'] = background_color
        # No real rendering in test
        return None

    monkeypatch.setattr(us, 'render_preview_section', capture_preview)

    # Change color and simulate an upstream bug passing default fonts into the wrapper
    us.st.session_state.background_color = '#ffcc00'

    # Call wrapper that collects values and renders preview, intentionally passing defaults
    us.render_preview_section_wrapper(
        processed_cards=[{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}],
        card_size=us.st.session_state.card_size,
        gap=us.st.session_state.gap_cm,
        margin=us.st.session_state.margin_cm,
        font_hanzi=48,  # simulate wrong default passed from upstream after color change
        font_pinyin=18,
        font_english=14,
        page_size=us.st.session_state.page_size,
        hanzi_font=us.st.session_state.hanzi_font,
        background_color=us.st.session_state.background_color,
        rows=us.st.session_state.rows,
        cols=us.st.session_state.cols,
        auto_fill=us.st.session_state.auto_fill,
    )

    # Assert: preview should receive the chosen font sizes from session_state, not passed defaults
    assert captured['font_hanzi'] == 26
    assert captured['font_pinyin'] == 12
    assert captured['font_english'] == 14
    assert captured['background_color'] == '#ffcc00'

