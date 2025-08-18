"""
Tests for configuration objects in core/config.py
"""

import pytest
from core.config import UIConfig, LayoutConfig, AppConfig, create_config_from_params


class TestUIConfig:
    """Test UIConfig data class."""
    
    def test_default_creation(self):
        """Test creating UIConfig with default values."""
        config = UIConfig()
        assert config.hanzi_font == 'SimHei'
        assert config.background_color == '#ffffff'
        assert config.preview_mode == '📄 完整页面'
    
    def test_custom_creation(self):
        """Test creating UIConfig with custom values."""
        config = UIConfig(
            hanzi_font='Arial',
            background_color='#f0f0f0',
            preview_mode='🔲 简单网格'
        )
        assert config.hanzi_font == 'Arial'
        assert config.background_color == '#f0f0f0'
        assert config.preview_mode == '🔲 简单网格'
    
    def test_from_dict(self):
        """Test creating UIConfig from dictionary."""
        data = {
            'hanzi_font': 'KaiTi',
            'background_color': '#e0e0e0',
            'preview_mode': '📄 完整页面'
        }
        config = UIConfig.from_dict(data)
        assert config.hanzi_font == 'KaiTi'
        assert config.background_color == '#e0e0e0'
        assert config.preview_mode == '📄 完整页面'
    
    def test_from_dict_with_missing_keys(self):
        """Test creating UIConfig from incomplete dictionary."""
        data = {'hanzi_font': 'KaiTi'}
        config = UIConfig.from_dict(data)
        assert config.hanzi_font == 'KaiTi'
        assert config.background_color == '#ffffff'  # default
        assert config.preview_mode == '📄 完整页面'  # default
    
    def test_to_dict(self):
        """Test converting UIConfig to dictionary."""
        config = UIConfig(hanzi_font='Arial', background_color='#f0f0f0')
        result = config.to_dict()
        expected = {
            'hanzi_font': 'Arial',
            'background_color': '#f0f0f0',
            'preview_mode': '📄 完整页面'
        }
        assert result == expected


class TestLayoutConfig:
    """Test LayoutConfig data class."""
    
    def test_default_creation(self):
        """Test creating LayoutConfig with default values."""
        config = LayoutConfig()
        assert config.card_size == 5.5
        assert config.gap == 0.5
        assert config.margin == 1.0
        assert config.font_hanzi == 48
        assert config.font_pinyin == 18
        assert config.font_english == 14
        assert config.page_size == 'A4'
        assert config.rows == 2
        assert config.cols == 3
        assert config.auto_fill is True
    
    def test_custom_creation(self):
        """Test creating LayoutConfig with custom values."""
        config = LayoutConfig(
            card_size=6.0,
            gap=0.8,
            margin=1.5,
            font_hanzi=52,
            rows=3,
            cols=4,
            auto_fill=False
        )
        assert config.card_size == 6.0
        assert config.gap == 0.8
        assert config.margin == 1.5
        assert config.font_hanzi == 52
        assert config.rows == 3
        assert config.cols == 4
        assert config.auto_fill is False
    
    def test_from_dict_with_type_conversion(self):
        """Test creating LayoutConfig from dictionary with type conversion."""
        data = {
            'card_size': '6.5',  # string should be converted to float
            'gap': '0.7',
            'font_hanzi': '50',  # string should be converted to int
            'rows': '4',
            'auto_fill': 'True'  # string should be converted to bool
        }
        config = LayoutConfig.from_dict(data)
        assert config.card_size == 6.5
        assert config.gap == 0.7
        assert config.font_hanzi == 50
        assert config.rows == 4
        assert config.auto_fill is True
    
    def test_to_dict(self):
        """Test converting LayoutConfig to dictionary."""
        config = LayoutConfig(card_size=6.0, rows=4, cols=5)
        result = config.to_dict()
        assert result['card_size'] == 6.0
        assert result['rows'] == 4
        assert result['cols'] == 5
        assert 'gap' in result
        assert 'margin' in result


class TestAppConfig:
    """Test AppConfig combined configuration."""
    
    def test_default_creation(self):
        """Test creating AppConfig with default values."""
        config = AppConfig.default()
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.layout, LayoutConfig)
        assert config.ui.hanzi_font == 'SimHei'
        assert config.layout.card_size == 5.5
    
    def test_from_dicts(self):
        """Test creating AppConfig from separate dictionaries."""
        ui_data = {'hanzi_font': 'Arial', 'background_color': '#f0f0f0'}
        layout_data = {'card_size': 6.0, 'rows': 4}
        
        config = AppConfig.from_dicts(ui_data, layout_data)
        assert config.ui.hanzi_font == 'Arial'
        assert config.ui.background_color == '#f0f0f0'
        assert config.layout.card_size == 6.0
        assert config.layout.rows == 4
    
    def test_to_dicts(self):
        """Test converting AppConfig to separate dictionaries."""
        config = AppConfig.default()
        ui_dict, layout_dict = config.to_dicts()
        
        assert isinstance(ui_dict, dict)
        assert isinstance(layout_dict, dict)
        assert 'hanzi_font' in ui_dict
        assert 'card_size' in layout_dict


class TestCreateConfigFromParams:
    """Test the migration function for creating config from individual parameters."""
    
    def test_create_config_from_params(self):
        """Test creating AppConfig from individual parameters."""
        config = create_config_from_params(
            card_size=6.0,
            gap=0.8,
            margin=1.5,
            page_size='A3',
            font_hanzi=50,
            font_pinyin=20,
            font_english=16,
            hanzi_font='Arial',
            background_color='#f0f0f0',
            preview_mode='🔲 简单网格',
            rows=4,
            cols=5,
            auto_fill=False
        )
        
        # Check UI config
        assert config.ui.hanzi_font == 'Arial'
        assert config.ui.background_color == '#f0f0f0'
        assert config.ui.preview_mode == '🔲 简单网格'
        
        # Check layout config
        assert config.layout.card_size == 6.0
        assert config.layout.gap == 0.8
        assert config.layout.margin == 1.5
        assert config.layout.page_size == 'A3'
        assert config.layout.font_hanzi == 50
        assert config.layout.font_pinyin == 20
        assert config.layout.font_english == 16
        assert config.layout.rows == 4
        assert config.layout.cols == 5
        assert config.layout.auto_fill is False


if __name__ == '__main__':
    pytest.main([__file__])
