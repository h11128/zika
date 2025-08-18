import pytest

from services.processing import parse_input_text, auto_segment_text, generate_missing_data
from src.dict_utils import create_default_dict

def test_parse_input_text_space_separated():
    text = "  爱   朋友  "  # multiple spaces
    cards = parse_input_text(text)
    assert len(cards) == 2
    assert [c['hanzi'] for c in cards] == ['爱', '朋友']


def test_pipeline_segment_then_parse_cleans_punct():
    raw = "  爱,  朋友  "
    segmented = auto_segment_text(raw)
    cards = parse_input_text(segmented)
    # after segmentation cleanup, parse should produce clean tokens
    assert [c['hanzi'] for c in cards] == ['爱', '朋友']


def test_parse_input_text_only_non_chinese():
    text = "hello world 123 !@#"
    cards = parse_input_text(text)
    assert cards == []


def test_auto_segment_text_with_symbols_and_duplicates():
    raw = "我，我我..爱!!家家 朋友"
    segmented = auto_segment_text(raw)
    # should not be empty and should be de-duplicated in order
    parts = segmented.split()
    assert len(parts) >= 3
    # ensure no punctuation remains
    for p in parts:
        assert all('\u4e00' <= ch <= '\u9fff' for ch in p)


def test_generate_missing_data_switches():
    d = create_default_dict("data")
    cards = [{'hanzi': '爱', 'pinyin': '', 'english': ''}]

    # only pinyin
    out = generate_missing_data(cards, auto_pinyin=True, auto_translate=False, dictionary=d)
    assert out[0]['pinyin'] and not out[0]['english']

    # only translation
    out = generate_missing_data(cards, auto_pinyin=False, auto_translate=True, dictionary=d)
    assert not out[0]['pinyin'] and out[0]['english']

    # both
    out = generate_missing_data(cards, auto_pinyin=True, auto_translate=True, dictionary=d)
    assert out[0]['pinyin'] and out[0]['english']

    # neither
    out = generate_missing_data(cards, auto_pinyin=False, auto_translate=False, dictionary=d)
    assert not out[0]['pinyin'] and not out[0]['english']

