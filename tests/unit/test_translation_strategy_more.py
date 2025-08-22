import pytest
import services.translation as tr


class MockMixedDict:
    def __init__(self, mapping):
        self.mapping = mapping

    def lookup_translation_mixed(self, text):
        return self.mapping.get(text)


def test_translate_with_google_generic_exception(monkeypatch):
    """Generic exception path should return None (broad except Exception)."""
    def boom(req, timeout=None):
        raise ValueError("unexpected")

    monkeypatch.setattr(tr, "urlopen", boom)
    out = tr.translate_with_google("测试", api_key="DUMMY", timeout=1)
    assert out is None


def test_translate_with_strategy_dict_mixed_cleans_result():
    """dict_mixed strategy should use lookup_translation_mixed and clean Chinese in brackets."""
    dictionary = MockMixedDict({"测试": "hello (中文)"})
    result = tr.translate_with_strategy("测试", dictionary, "dict_mixed")
    assert result == "hello"

