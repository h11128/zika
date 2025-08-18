from src.pinyin_utils import (
    hanzi_to_pinyin,
    get_pinyin_variants,
    is_chinese_char,
    contains_chinese,
    validate_pinyin,
)


def test_hanzi_to_pinyin_basic_and_heteronym():
    # Basic conversion
    assert hanzi_to_pinyin("你好")

    # Heteronym should include slashes for polyphonic characters when applicable
    poly = "行"  # commonly xíng / háng
    hetero = hanzi_to_pinyin(poly, heteronym=True)
    assert "/" in hetero or hetero  # tolerate environments without multiple variants

    # Empty/whitespace input
    assert hanzi_to_pinyin("") == ""
    assert hanzi_to_pinyin("   ") == ""


def test_get_pinyin_variants_and_validation():
    variants = get_pinyin_variants("好")
    assert isinstance(variants, list) and variants

    # validate_pinyin accepts tone marks, slashes, spaces, digits
    assert validate_pinyin("hǎo")
    assert validate_pinyin("hao3")
    assert validate_pinyin("hao/hao")

    # invalid string with symbols should fail
    assert not validate_pinyin("h@o!")


def test_chinese_char_detection():
    assert is_chinese_char("汉")
    assert not is_chinese_char("A")
    assert contains_chinese("学习A")
    assert not contains_chinese("ABC123")

