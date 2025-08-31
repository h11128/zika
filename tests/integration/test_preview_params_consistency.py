import pytest
from ui.sections import render_preview_section_wrapper
import ui.sections as us


def test_wrapper_uses_session_state_over_passed_defaults(monkeypatch):
    # Seed session_state with non-defaults
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
    us.st.session_state.last_params = {}

    captured = {}
    def capture(*args, **kwargs):
        # args order is fixed; extract what we need
        (
            processed_cards, preview_mode, card_size, gap, margin,
            hanzi_font_size, pinyin_font_size, english_font_size,
            page_size, hanzi_font_family, background_color,
            layout_rows, layout_cols, auto_fill
        ) = args
        captured['hanzi_font_size'] = hanzi_font_size
        captured['pinyin_font_size'] = pinyin_font_size
        captured['english_font_size'] = english_font_size
        captured['background_color'] = background_color
        return None

    monkeypatch.setattr(us, 'render_preview_section', capture)

    # Intentionally pass defaults; wrapper must use session_state instead
    render_preview_section_wrapper(
        processed_cards=[{'hanzi': '一', 'pinyin': 'yī', 'english': 'one'}],
        card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
        hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
        page_size='A4', hanzi_font_family='SimHei', background_color='#ff0000',
        layout_rows=2, layout_cols=3, layout_auto_fill=True
    )

    assert captured['hanzi_font_size'] == 26
    assert captured['pinyin_font_size'] == 12
    assert captured['english_font_size'] == 14
    # background_color comes from session state if set; our session had '#ffffff'
    assert captured['background_color'] == '#ffffff'

