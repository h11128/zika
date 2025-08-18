from services.processing import parse_input_text, auto_segment_text, generate_missing_data
from src.dict_utils import create_default_dict


def test_parse_input_text_filters_non_chinese():
    cards = parse_input_text("你好 world 学习")
    assert any(c["hanzi"] == "你好" for c in cards)
    assert all(c["hanzi"] != "world" for c in cards)


def test_auto_segment_text_splits_and_deduplicates():
    # Include punctuation and duplicates; auto_segment_text should remove non-Chinese and dedupe
    segmented = auto_segment_text("你好，世界世界!!!学习中文中文中文")
    assert " " in segmented  # space-separated
    # Basic property: no repeated adjacent segments when deduped by appearance order
    parts = segmented.split()
    assert len(parts) == len(list(dict.fromkeys(parts)))


def test_generate_missing_data_integration():
    dictionary = create_default_dict("data")
    cards = [{"hanzi": "朋友", "pinyin": "", "english": ""}]
    processed = generate_missing_data(cards, auto_pinyin=True, auto_translate=True, dictionary=dictionary)
    assert processed[0]["pinyin"]
    assert processed[0]["english"]

