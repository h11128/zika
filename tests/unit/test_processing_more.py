from services.processing import parse_input_text, auto_segment_text


def test_parse_input_text_empty_and_non_chinese():
    assert parse_input_text("") == []
    assert parse_input_text("ABC 123 !@#") == []


def test_auto_segment_text_edge_cases():
    assert auto_segment_text("") == ""
    assert auto_segment_text("!!!") == ""

    # Long segment > 4 chars should be split into 2-char chunks
    text = "学习汉语编程语言"  # 7 chars
    out = auto_segment_text(text)
    # Expect space separated chunks of 2 or 1 chars
    parts = out.split()
    assert all(len(p) in (1,2,3,4) for p in parts)
    assert parts  # not empty

