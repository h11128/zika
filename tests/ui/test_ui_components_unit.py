import types
import ui.components as uc


class SS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)
    def __setattr__(self, k, v):
        self[k] = v


class Ctx:
    def __init__(self, obj=None):
        self.obj = obj or self
    def __enter__(self):
        return self.obj
    def __exit__(self, exc_type, exc, tb):
        return False


class Placeholder:
    def container(self):
        return Ctx(self)


class DummySt:
    def __init__(self):
        self.session_state = SS()
        self.session_state.background_color = "#112233"
        self.session_state.current_page = 0
        self._html_calls = []
        self._buttons = {}

    def rerun(self):
        pass

    def error(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def selectbox(self, label, options, index=0, format_func=None, key=None):
        # Return index by default; render_color_palette fallback passes preset options
        return index if isinstance(index, int) else 0

    def button(self, label, disabled=False, use_container_width=False):
        # Return scripted result by label if present
        return self._buttons.get(label, False)

    def empty(self):
        return Placeholder()

    def columns(self, spec):
        n = spec if isinstance(spec, int) else (len(spec) if hasattr(spec, '__len__') else 3)
        return [Ctx(self) for _ in range(n)]

    class components:
        class v1:
            @staticmethod
            def html(html, height=0):
                pass


def setup_dummy_st(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(uc, "st", st)
    return st


def test_render_color_palette_fallback(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    # Force import failure of color_palette by raising in import
    def boom_import(*a, **k):
        raise Exception("no component")
    monkeypatch.setattr(uc, "DEFAULT_BACKGROUND_COLOR", "#112233", raising=False)
    # Simulate exception before selectbox path: patch to raise when trying to import
    monkeypatch.setattr(uc, "st", st)
    # Monkeypatch import inside function scope by making components unavailable through try/except
    # Easiest: monkeypatch uc.render_color_palette to enter except branch by raising
    # But we want to exercise the code; simulate by patching components.color_palette attribute lookup
    class FakeModule: pass
    FakeModule.color_palette = property(lambda self: (_ for _ in ()).throw(Exception("boom")))
    uc.components = types.SimpleNamespace(color_palette=boom_import)

    # Stub selectbox to return first option index 0
    st.selectbox = lambda *a, **k: 0

    uc.render_color_palette(["#112233", "#445566"])  # should hit fallback without exceptions


def test_render_color_palette_success(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    st.session_state.background_color = "#112233"

    # Provide a fake components.color_palette module
    import sys, types as _types
    pkg = _types.ModuleType("components")
    mod = _types.ModuleType("components.color_palette")
    def fake_color_palette(preset_colors, value, key):
        return "#445566"  # different from current to trigger change
    mod.color_palette = fake_color_palette
    sys.modules["components"] = pkg
    sys.modules["components.color_palette"] = mod

    uc.render_color_palette(["#112233", "#445566"])  # should update background_color
    assert st.session_state.background_color == "#445566"


def test_render_page_navigation_buttons_and_select(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    st.session_state.current_page = 1
    # Make selectbox choose page 2 (index 2)
    st.selectbox = lambda label, options, index=0, format_func=None, key=None: 2
    # Press all navigation buttons
    st._buttons = {"⏮️ 首页": True, "◀️ 上页": True, "▶️ 下页": True, "⏭️ 末页": True}
    uc.render_page_navigation(total_pages=3)
    # Final state should be last page due to "末页"
    assert st.session_state.current_page == 2


def test_render_preview_section_modes(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    st.session_state.current_page = 0

    # Patch cached HTML creators
    monkeypatch.setattr(uc, "cached_create_page_preview_html", lambda *a, **k: "<html>page</html>")
    monkeypatch.setattr(uc, "cached_create_simple_grid_html", lambda *a, **k: "<html>grid</html>")

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"} for _ in range(10)]

    # Full page mode
    uc.render_preview_section(cards, "📄 完整页面", 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)

    # Simple grid mode
    uc.render_preview_section(cards, "🔲 简单网格", 5.5, 0.5, 1.0, 48, 18, 14, "A4", "SimHei", "#fff", 2, 2, True)

