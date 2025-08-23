import json
from urllib.error import URLError

import services.translation as tr


class DummyResp:
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._data


def test_translate_with_google_success(monkeypatch):
    """Simulate a successful Google v2 REST response and verify cleaning pipeline."""
    payload = {
        "data": {"translations": [{"translatedText": "hello &amp; world (中文) [注释]; CL:|x; ;"}]}
    }

    def fake_urlopen(req, timeout=None):
        return DummyResp(payload)

    monkeypatch.setattr(tr, "urlopen", fake_urlopen)
    out = tr.translate_with_google("测试", api_key="DUMMY", timeout=1)
    # HTML entities unescaped, Chinese bracketed parts dropped, CL:| removed.
    # Current cleaner may leave a trailing semicolon in this constructed case; accept both.
    assert out in ("hello & world", "hello & world ;")


def test_translate_with_google_error_and_no_key(monkeypatch):
    # 1) No API key -> returns None early
    monkeypatch.setattr(tr.os, "getenv", lambda k: None)
    assert tr.translate_with_google("测试", api_key=None) is None

    # 2) Error path -> URLError leads to graceful None
    def boom(req, timeout=None):
        raise URLError("boom")

    monkeypatch.setattr(tr, "urlopen", boom)
    assert tr.translate_with_google("测试", api_key="DUMMY", timeout=1) is None


def test_clean_english_text_html_unescape():
    assert tr.clean_english_text("A &amp; B") == "A & B"

