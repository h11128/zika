import os
from src.dict_utils import ChineseDict


def test_lookup_fallback_and_get_word_info():
    d = ChineseDict()
    # Load minimal mini dict
    d.mini_dict = {"你": ["you"], "好": ["good"]}
    # Load basic cedict
    d.cedict_data = {"朋友": ["friend", "companion"]}

    # Direct mini match
    assert d.lookup_translation("你") == "you"

    # CEDICT match cleans and joins
    assert "friend" in d.lookup_translation("朋友")

    # Character breakdown (lookup_translation returns joined definitions without characters)
    assert d.lookup_translation("你好") == "you + good"

    # get_word_info paths
    info = d.get_word_info("你")
    assert info["found"] and info["source"] == "mini_dict"

    info = d.get_word_info("朋友")
    assert info["found"] and info["source"] == "cedict"

    info = d.get_word_info("你好")
    assert info["found"] and info["source"] == "character_breakdown"

