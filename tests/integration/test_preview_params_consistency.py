import pytest
from ui.sections import render_preview_section_wrapper
import ui.sections as us


def test_wrapper_uses_session_state_over_passed_defaults(monkeypatch):
    # Seed session_state with non-defaults
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
    us.st.session_state.last_params = {}

    captured = {}
    def capture(*args, **kwargs):
        # args order is fixed; extract what we need
        (
            processed_cards, preview_mode, card_size, gap, margin,
            font_hanzi, font_pinyin, font_english,
            page_size, hanzi_font, background_color,
            rows, cols, auto_fill
        ) = args
        captured['font_hanzi'] = font_hanzi
        captured['font_pinyin'] = font_pinyin
        captured['font_english'] = font_english
        captured['background_color'] = background_color
        return None

    monkeypatch.setattr(us, 'render_preview_section', capture)

    # Intentionally pass defaults; wrapper must use session_state instead
    render_preview_section_wrapper(
        processed_cards=[{'hanzi': '一', 'pinyin': 'yī', 'english': 'one'}],
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size='A4', hanzi_font='SimHei', background_color='#ff0000',
        rows=2, cols=3, auto_fill=True
    )

    assert captured['font_hanzi'] == 26
    assert captured['font_pinyin'] == 12
    assert captured['font_english'] == 14
    # background_color comes from session state if set; our session had '#ffffff'
    assert captured['background_color'] == '#ffffff'

