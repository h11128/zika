import pytest

import src.pinyin_utils as pu


def test_hanzi_to_pinyin_heteronym_branch(monkeypatch):
    """Cover the heteronym formatting branch (joins with '/')."""
    def fake_pinyin(text, style=None, heteronym=False, errors=None, strict=None):
        # Return two syllable lists; first with multiple options to exercise '/'
        return [["xi", "yi"], ["an"]]

    monkeypatch.setattr(pu, "pinyin", fake_pinyin)
    out = pu.hanzi_to_pinyin("选", heteronym=True)
    assert out == "xi/yi an"


def test_hanzi_to_pinyin_fallback_strict(monkeypatch):
    """Force the main pinyin() calls to fail, but allow the strict=False fallback to work."""
    def fake_pinyin(text, style=None, heteronym=False, errors=None, strict=None):
        # Simulate failure for the main attempts (no 'strict' kw),
        # and return a simple result for the fallback branch which passes strict=False.
        if strict is None:
            raise Exception("simulated failure")
        # Fallback path: return simple lists
        return [["luo"], ["ji"]]

    monkeypatch.setattr(pu, "pinyin", fake_pinyin)
    out = pu.hanzi_to_pinyin("落级", heteronym=False)
    assert out == "luo ji"


def test_helpers_is_chinese_and_validate():
    assert pu.is_chinese_char("你") is True
    assert pu.contains_chinese("hello你") is True
    assert pu.contains_chinese("hello") is False
    assert pu.validate_pinyin("nǐ hǎo 3/2") is True
    assert pu.validate_pinyin("") is False

