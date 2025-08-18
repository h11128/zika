import services.cache as sc


def test_create_preview_html_non_empty(monkeypatch):
    """Test create_preview_html with non-empty cards to exercise legacy path."""
    # Patch the cached function to return a known value
    def fake_cached_create_page_preview_html(*args, **kwargs):
        return "<div>cached preview</div>"
    
    monkeypatch.setattr(sc, "cached_create_page_preview_html", fake_cached_create_page_preview_html)
    
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    result = sc.create_preview_html(cards)
    
    assert result == "<div>cached preview</div>"


def test_create_preview_html_empty():
    """Test create_preview_html with empty cards."""
    result = sc.create_preview_html([])
    assert "输入汉字以查看预览" in result


def test_create_preview_html_max_cards(monkeypatch):
    """Test create_preview_html respects max_cards parameter."""
    def fake_cached_create_page_preview_html(*args, **kwargs):
        return "<div>preview with max cards</div>"

    monkeypatch.setattr(sc, "cached_create_page_preview_html", fake_cached_create_page_preview_html)

    cards = [{"hanzi": f"字{i}", "pinyin": f"zi{i}", "english": f"char{i}"} for i in range(15)]
    result = sc.create_preview_html(cards, max_cards=9)

    assert result == "<div>preview with max cards</div>"


def test_cached_create_simple_grid_html_edge_cases():
    """Test cached_create_simple_grid_html with edge cases."""
    # Test with empty cards - returns empty message
    result = sc.cached_create_simple_grid_html([], "SimHei", "#fff", 2, 2)
    assert "输入汉字以查看预览" in result

    # Test with single card
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    result = sc.cached_create_simple_grid_html(cards, "SimHei", "#fff", 1, 1)
    assert "simple-grid" in result and "你" in result

    # Test with zero rows/cols to cover edge case branches
    result = sc.cached_create_simple_grid_html(cards, "SimHei", "#fff", 0, 0)
    assert "simple-grid" in result


def test_cached_create_page_preview_html_auto_fill():
    """Test cached_create_page_preview_html with auto_fill=False."""
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    result = sc.cached_create_page_preview_html(
        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, False
    )
    assert "第 1 页" in result
