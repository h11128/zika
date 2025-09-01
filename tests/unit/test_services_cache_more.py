from services.cache_v2 import cached_create_page_preview_html_v2, cached_create_simple_grid_html_v2
from services.preview_types import LayoutOptions, Typography, VisualOptions

# Helper functions for v2 API compatibility
def cached_create_page_preview_html(cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                                  hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                                  layout_rows=2, layout_cols=3, hanzi_font_family="SimSun",
                                  background_color="#FFFFFF", **kwargs):
    """Cached compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=True,
        card_size_cm=card_size_cm,
        gap_cm=gap_cm,
        margin_cm=margin_cm,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=hanzi_font_size,
        pinyin_font_size_pt=pinyin_font_size,
        english_font_size_pt=english_font_size,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='📄 完整页面'
    )
    return cached_create_page_preview_html_v2(cards, page_num, layout, typography, visual)

def cached_create_simple_grid_html(cards, hanzi_font_family="SimSun", background_color="#FFFFFF", **kwargs):
    """Cached compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=2,
        layout_cols=3,
        layout_auto_fill=True,
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=48,
        pinyin_font_size_pt=18,
        english_font_size_pt=14,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='🔲 简单网格'
    )
    return cached_create_simple_grid_html_v2(cards, layout, typography, visual)


def test_cached_create_page_preview_html(tmp_path):
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html1 = cached_create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)
    html2 = cached_create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)
    assert html1 == html2 and "第 1 页" in html1


def test_cached_create_simple_grid_html():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = cached_create_simple_grid_html(cards, "SimHei", "#fff", 2, 2, 48, 18, 14, 5.5, True)
    assert "simple-grid" in html

