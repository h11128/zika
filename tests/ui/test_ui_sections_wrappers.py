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
        # initialize required keys referenced in us.render_preview_section_wrapper
        self.session_state.current_page = 0
        self.session_state.last_params = {}
        self.session_state.export_ready = {}
        self.session_state.export_data = {}
        self.session_state.hanzi_font = "SimHei"
        self.session_state.export_history = []
        self.session_state.total_cards_generated = 0

        self.session_state.background_color = "#FFFFFF"
        self.session_state.rows = 2
        self.session_state.cols = 3
        self.session_state.auto_fill = True

    # Streamlit surface used in sections
    def markdown(self, *a, **k):
        pass

    def header(self, *a, **k):
        pass

    def radio(self, label, options, horizontal=True, help=None):
        return options[0]

    def write(self, *a, **k):
        pass

    class _Ctx:
        def __enter__(self):
            return DummySt()
        def __exit__(self, exc_type, exc, tb):
            return False

    def expander(self, *a, **k):
        return DummySt._Ctx()

    def spinner(self, *a, **k):
        return DummySt._Ctx()

    def tabs(self, labels):
        # Return list of context managers to support `with tab:` usage
        return [DummySt._Ctx() for _ in labels]

    def columns(self, spec):
        # Provide context-managing columns
        n = spec if isinstance(spec, int) else (len(spec) if hasattr(spec, '__len__') else 3)
        return tuple(DummySt._Ctx() for _ in range(n))

    def text_input(self, *a, **k):
        # return provided default value when present
        return k.get("value", "")

    def info(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def button(self, *a, **k):
        return False

    def download_button(self, *a, **k):
        return None

    class components:
        class v1:
            @staticmethod
            def html(html, height=0):
                pass
            def html(html, height=0):
                pass


def setup_dummy_st(monkeypatch):
    dummy = DummySt()
    monkeypatch.setattr(us, "st", dummy)
    return dummy


def test_render_preview_section_wrapper_param_change_and_empty(monkeypatch):
    st = setup_dummy_st(monkeypatch)

    # Patch functions that produce heavy output
    monkeypatch.setattr(us, "render_page_navigation", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_preview_section", lambda *a, **k: None)
    monkeypatch.setattr(us, "render_page_info", lambda *a, **k: None)

    # Case 1: processed_cards non-empty triggers param change handling
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    us.render_preview_section_wrapper(
        processed_cards=cards,
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="A4", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=3, auto_fill=True,
    )
    # last_params set and current_page reset has occurred
    assert st.session_state.current_page == 0
    assert st.session_state.last_params.get("total_cards") == 1

    # Case 2: empty cards -> simple HTML path
    called = {"html": False}
    def fake_html(*a, **k):
        called["html"] = True
    monkeypatch.setattr(us, "create_preview_html", lambda cards: "<html></html>")
    monkeypatch.setattr(us.st.components.v1, "html", lambda *a, **k: fake_html())

    us.render_preview_section_wrapper(
        processed_cards=[],
        card_size=5.5, gap=0.5, margin=1.0,
        font_hanzi=48, font_pinyin=18, font_english=14,
        page_size="A4", hanzi_font="SimHei", background_color="#FFFFFF",
        rows=2, cols=3, auto_fill=True,
    )
    assert called["html"] is True


def test_render_export_section_gated(monkeypatch):
    st = setup_dummy_st(monkeypatch)

    # No processed cards -> return early
    us.render_export_section([])

    # Add a card and simulate export flow
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]

    # Patch button to return True once, then False
    btn_calls = {"count": 0}
    def fake_button(*a, **k):
        btn_calls["count"] += 1
        return btn_calls["count"] == 1

    monkeypatch.setattr(us, "time", types.SimpleNamespace(strftime=lambda fmt: "2025-01-01 00:00:00"))
    monkeypatch.setattr(us, "render_page_navigation", lambda *a, **k: None)
    monkeypatch.setattr(us, "st", st)
    st.button = fake_button

    # Patch export to return bytes
    def fake_export(cards, fmt, **params):
        return b"content"
    monkeypatch.setattr(us, "render_page_info", lambda *a, **k: None)
    monkeypatch.setattr(us, "st", st)
    # Patch the export function used by sections via its import path
    import services.export as svc_export
    monkeypatch.setattr(svc_export, "export_cards", fake_export, raising=False)

    # Stub download_button to not raise
    def fake_download_button(**kwargs):
        pass
    st.download_button = fake_download_button

    us.render_export_section(cards)
    # After first button click and export, state should be populated
    assert st.session_state.export_history
    assert st.session_state.total_cards_generated >= 1

