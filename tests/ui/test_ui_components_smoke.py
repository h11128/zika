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
            def html(html, height=0):
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

    # Monkeypatch cached HTML creators to avoid heavy logic
    monkeypatch.setattr(uc, "cached_create_page_preview_html", lambda *a, **k: "<html></html>")
    monkeypatch.setattr(uc, "cached_create_simple_grid_html", lambda *a, **k: "<html></html>")

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    uc.render_preview_section(
        processed_cards=cards,
        preview_mode="📄 完整页面",
        card_size=5.5,
        gap=0.5,
        margin=1.0,
        font_hanzi=48,
        font_pinyin=18,
        font_english=14,
        page_size="A4",
        hanzi_font="SimHei",
        background_color="#FFFFFF",
        rows=2,
        cols=3,
        auto_fill=True,
    )


def test_render_page_info_smoke(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    uc.render_page_info([{"hanzi": "你", "pinyin": "ni3", "english": "you"}], cards_per_page=6, total_pages=1)


def test_create_preview_placeholder_smoke(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    ph = uc.create_preview_placeholder()
    assert ph is not None

