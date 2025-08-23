import builtins
import io
import types
import services.export as ex


class DummyGen:
    def __init__(self, *a, **k):
        pass

    def generate_pptx(self, cards, path, **opts):
        with open(path, "wb") as f:
            f.write(b"ok")
        return True

    def generate_pdf(self, cards, path, **opts):
        with open(path, "wb") as f:
            f.write(b"ok")
        return True


def test_export_cards_pptx_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "PPTXCardGenerator", DummyGen)
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    content = ex.export_cards(cards, "pptx")
    assert content == b"ok"


def test_export_cards_pdf_and_cleanup(monkeypatch, tmp_path):
    monkeypatch.setattr(ex, "PDFCardGenerator", DummyGen)
    cards = [{"hanzi": "好", "pinyin": "hao3", "english": "good"}]
    content = ex.export_cards(cards, "pdf")
    assert content == b"ok"

