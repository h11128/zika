import types
import src.layout_pdf as ld


def test_pdf_layout_info_and_wrap(monkeypatch, tmp_path):
    # Patch canvas.Canvas to a dummy that records calls
    class DummyCanvas:
        def __init__(self, *a, **k): pass
        def setStrokeColor(self, *a, **k): pass
        def setLineWidth(self, *a, **k): pass
        def rect(self, *a, **k): pass
        def setFont(self, *a, **k): pass
        def setFillColor(self, *a, **k): pass
        def stringWidth(self, *a, **k): return 10
        def drawString(self, *a, **k): pass
        def showPage(self, *a, **k): pass
        def save(self, *a, **k): pass

    monkeypatch.setattr(ld, "canvas", types.SimpleNamespace(Canvas=DummyCanvas))

    gen = ld.PDFCardGenerator(page_size="A4", layout_rows=1, layout_cols=1, layout_auto_fill=True)
    info = gen.get_layout_info()
    assert info["layout_rows"] == 1 and info["layout_cols"] == 1 and "card_size_cm" in info

    # Use long english to trigger wrapping logic
    long_english = "this is a very long english translation that should wrap across multiple lines for testing purposes"
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": long_english}]
    ok = gen.generate_pdf(cards, str(tmp_path / "out.pdf"))
    assert ok is True

