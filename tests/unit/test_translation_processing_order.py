import types
import pytest

from services import processing as sp
from services import translation as st
from services.translation import clean_english_text


def test_clean_english_text_basic_cases():
    assert clean_english_text("test; testing") == "test; testing"
    assert clean_english_text(" hello ") == "hello"
    # remove chinese entirely
    assert clean_english_text("中文") is None
    # drop bracketed chinese
    assert clean_english_text("(中文) test") == "test"
    # keep bracketed ascii
    assert clean_english_text("(note) test") == "(note) test"


def _make_cards(word: str):
    return [{"hanzi": word, "pinyin": "", "english": ""}]


class DummyDict:
    def __init__(self, mapping):
        self.mapping = mapping

    def lookup_translation(self, hanzi):
        return self.mapping.get(hanzi)


def test_generate_missing_data_local_first_prefers_local(monkeypatch):
    cards = _make_cards("爱")
    d = DummyDict({"爱": "love"})
    # Even if google would return something, local should win
    monkeypatch.setattr(sp, "translate_with_google", lambda text: "google-love")

    out = sp.generate_missing_data(cards, auto_pinyin=False, auto_translate=True, dictionary=d)
    assert out[0]["english"] == "love"


def test_generate_missing_data_local_first_falls_back_to_google(monkeypatch):
    cards = _make_cards("不存在")
    d = DummyDict({})
    monkeypatch.setattr(sp, "translate_with_google", lambda text: "not exist")

    out = sp.generate_missing_data(cards, auto_pinyin=False, auto_translate=True, dictionary=d)
    assert out[0]["english"] == "not exist"


def test_generate_missing_data_ordered_google_first(monkeypatch):
    cards = _make_cards("测试")
    d = DummyDict({"测试": "test; testing"})
    monkeypatch.setattr(st, "translate_with_google", lambda text: "trial")

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="google_first")
    assert out[0]["english"] == "trial"  # google first wins


def test_generate_missing_data_ordered_local_only(monkeypatch):
    cards = _make_cards("测试")
    d = DummyDict({"测试": "test; testing"})
    # If google would return, it should be ignored in local_only
    monkeypatch.setattr(st, "translate_with_google", lambda text: "trial")

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="local_only")
    assert out[0]["english"] == "test; testing"


def test_generate_missing_data_ordered_google_only(monkeypatch):
    cards = _make_cards("测试")
    d = DummyDict({"测试": "test; testing"})
    monkeypatch.setattr(st, "translate_with_google", lambda text: "trial")

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="google_only")
    assert out[0]["english"] == "trial"


def test_generate_missing_data_ordered_mixed_mode(monkeypatch):
    cards = _make_cards("测试")
    d = DummyDict({"测试": "test; examination"})  # Use non-overlapping words
    monkeypatch.setattr(st, "translate_with_google", lambda text: "trial")

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="mixed")
    # Should combine both results since they're different
    assert out[0]["english"] == "test; examination | trial"


def test_generate_missing_data_ordered_mixed_mode_same_result(monkeypatch):
    cards = _make_cards("测试")
    d = DummyDict({"测试": "test"})
    monkeypatch.setattr(st, "translate_with_google", lambda text: "test")

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="mixed")
    # Should not duplicate when results are the same
    assert out[0]["english"] == "test"


def test_generate_missing_data_ordered_dict_mixed_mode(monkeypatch):
    cards = _make_cards("测试")

    # Create a mock dictionary with lookup_translation_mixed method
    class MockDictWithMixed:
        def lookup_translation(self, word):
            return "basic translation"

        def lookup_translation_mixed(self, word):
            return "mixed dictionary result"

    d = MockDictWithMixed()

    out = sp.generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=d, translate_order="dict_mixed")
    assert out[0]["english"] == "mixed dictionary result"


def test_final_translation_has_no_chinese(monkeypatch):
    # Local returns mixed content including Chinese; cleaner should remove it
    cards = _make_cards("混合")
    class DirtyDict:
        def lookup_translation(self, hanzi):
            return "混合; mix"
    monkeypatch.setattr(st, "translate_with_google", lambda text: None)
    out = sp.generate_missing_data(cards, auto_pinyin=False, auto_translate=True, dictionary=DirtyDict())
    assert out[0]["english"] is not None
    assert all(ord(ch) < 128 or ch.isascii() for ch in out[0]["english"] if ch.strip())  # basic ASCII assurance

