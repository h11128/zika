import types
import ui.sections as us


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
        self.session_state.hanzi_font_family = "SimHei"
        self.session_state.background_color = "#fff"
        self.session_state.layout_rows = 2
        self.session_state.layout_cols = 2
        self.session_state.layout_auto_fill = True
        self.session_state.last_params = {}
        self.session_state.export_ready = {}
        self.session_state.export_data = {}

    def markdown(self, *a, **k): pass
    def header(self, *a, **k): pass
    def radio(self, *a, **k): return "📄 完整页面"
    class _Col:
        def __enter__(self): return self
        def __exit__(self, a,b,c): return False
    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [DummySt._Col() for _ in range(n)]
    class _Tab:
        def __enter__(self): return self
        def __exit__(self, a,b,c): return False
    def tabs(self, labels): return [DummySt._Tab() for _ in labels]
    def text_input(self, *a, **k): return ""
    def button(self, *a, **k): return False
    def write(self, *a, **k): pass
    def info(self, *a, **k): pass
    def warning(self, *a, **k): pass
    def caption(self, *a, **k): pass
    def checkbox(self, label, value=True, **k): return value
    def color_picker(self, label, value=None, **k): return value
    class _Exp:
        def __enter__(self): return self
        def __exit__(self, a,b,c): return False
    def expander(self, *a, **k): return DummySt._Exp()
    def container(self, *a, **k): return DummySt._Exp()

    class components:
        class v1:
            @staticmethod
            def html(*a, **k): pass


def test_render_preview_section_wrapper(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    # Render with some cards
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"} for _ in range(5)]

    # Patch component calls used inside wrapper
    monkeypatch.setattr(us, "render_page_navigation", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_preview_section", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_page_info", lambda *a, **k: None)

    us.render_preview_section_wrapper(cards, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)
    # Ensure last_params updated
    assert st.session_state.current_page == 0 and st.session_state.last_params["layout_rows"] == 2

    # Render empty path
    us.render_preview_section_wrapper([], 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)

