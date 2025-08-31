import types
import ui.components as uc


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
        self.session_state.background_color = "#FFFFFF"
        self.session_state.current_page = 0

    # Minimal st API used in components
    def columns(self, spec):
        # Return tuple of dummy columns
        return (self, self, self, self, self)

    def button(self, label, disabled=False, use_container_width=False, key=None):
        return False

    def selectbox(self, label, options, index=0, format_func=None, key=None):
        # Return the selected option value (like Streamlit)
        return options[index]

    class components:
        class v1:
            @staticmethod
            def html(html, height_cm=0):
                pass

    def empty(self):
        return self

    # Context manager compatibility
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def container(self):
        return self

    def info(self, *args, **kwargs):
        pass

    def rerun(self):
        pass


def setup_dummy_st(monkeypatch):
    dummy = DummySt()
    monkeypatch.setattr(uc, "st", dummy)
    return dummy


def test_render_page_navigation_noop_when_single_page(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    uc.render_page_navigation(total_pages=1)  # should do nothing without errors


def test_render_preview_section_calls_html(monkeypatch):
    st = setup_dummy_st(monkeypatch)

    # Initialize session state with required keys
    st.session_state.current_page = 0
    st.session_state.layout_rows = 2
    st.session_state.layout_cols = 3
    st.session_state.layout_auto_fill = True
    st.session_state.hanzi_font_family = "SimHei"
    st.session_state.background_color = "#FFFFFF"

    # Monkeypatch cached HTML creators to avoid heavy logic
    monkeypatch.setattr(uc, "cached_create_page_preview_html", lambda *a, **k: "<html></html>")
    monkeypatch.setattr(uc, "cached_create_simple_grid_html", lambda *a, **k: "<html></html>")

    # Mock the immediate rendering functions from services.cache_v2
    monkeypatch.setattr("services.cache_v2.create_page_preview_html_immediate", lambda *a, **k: "<html></html>")
    monkeypatch.setattr("services.cache_v2.create_simple_grid_html_immediate", lambda *a, **k: "<html></html>")

    # Mock the state functions to avoid complex dependencies
    monkeypatch.setattr("core.state.get_all_ui_params", lambda *a, **k: {})
    monkeypatch.setattr("core.state.check_params_changed", lambda *a, **k: False)

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    uc.render_preview_section(
        processed_cards=cards,
        preview_mode="📄 完整页面",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        hanzi_font_size=48,
        pinyin_font_size=18,
        english_font_size=14,
        page_size="A4",
        hanzi_font_family="SimHei",
        background_color="#FFFFFF",
        layout_rows=2,
        layout_cols=3,
        layout_auto_fill=True,
    )


def test_render_page_info_smoke(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    uc.render_page_info([{"hanzi": "你", "pinyin": "ni3", "english": "you"}], cards_per_page=6, total_pages=1)


def test_create_preview_placeholder_smoke(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    ph = uc.create_preview_placeholder()
    assert ph is not None

