"""
Test cases for Chinese/Japanese character ambiguity in Google Translate.

This module tests the fix for the issue where Chinese characters that also exist
in Japanese (kanji) were being incorrectly translated as Japanese instead of Chinese.
"""

import json
import services.translation as tr


class DummyResp:
    """Mock response object for Google Translate API."""
    def __init__(self, payload: dict):
        self._data = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self._data


def test_xinmei_translation_fix(monkeypatch):
    """Test that '心美' translates to English, not Japanese romanization."""
    # Mock a proper English translation instead of Japanese "kokorobi"
    payload = {
        "data": {"translations": [{"translatedText": "beautiful heart"}]}
    }
    
    captured_request_data = {}
    
    def capture_urlopen(req, timeout=None):
        captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
        return DummyResp(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)

    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return "zh"
        return default

    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    result = tr.translate_with_google("心美", api_key="DUMMY")
    
    # Verify the source language is explicitly set to Chinese
    assert captured_request_data['data']['source'] == "zh"
    assert captured_request_data['data']['q'] == "心美"
    
    # Verify we get proper English translation, not Japanese romanization
    assert result == "beautiful heart"
    assert result != "kokorobi"  # This was the incorrect Japanese result


def test_ambiguous_chinese_japanese_characters(monkeypatch):
    """Test various Chinese characters that could be confused with Japanese."""
    test_cases = [
        ("心美", "beautiful heart"),  # The original problem case
        ("愛", "love"),               # Love - exists in both Chinese and Japanese
        ("美", "beautiful"),          # Beautiful - common in both languages
        ("心", "heart"),              # Heart - fundamental character in both
        ("学習", "study"),            # Study - compound that exists in both
    ]
    
    for chinese_text, expected_english in test_cases:
        payload = {
            "data": {"translations": [{"translatedText": expected_english}]}
        }
        
        captured_request_data = {}
        
        def capture_urlopen(req, timeout=None):
            captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
            return DummyResp(payload)
        
        monkeypatch.setattr(tr, "urlopen", capture_urlopen)

        def mock_getenv(key, default=None):
            if key == "GOOGLE_TRANSLATE_API_KEY":
                return "DUMMY"
            elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
                return "zh"
            return default

        monkeypatch.setattr(tr.os, "getenv", mock_getenv)
        
        result = tr.translate_with_google(chinese_text, api_key="DUMMY")
        
        # Verify source language is always set to Chinese
        assert captured_request_data['data']['source'] == "zh"
        assert captured_request_data['data']['q'] == chinese_text
        
        # Verify we get the expected English translation
        assert result == expected_english


def test_source_language_prevents_japanese_misdetection(monkeypatch):
    """Test that explicit source language prevents Japanese misdetection."""
    # Simulate what would happen without source language specification
    # vs. with explicit Chinese source language
    
    chinese_chars = ["心美", "愛情", "美麗", "學習"]
    
    for char in chinese_chars:
        payload = {
            "data": {"translations": [{"translatedText": f"english_translation_of_{char}"}]}
        }
        
        captured_request_data = {}
        
        def capture_urlopen(req, timeout=None):
            captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
            return DummyResp(payload)
        
        monkeypatch.setattr(tr, "urlopen", capture_urlopen)

        def mock_getenv(key, default=None):
            if key == "GOOGLE_TRANSLATE_API_KEY":
                return "DUMMY"
            elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
                return "zh"
            return default

        monkeypatch.setattr(tr.os, "getenv", mock_getenv)
        
        result = tr.translate_with_google(char, api_key="DUMMY")
        
        # The key fix: source language must be explicitly set
        assert "source" in captured_request_data['data']
        assert captured_request_data['data']['source'] == "zh"
        
        # Should not be auto-detecting (which would omit the source parameter)
        # This was the root cause of the original issue
        assert result is not None


def test_environment_variable_source_language_override(monkeypatch):
    """Test that GOOGLE_TRANSLATE_SOURCE_LANG environment variable works."""
    payload = {
        "data": {"translations": [{"translatedText": "test translation"}]}
    }
    
    captured_request_data = {}
    
    def capture_urlopen(req, timeout=None):
        captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
        return DummyResp(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    
    # Test with custom source language via environment variable
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        elif key == "GOOGLE_TRANSLATE_SOURCE_LANG":
            return "zh-CN"  # Specific Chinese variant
        return default
    
    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    result = tr.translate_with_google("心美", api_key="DUMMY")
    
    # Verify the custom source language is used
    assert captured_request_data['data']['source'] == "zh-CN"
    assert result == "test translation"


def test_default_source_language_is_chinese(monkeypatch):
    """Test that the default source language is Chinese when not specified."""
    payload = {
        "data": {"translations": [{"translatedText": "default test"}]}
    }
    
    captured_request_data = {}
    
    def capture_urlopen(req, timeout=None):
        captured_request_data['data'] = json.loads(req.data.decode('utf-8'))
        return DummyResp(payload)
    
    monkeypatch.setattr(tr, "urlopen", capture_urlopen)
    
    # Mock environment to only provide API key, not source language
    def mock_getenv(key, default=None):
        if key == "GOOGLE_TRANSLATE_API_KEY":
            return "DUMMY"
        # Don't provide GOOGLE_TRANSLATE_SOURCE_LANG - should default to "zh"
        return default
    
    monkeypatch.setattr(tr.os, "getenv", mock_getenv)
    
    result = tr.translate_with_google("心美", api_key="DUMMY")
    
    # Verify default source language is Chinese
    assert captured_request_data['data']['source'] == "zh"
    assert result == "default test"
