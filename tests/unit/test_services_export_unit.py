import types
import builtins

import services.export as se


class DummyGen:
    def __init__(self, success=True):
        self.success = success
        self.calls = []
    def generate_pptx(self, cards, path, **kwargs):
        self.calls.append(("pptx", cards, path, kwargs))
        return self.success
    def generate_pdf(self, cards, path, **kwargs):
        self.calls.append(("pdf", cards, path, kwargs))
        return self.success


def test_export_cards_pptx_and_pdf_success(monkeypatch, tmp_path):
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]

    # Patch generator classes to our dummy; ignore actual file writing
    monkeypatch.setattr(se, "PPTXCardGenerator", lambda **opts: DummyGen(True))
    monkeypatch.setattr(se, "PDFCardGenerator", lambda **opts: DummyGen(True))

    data = se.export_cards(cards, "pptx", page_size="A4", rows=2, cols=2, auto_fill=True)
    assert isinstance(data, (bytes, bytearray))

    data = se.export_cards(cards, "pdf", page_size="A4", rows=2, cols=2, auto_fill=False)
    assert isinstance(data, (bytes, bytearray))


def test_export_cards_unsupported_and_failure(monkeypatch):
    cards = []

    # Unsupported format
    try:
        se.export_cards(cards, "txt")
        assert False, "should have raised"
    except ValueError:
        pass

    # Failure case returns exception
    monkeypatch.setattr(se, "PPTXCardGenerator", lambda **opts: DummyGen(False))
    try:
        se.export_cards(cards, "pptx")
        assert False, "should have raised"
    except Exception as e:
        assert "generation failed" in str(e)

