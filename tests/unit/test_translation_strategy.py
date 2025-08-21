import pytest
from services.translation import translate_with_strategy, _are_different_translations


class MockDict:
    def __init__(self, mapping):
        self.mapping = mapping

    def lookup_translation(self, text):
        return self.mapping.get(text)


def test_are_different_translations():
    # Same text (case insensitive)
    assert not _are_different_translations("world", "World")
    assert not _are_different_translations("hello", "hello")
    
    # Containment relationships
    assert not _are_different_translations("hello", "hello world")
    assert not _are_different_translations("test", "testing")
    assert not _are_different_translations("book", "textbook")
    
    # Truly different
    assert _are_different_translations("love", "affection")
    assert _are_different_translations("car", "automobile")
    
    # None cases
    assert not _are_different_translations(None, "test")
    assert not _are_different_translations("test", None)
    assert not _are_different_translations(None, None)


def test_translate_with_strategy_local_only(monkeypatch):
    # Mock Google to ensure it's not called
    monkeypatch.setattr("services.translation.translate_with_google", lambda x: "should_not_be_called")
    
    dictionary = MockDict({"测试": "test"})
    result = translate_with_strategy("测试", dictionary, "local_only")
    assert result == "test"


def test_translate_with_strategy_google_only(monkeypatch):
    # Mock Google
    monkeypatch.setattr("services.translation.translate_with_google", lambda x: "google_result")
    
    dictionary = MockDict({"测试": "local_result"})
    result = translate_with_strategy("测试", dictionary, "google_only")
    assert result == "google_result"


def test_translate_with_strategy_mixed_different(monkeypatch):
    # Mock Google
    monkeypatch.setattr("services.translation.translate_with_google", lambda x: "google_result")
    
    dictionary = MockDict({"测试": "local_result"})
    result = translate_with_strategy("测试", dictionary, "mixed")
    assert result == "local_result | google_result"


def test_translate_with_strategy_mixed_same(monkeypatch):
    # Mock Google to return same as local
    monkeypatch.setattr("services.translation.translate_with_google", lambda x: "same_result")
    
    dictionary = MockDict({"测试": "same_result"})
    result = translate_with_strategy("测试", dictionary, "mixed")
    assert result == "same_result"  # Should not duplicate


def test_translate_with_strategy_mixed_containment(monkeypatch):
    # Mock Google to return contained text
    monkeypatch.setattr("services.translation.translate_with_google", lambda x: "test")
    
    dictionary = MockDict({"测试": "testing"})
    result = translate_with_strategy("测试", dictionary, "mixed")
    assert result == "testing"  # Should not duplicate due to containment
