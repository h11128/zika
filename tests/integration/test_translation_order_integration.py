import os
import pytest

from services.processing import generate_missing_data_ordered
from src.dict_utils import create_default_dict


def test_integration_translation_order_local_first(tmp_path, monkeypatch):
    # No Google key -> google path returns None; local should work
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)

    dictionary = create_default_dict("data")
    cards = [{"hanzi": "爱", "pinyin": "", "english": ""}]

    out = generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=dictionary, translate_order="local_first")
    assert out and out[0]["english"]


def test_integration_translation_order_google_first_uses_local_when_no_key(tmp_path, monkeypatch):
    # With no API key, Google will be skipped; then local should be used
    monkeypatch.delenv("GOOGLE_TRANSLATE_API_KEY", raising=False)

    dictionary = create_default_dict("data")
    # Use a word likely in local dictionary to ensure fallback success
    cards = [{"hanzi": "家", "pinyin": "", "english": ""}]

    out = generate_missing_data_ordered(cards, auto_pinyin=False, auto_translate=True, dictionary=dictionary, translate_order="google_first")
    assert out and out[0]["english"]

