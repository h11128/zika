import types
import builtins
import importlib

import pytest

import src.pinyin_utils as pu


def test_hanzi_to_pinyin_all_styles_fail_returns_original(monkeypatch):
    # Make all pinyin() calls raise to trigger the final fallback path
    def boom(*args, **kwargs):
        raise Exception("pinyin fail")

    monkeypatch.setattr(pu, "pinyin", boom)
    text = "汉"
    result = pu.hanzi_to_pinyin(text)
    assert result == text  # last resort returns original


def test_get_pinyin_variants_on_exception(monkeypatch):
    def boom(*args, **kwargs):
        raise Exception("pinyin fail")

    monkeypatch.setattr(pu, "pinyin", boom)
    # Should fall back to hanzi_to_pinyin without heteronym
    variants = pu.get_pinyin_variants("好")
    assert isinstance(variants, list) and variants

