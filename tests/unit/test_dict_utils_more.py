import os
import pytest
from src.dict_utils import ChineseDict, create_default_dict


def test_create_default_dict_mini_loaded():
    d = create_default_dict("data")
    stats = d.get_statistics()
    assert stats['mini_dict_entries'] > 0


def test_lookup_fallback_character_breakdown():
    # Construct a dict without entries for the multi-char word but with single chars
    d = ChineseDict()
    # provide mini dict for single characters only
    d.mini_dict = {"爱": ["love"], "家": ["home"], "朋友": ["friend"]}
    # ask for a composed word not in dict -> should fallback to character breakdown
    word = "爱家"
    trans = d.lookup_translation(word)
    assert trans is not None
    assert "love" in trans
    assert "home" in trans


def test_cedict_optional_loading():
    d = ChineseDict()
    ok = d.load_cedict_file(os.path.join("data", "nonexistent_file.u8"))
    assert ok is False  # nonexistent path returns False

    # Prefer the plain text file for positive path
    ok2 = d.load_cedict_file(os.path.join("data", "cedict_ts.txt"))
    assert ok2 is True

    # ensure statistics report cedict entries >= 1
    stats = d.get_statistics()
    assert stats['cedict_entries'] >= 1

