import json
from urllib.error import URLError
import services.translation as tr


def test_translate_with_google_handles_urlerror(monkeypatch):
    # Force urlopen to raise URLError to cover error branch (line ~118)
    def boom(*args, **kwargs):
        raise URLError("network down")

    monkeypatch.setattr(tr, "urlopen", boom)
    # Provide a fake API key so it attempts the request path
    out = tr.translate_with_google("你好", api_key="fake-key")
    assert out is None


def test_combine_two_translations_basic():
    out = tr.combine_two_translations("run", "sprint")
    assert out in ("run | sprint", "sprint | run")


class MockDictOK:
    def lookup_translation(self, text):
        return "hello"


class MockDictRaises:
    def lookup_translation(self, text):
        raise RuntimeError("boom")


class MockDictMixed:
    def lookup_translation_mixed(self, text):
        return "greet"


def test_strategy_google_first_falls_back_to_local(monkeypatch):
    monkeypatch.setattr(tr, "translate_with_google", lambda t: None)
    out = tr.translate_with_strategy("测试", dictionary=MockDictOK(), strategy="google_first")
    assert out == "hello"


def test_strategy_local_only_handles_exception():
    out = tr.translate_with_strategy("测试", dictionary=MockDictRaises(), strategy="local_only")
    assert out is None


def test_strategy_google_only(monkeypatch):
    monkeypatch.setattr(tr, "translate_with_google", lambda t: "world")
    out = tr.translate_with_strategy("测试", dictionary=MockDictOK(), strategy="google_only")
    assert out == "world"


def test_strategy_dict_mixed_none_dict():
    # Cover early return path when dictionary is None in try_local_mixed
    out = tr.translate_with_strategy("测试", dictionary=None, strategy="dict_mixed")
    assert out is None


def test_strategy_dict_mixed_with_mixed_method():
    out = tr.translate_with_strategy("测试", dictionary=MockDictMixed(), strategy="dict_mixed")
    assert out == "greet"

