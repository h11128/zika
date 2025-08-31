import types
import pandas as pd
import ui.sections as us


class SS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)
    def __setattr__(self, k, v):
        self[k] = v


class Ctx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


class DummySt:
    def __init__(self):
        self.session_state = SS()
        self.session_state.background_color = "#FFFFFF"
        self.session_state.hanzi_font_family = "SimHei"
        self.session_state.layout_rows = 2
        self.session_state.layout_cols = 3
        self.session_state.layout_auto_fill = True
        self.session_state.total_cards_generated = 0
        self.session_state.export_history = []

    def header(self, *a, **k):
        pass
    def subheader(self, *a, **k):
        pass
    def markdown(self, *a, **k):
        pass
    def caption(self, *a, **k):
        pass
    def write(self, *a, **k):
        pass
    def success(self, *a, **k):
        pass
    def error(self, *a, **k):
        pass
    def info(self, *a, **k):
        pass
    def warning(self, *a, **k):
        pass
    def checkbox(self, label, value=True, **kwargs):
        # Return provided default and set session state if key exists
        if 'key' in kwargs and kwargs['key']:
            self.session_state[kwargs['key']] = value
        return value
    def rerun(self):
        pass

    def sidebar(self):
        return Ctx()

    def radio(self, label, options, horizontal=False):
        # Return first option by default
        return options[0]

    def selectbox(self, label, options, index=0, key=None, help=None):
        # Save selection if key supplied
        value = options[index] if isinstance(index, int) else index
        if key:
            self.session_state[key] = value
        return value

    def text_area(self, label, key=None, height_cm=None, placeholder=None, help=None):
        # Do nothing; assume session_state already has key
        pass

    def text_input(self, label, value="", key=None, help=None):
        # Return the provided value and mirror into session_state when key is provided
        if key:
            self.session_state[key] = value
        return value

    def button(self, *a, **k):
        return False

    def file_uploader(self, label, type=None):
        return None

    def color_picker(self, label, value=None, key=None):
        return value

    def columns(self, spec):
        n = spec if isinstance(spec, int) else len(spec)
        return [Ctx() for _ in range(n)]

    def expander(self, *a, **k):
        return Ctx()

    def container(self, *a, **k):
        return Ctx()


def setup_dummy_st(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    return st


def test_render_input_section_manual(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    # Manual input path
    st.radio = lambda *a, **k: "手动输入"
    # Pre-populate input text
    st.session_state.input_text = "你好 世界"
    # Patch parse_input_text to return two cards
    monkeypatch.setattr(us, "parse_input_text", lambda txt: [{"hanzi": h, "pinyin": "", "english": ""} for h in txt.split()])

    cards = us.render_input_section()
    assert len(cards) == 2


def test_render_input_section_upload_csv(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    st.radio = lambda *a, **k: "上传CSV文件"

    class FakeUpload:
        def getvalue(self):
            return "hanzi,pinyin,english\n你,ni3,you\n".encode("utf-8")

    st.file_uploader = lambda *a, **k: FakeUpload()

    cards = us.render_input_section()
    assert len(cards) == 1 and cards[0]["hanzi"] == "你"


def test_render_input_section_upload_csv_missing_col(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    st.radio = lambda *a, **k: "上传CSV文件"

    class FakeUpload:
        def getvalue(self):
            return b"pinyin,english\nni3,you\n"

    st.file_uploader = lambda *a, **k: FakeUpload()

    # Expect error path and []
    cards = us.render_input_section()
    assert cards == []


def test_render_options_and_advanced(monkeypatch):
    st = setup_dummy_st(monkeypatch)

    # Options section
    monkeypatch.setattr(us, "st", st)
    st.checkbox = lambda label, value=True: value
    st.selectbox = lambda label, options, index=0, **kwargs: options[index]
    st.slider = lambda *a, **k: 5.5

    auto_pinyin, auto_translate, page_size, card_size_cm = us.render_options_section()
    assert auto_pinyin is True and auto_translate is True and page_size in ("A4", "Letter") and isinstance(card_size, float)

    # Advanced options
    st.slider = lambda *a, **k: 0.5 if "间距" in a[0] else (1.0 if "边距" in a[0] else (48 if "汉字" in a[0] else (18 if "拼音" in a[0] else 14)))
    st.number_input = lambda *a, **k: 2
    st.selectbox = lambda *a, **k: st.session_state.hanzi_font_family
    st.color_picker = lambda *a, **k: st.session_state.background_color

    # Avoid calling real color palette
    monkeypatch.setattr(us, "render_color_palette", lambda *a, **k: None)

    gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = us.render_advanced_options()
    assert isinstance(gap, float) and isinstance(margin, float)
    assert isinstance(hanzi_font_size, int) and isinstance(pinyin_font_size, int) and isinstance(english_font_size, int)
    assert isinstance(layout_rows, int) and isinstance(layout_cols, int)

