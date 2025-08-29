"""
Unit tests for services/preview_types.py
Tests dataclass creation, validation, and conversion functions.
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from services.preview_types import (
    LayoutOptions, Typography, VisualOptions, PreviewParams,
    convert_app_config_to_preview_params, convert_legacy_params_to_preview_params,
    validate_preview_params, extract_legacy_params
)


class TestLayoutOptions:
    """Test LayoutOptions dataclass."""
    
    def test_layout_options_creation(self):
        """Test basic LayoutOptions creation."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        assert layout.rows == 2
        assert layout.cols == 3
        assert layout.auto_fill is True
        assert layout.card_size_cm == 5.5
        assert layout.gap_cm == 0.5
        assert layout.margin_cm == 1.0
        assert layout.page_size == 'A4'
    
    def test_layout_options_validation(self):
        """Test LayoutOptions validation."""
        # Test negative rows
        with pytest.raises(ValueError, match="Rows and cols must be positive"):
            LayoutOptions(
                rows=-1, cols=3, auto_fill=True,
                card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                page_size='A4'
            )
        
        # Test negative card size
        with pytest.raises(ValueError, match="Card size must be positive"):
            LayoutOptions(
                rows=2, cols=3, auto_fill=True,
                card_size_cm=-1.0, gap_cm=0.5, margin_cm=1.0,
                page_size='A4'
            )
        
        # Test negative gap
        with pytest.raises(ValueError, match="Gap and margin must be non-negative"):
            LayoutOptions(
                rows=2, cols=3, auto_fill=True,
                card_size_cm=5.5, gap_cm=-0.1, margin_cm=1.0,
                page_size='A4'
            )
    
    def test_layout_options_float_normalization(self):
        """Test float normalization for stable hashing."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.123456789, gap_cm=0.567891234, margin_cm=1.987654321,
            page_size='A4'
        )
        
        # Should be rounded to 4 decimal places
        assert layout.card_size_cm == 5.1235
        assert layout.gap_cm == 0.5679
        assert layout.margin_cm == 1.9877
    
    def test_layout_options_from_layout_config(self):
        """Test creation from LayoutConfig."""
        # Create a simple object instead of MagicMock to avoid getattr issues
        class MockConfig:
            def __init__(self):
                self.rows = 3
                self.cols = 4
                self.auto_fill = False
                self.card_size = 6.0
                self.gap = 0.8
                self.margin = 1.5
                self.page_size = 'Letter'

        mock_config = MockConfig()
        layout = LayoutOptions.from_layout_config(mock_config)

        assert layout.rows == 3
        assert layout.cols == 4
        assert layout.auto_fill is False
        assert layout.card_size_cm == 6.0
        assert layout.gap_cm == 0.8
        assert layout.margin_cm == 1.5
        assert layout.page_size == 'Letter'
    
    def test_layout_options_dict_conversion(self):
        """Test dictionary conversion."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        
        # Test to_dict
        data = layout.to_dict()
        expected = {
            'rows': 2, 'cols': 3, 'auto_fill': True,
            'card_size_cm': 5.5, 'gap_cm': 0.5, 'margin_cm': 1.0,
            'page_size': 'A4'
        }
        assert data == expected
        
        # Test from_dict
        layout2 = LayoutOptions.from_dict(data)
        assert layout2 == layout


class TestTypography:
    """Test Typography dataclass."""
    
    def test_typography_creation(self):
        """Test basic Typography creation."""
        typo = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font='SimHei'
        )
        
        assert typo.font_hanzi_pt == 48
        assert typo.font_pinyin_pt == 18
        assert typo.font_english_pt == 14
        assert typo.hanzi_font == 'SimHei'
    
    def test_typography_validation(self):
        """Test Typography validation."""
        # Test negative font size
        with pytest.raises(ValueError, match="Font sizes must be positive"):
            Typography(
                font_hanzi_pt=-1, font_pinyin_pt=18, font_english_pt=14,
                hanzi_font='SimHei'
            )
        
        # Test empty font name
        with pytest.raises(ValueError, match="Hanzi font must not be empty"):
            Typography(
                font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
                hanzi_font=''
            )
    
    def test_typography_from_configs(self):
        """Test creation from layout and UI configs."""
        mock_layout = MagicMock()
        mock_layout.font_hanzi = 50
        mock_layout.font_pinyin = 20
        mock_layout.font_english = 16
        
        mock_ui = MagicMock()
        mock_ui.hanzi_font = 'Arial'
        
        typo = Typography.from_configs(mock_layout, mock_ui)
        
        assert typo.font_hanzi_pt == 50
        assert typo.font_pinyin_pt == 20
        assert typo.font_english_pt == 16
        assert typo.hanzi_font == 'Arial'


class TestVisualOptions:
    """Test VisualOptions dataclass."""
    
    def test_visual_options_creation(self):
        """Test basic VisualOptions creation."""
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        assert visual.background_color == '#ffffff'
        assert visual.preview_mode == '📄 完整页面'
    
    def test_visual_options_validation(self):
        """Test VisualOptions validation."""
        # Test empty background color
        with pytest.raises(ValueError, match="Background color must not be empty"):
            VisualOptions(background_color='', preview_mode='📄 完整页面')
        
        # Test invalid preview mode
        with pytest.raises(ValueError, match="Invalid preview mode"):
            VisualOptions(background_color='#ffffff', preview_mode='invalid')
    
    def test_visual_options_from_ui_config(self):
        """Test creation from UIConfig."""
        mock_ui = MagicMock()
        mock_ui.background_color = '#ff0000'
        mock_ui.preview_mode = '🔲 简单网格'
        
        visual = VisualOptions.from_ui_config(mock_ui)
        
        assert visual.background_color == '#ff0000'
        assert visual.preview_mode == '🔲 简单网格'


class TestPreviewParams:
    """Test PreviewParams dataclass."""
    
    def test_preview_params_creation(self):
        """Test PreviewParams creation."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font='SimHei'
        )
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        assert params.layout == layout
        assert params.typography == typography
        assert params.visual == visual
    
    def test_preview_params_from_app_config(self):
        """Test creation from AppConfig."""
        # Create simple objects instead of MagicMock
        class MockLayoutConfig:
            def __init__(self):
                self.rows = 2
                self.cols = 3
                self.auto_fill = True
                self.card_size = 5.5
                self.gap = 0.5
                self.margin = 1.0
                self.page_size = 'A4'
                self.font_hanzi = 48
                self.font_pinyin = 18
                self.font_english = 14

        class MockUIConfig:
            def __init__(self):
                self.hanzi_font = 'SimHei'
                self.background_color = '#ffffff'
                self.preview_mode = '📄 完整页面'

        class MockAppConfig:
            def __init__(self):
                self.layout = MockLayoutConfig()
                self.ui = MockUIConfig()

        mock_app_config = MockAppConfig()
        params = PreviewParams.from_app_config(mock_app_config)

        assert params.layout.rows == 2
        assert params.layout.cols == 3
        assert params.typography.font_hanzi_pt == 48
        assert params.visual.background_color == '#ffffff'
    
    def test_preview_params_json_conversion(self):
        """Test JSON serialization and deserialization."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font='SimHei'
        )
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        # Test to_json
        json_str = params.to_json()
        assert isinstance(json_str, str)
        
        # Test from_json
        params2 = PreviewParams.from_json(json_str)
        assert params2 == params


class TestConversionFunctions:
    """Test conversion utility functions."""
    
    def test_convert_legacy_params_to_preview_params(self):
        """Test legacy parameter conversion."""
        params = convert_legacy_params_to_preview_params(
            card_size=5.5, gap=0.5, margin=1.0, page_size='A4',
            font_hanzi=48, font_pinyin=18, font_english=14,
            hanzi_font='SimHei', background_color='#ffffff',
            preview_mode='📄 完整页面', rows=2, cols=3, auto_fill=True
        )
        
        assert params.layout.card_size_cm == 5.5
        assert params.layout.gap_cm == 0.5
        assert params.typography.font_hanzi_pt == 48
        assert params.visual.background_color == '#ffffff'
    
    def test_extract_legacy_params(self):
        """Test legacy parameter extraction."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font='SimHei'
        )
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        legacy = extract_legacy_params(params)
        
        expected = {
            'card_size': 5.5, 'gap': 0.5, 'margin': 1.0, 'page_size': 'A4',
            'font_hanzi': 48, 'font_pinyin': 18, 'font_english': 14,
            'hanzi_font': 'SimHei', 'background_color': '#ffffff',
            'preview_mode': '📄 完整页面', 'rows': 2, 'cols': 3, 'auto_fill': True
        }
        
        assert legacy == expected
    
    def test_validate_preview_params(self):
        """Test preview params validation."""
        layout = LayoutOptions(
            rows=2, cols=3, auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )
        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font='SimHei'
        )
        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )
        
        params = PreviewParams(layout=layout, typography=typography, visual=visual)
        
        # Should not raise any exceptions
        validated = validate_preview_params(params)
        assert validated == params
