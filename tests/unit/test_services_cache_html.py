from services.cache import (
    create_page_preview_html,
    create_simple_grid_html,
)


def test_create_page_preview_html_auto_fill_and_letter():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_page_preview_html(
        cards, page_num=0,
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="Letter", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=2, auto_fill=True,
    )
    assert "page-container" in html and "grid-template-columns" in html
    assert "第 1 页" in html


def test_create_page_preview_html_page_out_of_range():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_page_preview_html(
        cards, page_num=5,
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="A4", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=2, auto_fill=False,
    )
    assert "页面不存在" in html


def test_create_simple_grid_html_empty_and_nonempty():
    empty_html = create_simple_grid_html([], hanzi_font="SimHei", background_color="#FFFFFF", rows=2, cols=2)
    assert "输入汉字以查看预览" in empty_html

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = create_simple_grid_html(cards, hanzi_font="SimHei", background_color="#FFFFFF", rows=2, cols=2)
    assert "simple-card" in html and "simple-grid" in html

