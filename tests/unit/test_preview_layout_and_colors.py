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

