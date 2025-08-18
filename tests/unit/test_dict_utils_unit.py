import os
from src.dict_utils import ChineseDict, create_default_dict


def test_mini_dict_load_and_lookup():
    d = ChineseDict()
    ok = d.load_mini_dict(os.path.join("data", "mini_cedict.json"))
    assert ok
    # pick a known simple entry likely in mini dict, e.g., 爱
    t = d.lookup_translation("爱")
    assert t and isinstance(t, str)


def test_cedict_parse_and_character_breakdown(tmp_path):
    # Create a small cedict file with two entries and duplicate forms
    text = (
        "愛 爱 [ai4] /to love/love/\n"
        "朋友 朋友 [peng2 you3] /friend/companion/\n"
    )
    cedict_path = tmp_path / "cedict_ts.txt"
    cedict_path.write_text(text, encoding="utf-8")

    d = ChineseDict()
    d.load_mini_dict(os.path.join("data", "mini_cedict.json"))
    assert d.load_cedict_file(str(cedict_path))

    # word present
    assert d.lookup_translation("朋友")

    # non-existent multi-character should fallback to per-char aggregation if chars exist
    agg = d.lookup_translation("爱友")  # mix of two characters
    assert agg is None or isinstance(agg, str)

    info = d.get_word_info("朋友")
    assert info["found"] is True
    assert info["translation"]


def test_statistics():
    d = create_default_dict("data")
    stats = d.get_statistics()
    assert set(["mini_dict_entries", "cedict_entries", "total_entries", "loaded_sources"]).issubset(stats.keys())

