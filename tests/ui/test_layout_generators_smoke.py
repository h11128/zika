import types
import src.layout_pptx as lp
import src.layout_pdf as ld


class DummyCanvas:
    def __init__(self):
        self.ops = []
    def setFillColor(self, *a, **k): pass
    def setStrokeColor(self, *a, **k): pass
    def setLineWidth(self, *a, **k): pass
    def rect(self, *a, **k): pass
    def setFont(self, *a, **k): pass
    def drawCentredString(self, *a, **k): pass
    def drawString(self, *a, **k): pass
    def saveState(self): pass
    def restoreState(self): pass
    def stringWidth(self, *a, **k): return 10
    def showPage(self): pass
    def save(self): pass


def test_pdf_generate_smoke(monkeypatch, tmp_path):
    # Patch canvas to dummy to avoid file IO
    monkeypatch.setattr(ld, "canvas", types.SimpleNamespace(Canvas=lambda *a, **k: DummyCanvas()))

    gen = ld.PDFCardGenerator(page_size="A4", layout_rows=1, layout_cols=1, layout_auto_fill=True)
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    ok = gen.generate_pdf(cards, str(tmp_path / "out.pdf"))
    assert ok is True


def test_pptx_generate_smoke(monkeypatch, tmp_path):
    # Patch Presentation to avoid real file creation
    class DummySlide:
        class Shapes:
            def add_shape(self, *a, **k):
                class P:
                    def __init__(self):
                        self.font = type("F", (), {"size": None, "name": None, "color": type("C", (), {"rgb": None})()})()
                        self.line_spacing = 1.0
                    def __setattr__(self, name, value):
                        object.__setattr__(self, name, value)
                class TF:
                    def __init__(self):
                        self.paragraphs = [P()]
                        self.margin_left = self.margin_right = self.margin_top_px = self.margin_bottom_px = 0
                        self.vertical_anchor = None
                        self.word_wrap = True
                    def add_paragraph(self):
                        p = P()
                        self.paragraphs.append(p)
                        return p
                    @property
                    def text(self):
                        return ""
                    @text.setter
                    def text(self, v):
                        pass
                class S:
                    def __init__(self):
                        self.fill = type("F", (), {"solid": lambda self: None, "fore_color": type("C", (), {"rgb": None})()})()
                        self.line = type("L", (), {"width_cm": 0, "color": type("C", (), {"rgb": None})()})()
                        self.text_frame = TF()
                return S()
            def add_textbox(self, *a, **k):
                class P:
                    def __init__(self):
                        self.font = type("F", (), {"size": None, "name": None, "color": type("C", (), {"rgb": None})()})()
                        self.line_spacing = 1.0
                    def __setattr__(self, name, value):
                        object.__setattr__(self, name, value)
                class TF:
                    def __init__(self):
                        self.paragraphs = [P()]
                    def add_paragraph(self):
                        p = P()
                        self.paragraphs.append(p)
                        return p
                    @property
                    def text(self):
                        return ""
                    @text.setter
                    def text(self, v):
                        pass
                class T:
                    def __init__(self):
                        self.text_frame = TF()
                return T()
        def __init__(self):
            self.shapes = DummySlide.Shapes()

    class Slides:
        def __init__(self):
            self._slides = []
        def add_slide(self, layout):
            s = DummySlide()
            self._slides.append(s)
            return s

    class DummyPresentation:
        def __init__(self):
            self.slides = Slides()
            # Ensure index 6 exists for blank layout
            self.slide_layouts = [None]*7
        def save(self, *a, **k):
            pass

    monkeypatch.setattr(lp, "Presentation", lambda: DummyPresentation())

    gen = lp.PPTXCardGenerator(page_size="A4", layout_rows=1, layout_cols=1, layout_auto_fill=True)
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    ok = gen.generate_pptx(cards, str(tmp_path / "out.pptx"))
    assert ok is True

