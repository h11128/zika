from services.cache_v2 import cached_create_page_preview_html, cached_create_simple_grid_html


def test_cached_create_page_preview_html(tmp_path):
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html1 = cached_create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)
    html2 = cached_create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)
    assert html1 == html2 and "第 1 页" in html1


def test_cached_create_simple_grid_html():
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    html = cached_create_simple_grid_html(cards, "SimHei", "#fff", 2, 2, 48, 18, 14, 5.5, True)
    assert "simple-grid" in html

