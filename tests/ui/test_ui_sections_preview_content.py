import types
import ui.sections as us
from core.config import AppConfig


class SS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)
    def __setattr__(self, k, v):
        self[k] = v


class DummySt:
    def __init__(self):
        self.session_state = SS()
        self.session_state.current_page = 0

    def error(self, *a, **k):
        pass

    class components:
        class v1:
            @staticmethod
            def html(html, height_cm=0):
                pass


def test_render_preview_content_non_empty(monkeypatch):
    """Test render_preview_content with non-empty cards."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    # Mock state functions
    def fake_get_layout_settings():
        return {"layout_rows": 2, "layout_cols": 2}
    
    def fake_get_current_page():
        return 0
    
    def fake_set_current_page(page):
        st.session_state.current_page = page
    
    monkeypatch.setattr(us, "get_layout_settings", fake_get_layout_settings)
    monkeypatch.setattr(us, "get_current_page", fake_get_current_page)
    monkeypatch.setattr(us, "set_current_page", fake_set_current_page)
    
    # Mock render functions
    monkeypatch.setattr(us, "render_page_navigation", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_preview_section", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_page_info", lambda *a, **k: None)
    
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    config = AppConfig.default()
    
    cards_per_page, total_pages = us.render_preview_content(cards, config)
    
    assert cards_per_page == 4  # 2x2 grid
    assert total_pages == 1


def test_render_preview_content_empty(monkeypatch):
    """Test render_preview_content with empty cards."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    # Mock create_preview_html for empty case
    def fake_create_preview_html(cards):
        return "<div>empty preview</div>"
    
    monkeypatch.setattr(us, "create_preview_html", fake_create_preview_html)
    
    config = AppConfig.default()
    cards_per_page, total_pages = us.render_preview_content([], config)
    
    assert cards_per_page == 0
    assert total_pages == 1


def test_render_preview_content_page_reset(monkeypatch):
    """Test render_preview_content resets page when out of range."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    # Mock state functions - current page is out of range
    def fake_get_layout_settings():
        return {"layout_rows": 2, "layout_cols": 2}
    
    def fake_get_current_page():
        return 5  # Out of range for 1 card
    
    set_page_calls = []
    def fake_set_current_page(page):
        set_page_calls.append(page)
        st.session_state.current_page = page
    
    monkeypatch.setattr(us, "get_layout_settings", fake_get_layout_settings)
    monkeypatch.setattr(us, "get_current_page", fake_get_current_page)
    monkeypatch.setattr(us, "set_current_page", fake_set_current_page)
    
    # Mock render functions
    monkeypatch.setattr(us, "render_page_navigation", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_preview_section", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_page_info", lambda *a, **k: None)
    
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    config = AppConfig.default()
    
    us.render_preview_content(cards, config)
    
    # Verify page was reset to 0
    assert 0 in set_page_calls


def test_render_preview_content_legacy(monkeypatch):
    """Test render_preview_content_legacy wrapper function."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    # Mock get_layout_settings for legacy wrapper
    def fake_get_layout_settings():
        return {"layout_rows": 3, "layout_cols": 3, "layout_auto_fill": True}
    
    monkeypatch.setattr(us, "get_layout_settings", fake_get_layout_settings)
    
    # Mock render_preview_content to return known values
    def fake_render_preview_content(cards, config):
        return 9, 1  # 3x3 grid, 1 page
    
    monkeypatch.setattr(us, "render_preview_content", fake_render_preview_content)
    
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    preview_params = {
        "hanzi_font_family": "SimHei",
        "background_color": "#ffffff",
        "preview_mode": "📄 完整页面"
    }
    layout_params = {
        "card_size_cm": 5.5,
        "gap_cm": 0.5,
        "margin_cm": 1.0,
        "page_size": "A4",
        "hanzi_font_size": 48,
        "pinyin_font_size": 18,
        "english_font_size": 14
    }
    
    cards_per_page, total_pages = us.render_preview_content_legacy(
        cards, preview_params, layout_params
    )
    
    assert cards_per_page == 9
    assert total_pages == 1


def test_validate_preview_inputs():
    """Test _validate_preview_inputs function."""
    # Test with valid inputs
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    config = AppConfig.default()
    
    validated_cards, validated_config = us._validate_preview_inputs(cards, config)
    
    assert validated_cards == cards
    assert validated_config == config
    
    # Test with invalid inputs
    validated_cards, validated_config = us._validate_preview_inputs("not a list", "not a config")
    
    assert validated_cards == []
    assert isinstance(validated_config, AppConfig)


def test_calculate_pagination(monkeypatch):
    """Test _calculate_pagination function."""
    def fake_get_layout_settings():
        return {"layout_rows": 2, "layout_cols": 3}
    
    monkeypatch.setattr(us, "get_layout_settings", fake_get_layout_settings)
    
    cards = [{"hanzi": f"字{i}", "pinyin": f"zi{i}", "english": f"char{i}"} for i in range(10)]
    
    cards_per_page, total_pages = us._calculate_pagination(cards)
    
    assert cards_per_page == 6  # 2x3 grid
    assert total_pages == 2  # 10 cards / 6 per page = 2 pages


def test_manage_page_state(monkeypatch):
    """Test _manage_page_state function."""
    def fake_get_current_page():
        return 5  # Out of range
    
    set_page_calls = []
    def fake_set_current_page(page):
        set_page_calls.append(page)
    
    monkeypatch.setattr(us, "get_current_page", fake_get_current_page)
    monkeypatch.setattr(us, "set_current_page", fake_set_current_page)
    
    us._manage_page_state(total_pages=3)
    
    # Should reset to page 0
    assert 0 in set_page_calls


def test_render_preview_ui(monkeypatch):
    """Test _render_preview_ui function."""
    # Mock all render functions
    render_calls = []
    
    def mock_render_page_navigation(total_pages):
        render_calls.append(("page_nav", total_pages))
    
    def mock_render_preview_section(*args, **kwargs):
        render_calls.append(("preview_section", args, kwargs))
    
    def mock_render_page_info(cards, cards_per_page, total_pages):
        render_calls.append(("page_info", len(cards), cards_per_page, total_pages))
    
    monkeypatch.setattr(us, "render_page_navigation", mock_render_page_navigation)
    monkeypatch.setattr(us, "render_preview_section", mock_render_preview_section)
    monkeypatch.setattr(us, "render_page_info", mock_render_page_info)
    
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    config = AppConfig.default()
    
    us._render_preview_ui(cards, config, cards_per_page=4, total_pages=1)
    
    # Verify all render functions were called
    assert len(render_calls) == 3
    assert render_calls[0][0] == "page_nav"
    assert render_calls[1][0] == "preview_section"
    assert render_calls[2][0] == "page_info"


def test_render_empty_preview(monkeypatch):
    """Test _render_empty_preview function."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    html_calls = []
    def mock_html(html, height_cm=0):
        html_calls.append((html, height))
    
    # Mock create_preview_html
    def fake_create_preview_html(cards):
        return "<div>empty</div>"
    
    monkeypatch.setattr(us, "create_preview_html", fake_create_preview_html)
    st.components.v1.html = mock_html
    
    us._render_empty_preview()
    
    assert len(html_calls) == 1
    assert html_calls[0][0] == "<div>empty</div>"
    assert html_calls[0][1] == 650
