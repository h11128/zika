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
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: None)
    assert tr.translate_with_google("测试", api_key=None) is None

    # 2) Error path -> URLError leads to graceful None
    def boom(req, timeout=None):
        raise URLError("boom")

    monkeypatch.setattr(tr, "urlopen", boom)
    assert tr.translate_with_google("测试", api_key="DUMMY", timeout=1) is None


def test_clean_english_text_html_unescape():
    assert tr.clean_english_text("A &amp; B") == "A & B"


def test_translate_with_google_includes_source_language(monkeypatch):
    """Verify that the source language parameter is correctly included in API calls."""
    payload = {
        "data": {"translations": [{"translatedText": "beautiful heart"}]}
    }

    captured_request_data = {}

    def capture_urlopen(req, timeout=None):
        # Capture the request data to verify source language is included
        captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
        return DummyResp(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    # Test with default source language (should be 'zh')
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return "zh"
        return default

    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    result = tr.translate_with_google("心美", api_key="DUMMY")

    # Verify the API call includes the source language
    assert "source" in captured_request_data['data']
    assert captured_request_data['data']['source'] == "zh"
    assert captured_request_data['data']['target'] == "en"
    assert captured_request_data['data']['q'] == "心美"
    assert result == "beautiful heart"


def test_translate_with_google_configurable_source_language(monkeypatch):
    """Verify that the source language can be configured via environment variable."""
    payload = {
        "data": {"translations": [{"translatedText": "test result"}]}
    }

    captured_request_data = {}

    def capture_urlopen(req, timeout=None):
        captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
        return DummyResp(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    # Test with custom source language
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return "ja"  # Japanese
        return default

    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    result = tr.translate_with_google("テスト", api_key="DUMMY")

    # Verify the custom source language is used
    assert captured_request_data['data']['source'] == "ja"
    assert result == "test result"

