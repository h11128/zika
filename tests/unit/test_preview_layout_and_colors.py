"""
预览与布局/颜色相关的综合测试
- 字体大小一致性
- 简单网格响应式布局
- 自定义颜色应用与一致性
"""

import re
import pytest
from services.cache import (
    create_page_preview_html,
    create_simple_grid_html_immediate,
)


class TestPreviewFontAndColorConsistency:
    def test_preview_font_size_calculation_without_scale_factor(self):
        test_cards = [
            {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
            {'hanzi': '世界', 'pinyin': 'shì jiè', 'english': 'world'}
        ]
        hanzi_font = 'SimHei'
        background_color = '#ffffff'
        rows, cols = 2, 1
        font_hanzi, font_pinyin, font_english = 48, 18, 14
        card_size, auto_fill = 5.5, False

        html = create_page_preview_html(
            test_cards, 0, card_size, 0.5, 1.0,
            font_hanzi, font_pinyin, font_english, 'A4', hanzi_font,
            background_color, rows, cols, auto_fill
        )

        hanzi_font_pattern = r'\.page-hanzi[^}]*font-size:\s*(\d+(?:\.\d+)?)px'
        hanzi_matches = re.findall(hanzi_font_pattern, html)
        assert len(hanzi_matches) > 0
        actual_hanzi_size = float(hanzi_matches[0])
        # 期望 = pt → px (96/72) × 页面缩放(scale_factor)
        # scale_factor 在预览中约为 600 / page_width_px（A4≈793.8px），此处只校验比例常数 96/72
        pt_to_px = 96/72
        expected_min = font_hanzi * pt_to_px * 0.6  # 下界（考虑页缩放）
        expected_max = font_hanzi * pt_to_px * 1.0  # 上界
        assert expected_min <= actual_hanzi_size <= expected_max

    def test_color_consistency_across_preview_modes(self):
        test_cards = [{'hanzi': '一致', 'pinyin': 'yī zhì', 'english': 'consistent'}]
        custom_color = '#0000ff'
        page_html = create_page_preview_html(
            test_cards, 0, 5.5, 0.5, 1.0,
            48, 18, 14, 'A4', 'SimHei',
            custom_color, 1, 1, False
        )
        grid_html = create_simple_grid_html_immediate(
            test_cards, 'SimHei', custom_color, 1, 1,
            48, 18, 14, 5.5, False
        )
        assert custom_color.lower() in page_html.lower()
        assert custom_color.lower() in grid_html.lower()

    def test_simple_grid_font_size_matches_pt_to_px(self):
        test_cards = [{'hanzi': '测', 'pinyin': 'cè', 'english': 'test'}]
        html = create_simple_grid_html_immediate(
            test_cards, 'SimHei', '#ffffff', 1, 1,
            48, 18, 14, 5.5, False
        )
        import re
        size_hanzi = float(re.findall(r'\.simple-hanzi[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        size_pinyin = float(re.findall(r'\.simple-pinyin[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        size_en = float(re.findall(r'\.simple-english[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        pt_to_px = 96/72
        assert abs(size_hanzi - 48*pt_to_px) < 0.5
        assert abs(size_pinyin - 18*pt_to_px) < 0.5
        assert abs(size_en - 14*pt_to_px) < 0.5


    def test_simple_grid_font_size_matches_pt_to_px_for_custom_values(self):
        # Verify non-default sizes 26/12/14 are converted properly in simple grid
        test_cards = [{'hanzi': '字', 'pinyin': 'zì', 'english': 'zi'}]
        html = create_simple_grid_html_immediate(
            test_cards, 'SimHei', '#ffffff', 1, 1,
            26, 12, 14, 5.5, False
        )
        size_hanzi = float(re.findall(r'\.simple-hanzi[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        size_pinyin = float(re.findall(r'\.simple-pinyin[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        size_en = float(re.findall(r'\.simple-english[^}]*font-size:\s*(\d+(?:\.\d+)?)px', html)[0])
        pt_to_px = 96/72
        assert abs(size_hanzi - 26*pt_to_px) < 0.5
        assert abs(size_pinyin - 12*pt_to_px) < 0.5
        assert abs(size_en - 14*pt_to_px) < 0.5


class TestSimpleGridResponsiveLayout:
    def test_simple_grid_responsive_columns(self):
        test_cards = [{'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'word{i}'} for i in range(12)]
        rows, cols = 2, 6
        card_size, auto_fill = 6.0, False
        html = create_simple_grid_html_immediate(
            test_cards, 'SimHei', '#ffffff', rows, cols,
            48, 18, 14, card_size, auto_fill
        )
        responsive_patterns = [
            r'grid-template-columns:\s*repeat\(auto-fit',
            r'grid-template-columns:\s*repeat\(auto-fill',
            r'minmax\(', r'min\(', r'max\('
        ]
        assert any(re.search(p, html) for p in responsive_patterns)

    def test_simple_grid_container_constraints(self):
        test_cards = [{'hanzi': f'字{i}', 'pinyin': f'zì{i}', 'english': f'word{i}'} for i in range(40)]
        rows, cols = 5, 8
        html = create_simple_grid_html_immediate(
            test_cards, 'SimHei', '#ffffff', rows, cols,
            48, 18, 14, 5.5, False
        )
        container_patterns = [r'max-width:\s*(\d+)px', r'width:\s*100%', r'overflow:\s*hidden', r'overflow-x:\s*auto']
        assert any(re.search(p, html) for p in container_patterns)


# Additional coverage tests for layout_pdf.py
def test_pdf_card_generator_unsupported_page_size():
    """Test that unsupported page size raises ValueError."""
    from src.layout_pdf import PDFCardGenerator
    with pytest.raises(ValueError, match="Unsupported page size"):
        PDFCardGenerator(
            page_size="INVALID",
            card_size_cm=5.5,
            gap_cm=0.5,
            margin_cm=1.0,
            rows=2,
            cols=3,
            auto_fill=False
        )


def test_pdf_card_generator_manual_card_size():
    """Test manual card size calculation (auto_fill=False)."""
    from src.layout_pdf import PDFCardGenerator
    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=6.0,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=3,
        auto_fill=False
    )
    # Should use manual card size
    expected_size = 6.0 * 28.35  # cm to points conversion
    assert abs(generator.card_size - expected_size) < 1.0


def test_pdf_card_generator_letter_page_size():
    """Test Letter page size initialization."""
    from src.layout_pdf import PDFCardGenerator
    from reportlab.lib.pagesizes import letter

    generator = PDFCardGenerator(
        page_size="LETTER",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=3,
        auto_fill=True
    )

    # Letter size is different from A4
    assert generator.page_width == letter[0]
    assert generator.page_height == letter[1]


def test_pdf_card_generator_zero_rows_cols():
    """Test handling of zero rows or cols in auto_fill mode."""
    from src.layout_pdf import PDFCardGenerator

    # Test with zero cols
    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=0,  # Zero cols
        auto_fill=True
    )
    assert generator.card_size >= 0

    # Test with zero rows
    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=0,  # Zero rows
        cols=3,
        auto_fill=True
    )
    assert generator.card_size >= 0


# Additional high-priority tests for src/layout_pdf.py core business logic
def test_pdf_card_generator_grid_scaling():
    """Test grid scaling when cards exceed page bounds."""
    from src.layout_pdf import PDFCardGenerator

    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=15.0,  # Very large cards that will exceed bounds
        gap_cm=2.0,
        margin_cm=1.0,
        rows=3,
        cols=3,
        auto_fill=False
    )

    # Grid should be scaled down to fit within page bounds
    assert generator.card_size < 15.0 * 28.35  # Should be smaller than original
    # The grid scaling should ensure it fits within available space
    available_width = generator.page_width - 2 * generator.margin
    available_height = generator.page_height - 2 * generator.margin
    # Just check that scaling occurred (card size was reduced)
    assert generator.card_size < 15.0 * 28.35


def test_pdf_card_generator_font_registration_paths():
    """Test font registration with different font paths and types."""
    from src.layout_pdf import PDFCardGenerator
    from unittest.mock import patch

    with patch('src.layout_pdf.os.path.exists') as mock_exists, \
         patch('src.layout_pdf.pdfmetrics.registerFont') as mock_register:

        # Test successful font registration
        mock_exists.return_value = True
        mock_register.return_value = None

        generator = PDFCardGenerator(
            page_size="A4",
            card_size_cm=5.5,
            gap_cm=0.5,
            margin_cm=1.0,
            rows=2,
            cols=3,
            auto_fill=True
        )

        # Should attempt to register fonts (the method tries multiple font paths)
        assert mock_register.call_count >= 1
        # Should have font names set (either registered or fallback)
        assert generator.chinese_font is not None
        assert generator.pinyin_font is not None


def test_pdf_card_generator_draw_card_text():
    """Test card text drawing functionality."""
    from src.layout_pdf import PDFCardGenerator
    from unittest.mock import MagicMock, patch

    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=3,
        auto_fill=True
    )

    # Mock canvas
    mock_canvas = MagicMock()
    mock_canvas.stringWidth.return_value = 50

    # Test card with all fields
    card = {
        'hanzi': '你好',
        'pinyin': 'ni3 hao3',
        'english': 'hello'
    }

    # This should not raise an error and should draw all text elements
    generator._draw_card_text(mock_canvas, card, 100, 100, 48, 18, 14)

    # Should have called drawString for each text element
    assert mock_canvas.drawString.call_count >= 3  # At least hanzi, pinyin, english


def test_pdf_card_generator_add_single_card():
    """Test adding a single card with all text elements."""
    from src.layout_pdf import PDFCardGenerator
    from unittest.mock import MagicMock, patch

    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=3,
        auto_fill=True
    )

    # Mock canvas
    mock_canvas = MagicMock()
    mock_canvas.stringWidth.return_value = 50

    # Test card with all fields
    card = {
        'hanzi': '你好',
        'pinyin': 'ni3 hao3',
        'english': 'hello'
    }

    # Should not raise an error - test the border and text drawing methods separately
    generator._draw_card_border(mock_canvas, 0, 0)
    generator._draw_card_text(mock_canvas, card, 0, 0, 48, 18, 14)

    # Should have drawn border and text
    assert mock_canvas.rect.called  # Border
    assert mock_canvas.drawString.call_count >= 3  # At least hanzi, pinyin, english


def test_pdf_card_generator_empty_text_handling():
    """Test handling of empty text fields in cards."""
    from src.layout_pdf import PDFCardGenerator
    from unittest.mock import MagicMock

    generator = PDFCardGenerator(
        page_size="A4",
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        rows=2,
        cols=3,
        auto_fill=True
    )

    # Mock canvas
    mock_canvas = MagicMock()
    mock_canvas.stringWidth.return_value = 50

    # Test card with empty fields
    card = {
        'hanzi': '你好',
        'pinyin': '',  # Empty pinyin
        'english': ''  # Empty english
    }

    # Should handle empty fields gracefully without errors
    generator._draw_card_text(mock_canvas, card, 0, 0, 48, 18, 14)

    # Should still draw hanzi (at least one drawString call)
    assert mock_canvas.drawString.called


def test_pdf_card_generator_font_fallback():
    """Test font fallback when no specific fonts are found."""
    from src.layout_pdf import PDFCardGenerator
    from unittest.mock import patch

    with patch('src.layout_pdf.os.path.exists') as mock_exists:
        mock_exists.return_value = False  # No fonts found

        generator = PDFCardGenerator(
            page_size="A4",
            card_size_cm=5.5,
            gap_cm=0.5,
            margin_cm=1.0,
            rows=2,
            cols=3,
            auto_fill=True
        )

        # Should fall back to default fonts
        assert generator.chinese_font == "Helvetica"
        assert generator.pinyin_font == "Helvetica"

