"""
Comprehensive unit tests for the Google Translate source language specification fix.

This module tests all aspects of the fix that addresses the issue where Chinese characters
were being incorrectly auto-detected as Japanese, leading to wrong translations.

Tests cover:
- Source language parameter inclusion in API calls
- Environment variable configuration
- Default behavior
- Edge cases and error handling
- Backward compatibility
"""

import json
import os
from unittest.mock import patch
import services.translation as tr


class MockResponse:
    """Mock response object for Google Translate API."""
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._data


def test_source_language_always_included_in_api_call(monkeypatch):
    """Test that source language parameter is always included in Google Translate API calls."""
    payload = {"data": {"translations": [{"translatedText": "test"}]}}
    captured_requests = []
    
    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)
    
    # Test the fix: source language should always be included
    result = tr.translate_with_google("测试", api_key="DUMMY")
    
    assert len(captured_requests) == 1
    request_data = captured_requests[0]
    
    # Critical assertion: source parameter must be present
    assert "source" in request_data, "Source language parameter missing from API call"
    assert request_data["source"] == "zh", f"Expected source='zh', got source='{request_data['source']}'"
    assert request_data["target"] == "en"
    assert request_data["q"] == "测试"
    assert result == "test"


def test_default_source_language_is_chinese(monkeypatch):
    """Test that the default source language is Chinese when no environment variable is set."""
    payload = {"data": {"translations": [{"translatedText": "default chinese"}]}}
    captured_requests = []
    
    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    
    # Mock environment with only API key, no source language override
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return default  # Return the default value (should be "zh")
        return default
    
    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    result = tr.translate_with_google("心美", api_key="DUMMY")
    
    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh"
    assert result == "default chinese"


def test_environment_variable_source_language_override(monkeypatch):
    """Test that GOOGLE_TRANSLATE_SOURCE_LANG environment variable overrides default."""
    test_cases = [
        ("zh-CN", "simplified chinese"),
        ("zh-TW", "traditional chinese"),
        ("ja", "japanese override"),
        ("ko", "korean override"),
    ]
    
    for source_lang, expected_translation in test_cases:
        payload = {"data": {"translations": [{"translatedText": expected_translation}]}}
        captured_requests = []
        
        def capture_urlopen(req, timeout=None):
            request_data = json.loads(req.data.decode('utf-8'))
            captured_requests.append(request_data)
            return MockResponse(payload)
        
        monkeypatch.setattr(tr, "urlopen", capture_urlopen)
        
        def mock_getenv(key, default=None):
            if key == "GOOGLE_TRANSLATE_API_KEY":
                return "DUMMY"
            elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
                return source_lang
            return default
        
        monkeypatch.setattr(tr.os, "getenv", mock_getenv)
        
        result = tr.translate_with_google("测试", api_key="DUMMY")
        
        assert len(captured_requests) == 1
        assert captured_requests[0]["source"] == source_lang
        assert result == expected_translation


def test_source_language_with_empty_environment_variable(monkeypatch):
    """Test behavior when GOOGLE_TRANSLATE_SOURCE_LANG is set but empty."""
    payload = {"data": {"translations": [{"translatedText": "empty env test"}]}}
    captured_requests = []
    
    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return ""  # Empty string
        return default
    
    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    result = tr.translate_with_google("测试", api_key="DUMMY")
    
    assert len(captured_requests) == 1
    # Empty string should be used as-is (Google API will handle it)
    assert captured_requests[0]["source"] == ""
    assert result == "empty env test"


def test_source_language_with_none_environment_variable(monkeypatch):
    """Test behavior when GOOGLE_TRANSLATE_SOURCE_LANG is explicitly None."""
    payload = {"data": {"translations": [{"translatedText": "none env test"}]}}
    captured_requests = []

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            # When env var is None, os.getenv should return the default value
            return default  # This will be "zh" when called with default="zh"
        return default

    monkeypatch.setattr(tr.os, "getenv", mock_getenv)

    result = tr.translate_with_google("测试", api_key="DUMMY")

    assert len(captured_requests) == 1
    # None should fall back to default "zh"
    assert captured_requests[0]["source"] == "zh"
    assert result == "none env test"


def test_source_language_preserved_through_error_handling(monkeypatch):
    """Test that source language is included even when errors occur."""
    from urllib.error import HTTPError
    
    captured_requests = []
    
    def capture_and_fail(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        # Simulate HTTP error after capturing the request
        raise HTTPError(None, 500, "Server Error", None, None)
    
    monkeypatch.setattr(tr, "urlopen", capture_and_fail)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)
    
    result = tr.translate_with_google("测试", api_key="DUMMY")
    
    # Should return None due to error, but request should still have source language
    assert result is None
    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh"


def test_source_language_with_different_text_inputs(monkeypatch):
    """Test source language specification with various text inputs."""
    test_cases = [
        ("心美", "beautiful heart"),      # The original problem case
        ("你好", "hello"),               # Simple greeting
        ("学习中文", "learn Chinese"),    # Learning Chinese
        ("北京大学", "Beijing University"), # Beijing University
        ("一二三四五", "one two three four five"), # Numbers
        ("春夏秋冬", "spring summer autumn winter"), # Seasons
    ]

    for i, (text_input, expected_translation) in enumerate(test_cases):
        # Use English-only translations since clean_english_text removes Chinese characters
        payload = {"data": {"translations": [{"translatedText": expected_translation}]}}
        captured_requests = []

        def make_capture_urlopen(expected_payload):
            def capture_urlopen(req, timeout=None):
                request_data = json.loads(req.data.decode('utf-8'))
                captured_requests.append(request_data)
                return MockResponse(expected_payload)
            return capture_urlopen

        monkeypatch.setattr(tr, "urlopen", make_capture_urlopen(payload))
        monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)

        result = tr.translate_with_google(text_input, api_key="DUMMY")

        assert len(captured_requests) == 1, f"Test {i}: Expected 1 request, got {len(captured_requests)}"
        assert captured_requests[0]["source"] == "zh", f"Test {i}: Expected source='zh', got {captured_requests[0]['source']}"
        assert captured_requests[0]["q"] == text_input, f"Test {i}: Expected q='{text_input}', got {captured_requests[0]['q']}"
        assert result == expected_translation, f"Test {i}: Expected '{expected_translation}', got '{result}'"


def test_backward_compatibility_api_structure(monkeypatch):
    """Test that the API call structure maintains backward compatibility."""
    payload = {"data": {"translations": [{"translatedText": "compatibility test"}]}}
    captured_requests = []
    
    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)
    
    result = tr.translate_with_google("测试", api_key="DUMMY")
    
    assert len(captured_requests) == 1
    request_data = captured_requests[0]
    
    # Verify all expected fields are present
    expected_fields = {"q", "source", "target", "format"}
    actual_fields = set(request_data.keys())
    assert expected_fields.issubset(actual_fields), f"Missing fields: {expected_fields - actual_fields}"
    
    # Verify field values
    assert request_data["target"] == "en"
    assert request_data["format"] == "text"
    assert request_data["source"] == "zh"  # This is the new addition
    assert result == "compatibility test"


def test_source_language_with_api_key_parameter(monkeypatch):
    """Test source language when API key is passed as parameter vs environment."""
    payload = {"data": {"translations": [{"translatedText": "param test"}]}}
    captured_requests = []
    
    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    
    # Mock environment with no API key but custom source language
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return None  # No API key in environment
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return "zh-TW"  # Custom source language
        return default
    
    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    # Pass API key as parameter
    result = tr.translate_with_google("测试", api_key="PARAM_KEY")

    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh-TW"  # Should still use env var for source
    assert result == "param test"


def test_source_language_with_malformed_response(monkeypatch):
    """Test source language handling when Google API returns malformed response."""
    # Test with missing translations array
    malformed_payload = {"data": {}}
    captured_requests = []

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(malformed_payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)

    result = tr.translate_with_google("测试", api_key="DUMMY")

    # Should return None due to malformed response, but source should still be included
    assert result is None
    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh"


def test_source_language_with_json_decode_error(monkeypatch):
    """Test source language handling when response cannot be decoded as JSON."""
    captured_requests = []

    class BadJsonResponse:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def read(self):
            return b"invalid json response"

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return BadJsonResponse()

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)

    result = tr.translate_with_google("测试", api_key="DUMMY")

    # Should return None due to JSON decode error, but source should still be included
    assert result is None
    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh"


def test_source_language_configuration_isolation(monkeypatch):
    """Test that source language configuration doesn't interfere with other environment variables."""
    payload = {"data": {"translations": [{"translatedText": "isolation test"}]}}
    captured_requests = []

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    # Mock environment with various unrelated variables
    def mock_getenv(key, default=None):
        env_vars = {
            "GOOGLE_TRANSLATE_API_KEY": "DUMMY",
            "GOOGLE_TRANSLATE_SOURCE_LANG": "zh-CN",
            "LANG": "en_US.UTF-8",
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/user",
            "PYTHONPATH": "/some/path",
        }
        return env_vars.get(key, default)

    monkeypatch.setattr(tr.os, "getenv", mock_getenv)

    result = tr.translate_with_google("测试", api_key="DUMMY")

    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "zh-CN"
    assert result == "isolation test"


def test_source_language_with_unicode_text(monkeypatch):
    """Test source language specification with various Unicode Chinese text."""
    unicode_test_cases = [
        ("🇨🇳中文", "Chinese with flag"),      # Chinese with flag emoji
        ("中文\n换行", "Chinese with newline"),     # Chinese with newline
        ("中文\t制表符", "Chinese with tab"),   # Chinese with tab
        ("中文 空格", "Chinese with space"),      # Chinese with space
        ("繁體中文", "Traditional Chinese"),       # Traditional Chinese
        ("简体中文", "Simplified Chinese"),       # Simplified Chinese
    ]

    for i, (text_input, expected_translation) in enumerate(unicode_test_cases):
        # Use English-only translations since clean_english_text removes Chinese characters
        payload = {"data": {"translations": [{"translatedText": expected_translation}]}}
        captured_requests = []

        def make_capture_urlopen(expected_payload):
            def capture_urlopen(req, timeout=None):
                request_data = json.loads(req.data.decode('utf-8'))
                captured_requests.append(request_data)
                return MockResponse(expected_payload)
            return capture_urlopen

        monkeypatch.setattr(tr, "urlopen", make_capture_urlopen(payload))
        monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)

        result = tr.translate_with_google(text_input, api_key="DUMMY")

        assert len(captured_requests) == 1, f"Unicode test {i}: Expected 1 request, got {len(captured_requests)}"
        assert captured_requests[0]["source"] == "zh", f"Unicode test {i}: Expected source='zh'"
        assert captured_requests[0]["q"] == text_input, f"Unicode test {i}: Expected q='{text_input}'"
        assert result == expected_translation, f"Unicode test {i}: Expected '{expected_translation}', got '{result}'"


def test_source_language_environment_variable_precedence(monkeypatch):
    """Test that GOOGLE_TRANSLATE_SOURCE_LANG takes precedence over default."""
    payload = {"data": {"translations": [{"translatedText": "precedence test"}]}}
    captured_requests = []

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)
        return MockResponse(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    # Test with environment variable that should override default
    with patch.dict(os.environ, {
        "GOOGLE_TRANSLATE_API_KEY": "DUMMY",
        "GOOGLE_TRANSLATE_SOURCE_LANG": "ja"  # Should override default "zh"
    }):
        result = tr.translate_with_google("测试", api_key="DUMMY")

    assert len(captured_requests) == 1
    assert captured_requests[0]["source"] == "ja"  # Should use env var, not default
    assert result == "precedence test"


def test_source_language_fix_prevents_auto_detection(monkeypatch):
    """Test that the fix prevents auto-detection by always including source parameter."""
    payload = {"data": {"translations": [{"translatedText": "no auto detection"}]}}
    captured_requests = []

    def capture_urlopen(req, timeout=None):
        request_data = json.loads(req.data.decode('utf-8'))
        captured_requests.append(request_data)

        # Verify that source is always present (this was the original bug)
        assert "source" in request_data, "CRITICAL: Source parameter missing - auto-detection would occur!"

        return MockResponse(payload)

    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    monkeypatch.setattr(tr.os, "getenv", lambda k, default=None: "DUMMY" if k == "GOOGLE_TRANSLATE_API_KEY" else default)

    # Test with the original problematic text
    result = tr.translate_with_google("心美", api_key="DUMMY")

    assert len(captured_requests) == 1
    request_data = captured_requests[0]

    # The critical fix: source parameter must ALWAYS be present
    assert "source" in request_data
    assert request_data["source"] is not None
    assert request_data["source"] != ""  # Should have a value
    assert result == "no auto detection"
