import os
import io
import pytest

from services.export import export_cards
from services import cache as preview_cache

SAMPLE_CARDS = [
    {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
    {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
    {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
]


def test_export_pptx_and_pdf_bytes():
    for fmt in ['pptx', 'pdf']:
        content = export_cards(SAMPLE_CARDS, fmt, page_size='A4', card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0)
        assert isinstance(content, (bytes, bytearray)) and len(content) > 0


def test_export_unsupported_format_raises():
    with pytest.raises(ValueError):
        export_cards(SAMPLE_CARDS, 'docx')


def test_preview_html_contains_expected_bits():
    color = '#E3F2FD'
    simple_html = preview_cache.create_simple_grid_html(SAMPLE_CARDS, hanzi_font_family='Microsoft YaHei', background_color=color)
    assert color in simple_html
    assert 'simple-card' in simple_html

    page_html = preview_cache.create_page_preview_html(
        SAMPLE_CARDS, page_num=0,
        card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
        hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
        page_size='A4', hanzi_font_family='Microsoft YaHei', background_color=color,
        layout_rows=3, layout_cols=3, layout_auto_fill=True
    )
    assert color in page_html
    assert 'page-card' in page_html

