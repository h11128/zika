import types
import time
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
        self.session_state.card_size = 5.5
        self.session_state.gap_cm = 0.5
        self.session_state.margin_cm = 1.0
        self.session_state.font_hanzi = 48
        self.session_state.font_pinyin = 18
        self.session_state.font_english = 14
        self.session_state.page_size = "A4"
        self.session_state.hanzi_font = "SimHei"
        self.session_state.background_color = "#fff"
        self.session_state.rows = 2
        self.session_state.cols = 2
        self.session_state.auto_fill = True
        self.session_state.export_ready = {}
        self.session_state.export_data = {}
        self.session_state.export_history = []
        self.session_state.total_cards_generated = 0
        self._button_results = {}
        self._download_calls = []

    def header(self, *a, **k):
        pass

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        class Col:
            def __enter__(self): return self
            def __exit__(self, a,b,c): return False
            def button(self, label, use_container_width=False):
                return self._parent._button_results.get(label, False)
            def download_button(self, label, data, file_name, mime, use_container_width=False):
                self._parent._download_calls.append({
                    "label": label,
                    "data": data,
                    "file_name": file_name,
                    "mime": mime
                })
            def spinner(self, text):
                class Spinner:
                    def __enter__(self): return self
                    def __exit__(self, a,b,c): return False
                return Spinner()
            def error(self, *a, **k): pass
        cols = [Col() for _ in range(n)]
        for col in cols:
            col._parent = self
        return cols

    def button(self, label, use_container_width=False):
        return self._button_results.get(label, False)

    def download_button(self, label, data, file_name, mime, use_container_width=False):
        self._download_calls.append({
            "label": label,
            "data": data,
            "file_name": file_name,
            "mime": mime
        })

    def spinner(self, text):
        class Spinner:
            def __enter__(self): return self
            def __exit__(self, a,b,c): return False
        return Spinner()

    def error(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass


def test_render_export_section_pptx_and_pdf(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    monkeypatch.setattr(us, "time", types.SimpleNamespace(strftime=lambda fmt: "20250101_120000"))

    # Mock export_cards to return bytes
    def fake_export_cards(cards, format_type, **kwargs):
        return b"fake file content"

    monkeypatch.setattr("services.export.export_cards", fake_export_cards)

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]

    # Test PPTX export - button press triggers export and download button
    st._button_results["📄 导出 PowerPoint"] = True
    us.render_export_section(cards)

    # Verify export data was stored and download button called
    export_params = {'card_size': 5.5, 'gap': 0.5, 'margin': 1.0, 'font_hanzi': 48, 'font_pinyin': 18, 'font_english': 14, 'page_size': 'A4', 'hanzi_font': 'SimHei', 'background_color': '#fff', 'rows': 2, 'cols': 2, 'auto_fill': True}
    export_key = f"1_{hash(str(export_params))}"
    assert export_key in st.session_state.export_data
    assert st.session_state.export_ready[export_key] == 'pptx'
    assert len(st.session_state.export_history) == 1
    assert st.session_state.total_cards_generated == 1
    # Download button should be called since data exists
    assert len(st._download_calls) == 1
    assert st._download_calls[0]["label"] == "⬇️ 下载 PPTX"

    # Reset for PDF test
    st._button_results = {"📑 导出 PDF": True}
    st._download_calls = []

    us.render_export_section(cards)

    # Verify PDF export
    assert st.session_state.export_ready[export_key] == 'pdf'
    assert len(st.session_state.export_history) == 2
    assert st.session_state.total_cards_generated == 2
    # Download button should be called for PDF too
    assert len(st._download_calls) == 1
    assert st._download_calls[0]["label"] == "⬇️ 下载 PDF"


def test_render_export_section_error_handling(monkeypatch):
    """Test export error handling."""
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    monkeypatch.setattr(us, "time", types.SimpleNamespace(strftime=lambda fmt: "20250101_120000"))

    # Mock export_cards to raise an exception
    def fake_export_cards(cards, format_type, **kwargs):
        raise Exception("Export failed")

    monkeypatch.setattr("services.export.export_cards", fake_export_cards)

    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]

    # Test error handling for PPTX export
    st._button_results["📄 导出 PowerPoint"] = True
    us.render_export_section(cards)

    # Should not have any export data due to error
    export_params = {'card_size': 5.5, 'gap': 0.5, 'margin': 1.0, 'font_hanzi': 48, 'font_pinyin': 18, 'font_english': 14, 'page_size': 'A4', 'hanzi_font': 'SimHei', 'background_color': '#fff', 'rows': 2, 'cols': 2, 'auto_fill': True}
    export_key = f"1_{hash(str(export_params))}"
    assert export_key not in st.session_state.export_data


def test_render_export_section_empty_cards(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    
    # Should return early for empty cards
    us.render_export_section([])
    # No assertions needed - just ensure no exceptions
