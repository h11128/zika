import src.pinyin_utils as pu


def test_hanzi_to_pinyin_style_fallbacks(monkeypatch):
    # Force first style to return high unicode invalid string, second to work
    calls = {"style": []}

    def fake_pinyin(text, style=None, heteronym=False, errors=None, strict=None):
        calls["style"].append(style)
        if style == pu.Style.TONE:
            # Return a string with a high code point without using the escape in source
            high = chr(0x110000 - 1)  # 0x10FFFF
            return [[high]]  # triggers fallback in hanzi_to_pinyin
        if style == pu.Style.TONE3:
            return [["ni3"]]
        return [["ni"]]

    monkeypatch.setattr(pu, "pinyin", fake_pinyin)

    result = pu.hanzi_to_pinyin("你")
    assert result == "ni3"


def test_get_pinyin_variants_combination(monkeypatch):
    def fake_pinyin(text, style=None, heteronym=False, errors=None):
        return [["x", "y"], ["a"]]
    monkeypatch.setattr(pu, "pinyin", fake_pinyin)
    variants = pu.get_pinyin_variants("好")
    assert set(variants) == {"x a", "y a"}

