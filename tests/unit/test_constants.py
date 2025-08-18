import pytest

from core import constants as C

def test_defaults_basic():
    assert C.DEFAULT_ROWS >= 1
    assert C.DEFAULT_COLS >= 1
    assert isinstance(C.DEFAULT_AUTO_FILL, bool)
    assert C.DEFAULT_PAGE_SIZE in {"A4", "Letter", "LETTER"}
    assert 3.0 <= C.DEFAULT_CARD_SIZE <= 10.0
    assert 0.0 <= C.DEFAULT_GAP <= 5.0
    assert 0.0 <= C.DEFAULT_MARGIN <= 5.0


def test_preset_colors_and_fonts():
    # preset colors should be hex and length 7
    for color in C.PRESET_COLORS:
        assert isinstance(color, str) and color.startswith('#') and len(color) == 7
        int(color[1:], 16)  # should parse as hex without raising

    # fonts should be non-empty strings
    for f in C.HANZI_FONT_OPTIONS:
        assert isinstance(f, str) and f.strip()

