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
        assert config.hanzi_font_family == 'SimHei'
        assert config.background_color == '#ffffff'
        assert config.preview_mode == '📄 完整页面'
    
    def test_custom_creation(self):
        """Test creating UIConfig with custom values."""
        config = UIConfig(
            hanzi_font_family='Arial',
            background_color='#f0f0f0',
            preview_mode='🔲 简单网格'
        )
        assert config.hanzi_font_family == 'Arial'
        assert config.background_color == '#f0f0f0'
        assert config.preview_mode == '🔲 简单网格'
    
    def test_from_dict(self):
        """Test creating UIConfig from dictionary."""
        data = {
            'hanzi_font_family': 'KaiTi',
            'background_color': '#e0e0e0',
            'preview_mode': '📄 完整页面'
        }
        config = UIConfig.from_dict(data)
        assert config.hanzi_font_family == 'KaiTi'
        assert config.background_color == '#e0e0e0'
        assert config.preview_mode == '📄 完整页面'
    
    def test_from_dict_with_missing_keys(self):
        """Test creating UIConfig from incomplete dictionary."""
        data = {'hanzi_font_family': 'KaiTi'}
        config = UIConfig.from_dict(data)
        assert config.hanzi_font_family == 'KaiTi'
        assert config.background_color == '#ffffff'  # default
        assert config.preview_mode == '📄 完整页面'  # default
    
    def test_to_dict(self):
        """Test converting UIConfig to dictionary."""
        config = UIConfig(hanzi_font_family='Arial', background_color='#f0f0f0')
        result = config.to_dict()
        expected = {
            'hanzi_font_family': 'Arial',
            'background_color': '#f0f0f0',
            'preview_mode': '📄 完整页面'
        }
        assert result == expected


class TestLayoutConfig:
    """Test LayoutConfig data class."""
    
    def test_default_creation(self):
        """Test creating LayoutConfig with default values."""
        config = LayoutConfig()
        assert config.card_size_cm == 5.5
        assert config.gap_cm == 0.5
        assert config.margin_cm == 1.0
        assert config.hanzi_font_size == 48
        assert config.pinyin_font_size == 18
        assert config.english_font_size == 14
        assert config.page_size == 'A4'
        assert config.layout_rows == 2
        assert config.layout_cols == 3
        assert config.layout_auto_fill is True
    
    def test_custom_creation(self):
        """Test creating LayoutConfig with custom values."""
        config = LayoutConfig(
            card_size_cm=6.0,
            gap_cm=0.8,
            margin_cm=1.5,
            hanzi_font_size=52,
            layout_rows=3,
            layout_cols=4,
            layout_auto_fill=False
        )
        assert config.card_size_cm == 6.0
        assert config.gap_cm == 0.8
        assert config.margin_cm == 1.5
        assert config.hanzi_font_size == 52
        assert config.layout_rows == 3
        assert config.layout_cols == 4
        assert config.layout_auto_fill is False
    
    def test_from_dict_with_type_conversion(self):
        """Test creating LayoutConfig from dictionary with type conversion."""
        data = {
            'card_size_cm': '6.5',  # string should be converted to float
            'gap_cm': '0.7',
            'hanzi_font_size': '50',  # string should be converted to int
            'layout_rows': '4',
            'layout_auto_fill': 'True'  # string should be converted to bool
        }
        config = LayoutConfig.from_dict(data)
        assert config.card_size_cm == 6.5
        assert config.gap_cm == 0.7
        assert config.hanzi_font_size == 50
        assert config.layout_rows == 4
        assert config.layout_auto_fill is True
    
    def test_to_dict(self):
        """Test converting LayoutConfig to dictionary."""
        config = LayoutConfig(card_size_cm=6.0, layout_rows=4, layout_cols=5)
        result = config.to_dict()
        assert result['card_size_cm'] == 6.0
        assert result['layout_rows'] == 4
        assert result['layout_cols'] == 5
        assert 'gap_cm' in result
        assert 'margin_cm' in result


class TestAppConfig:
    """Test AppConfig combined configuration."""
    
    def test_default_creation(self):
        """Test creating AppConfig with default values."""
        config = AppConfig.default()
        assert isinstance(config.ui, UIConfig)
        assert isinstance(config.layout, LayoutConfig)
        assert config.ui.hanzi_font_family == 'SimHei'
        assert config.layout.card_size_cm == 5.5
    
    def test_from_dicts(self):
        """Test creating AppConfig from separate dictionaries."""
        ui_data = {'hanzi_font_family': 'Arial', 'background_color': '#f0f0f0'}
        layout_data = {'card_size_cm': 6.0, 'layout_rows': 4}
        
        config = AppConfig.from_dicts(ui_data, layout_data)
        assert config.ui.hanzi_font_family == 'Arial'
        assert config.ui.background_color == '#f0f0f0'
        assert config.layout.card_size_cm == 6.0
        assert config.layout.layout_rows == 4
    
    def test_to_dicts(self):
        """Test converting AppConfig to separate dictionaries."""
        config = AppConfig.default()
        ui_dict, layout_dict = config.to_dicts()
        
        assert isinstance(ui_dict, dict)
        assert isinstance(layout_dict, dict)
        assert 'hanzi_font_family' in ui_dict
        assert 'card_size_cm' in layout_dict


class TestCreateConfigFromParams:
    """Test the migration function for creating config from individual parameters."""
    
    def test_create_config_from_params(self):
        """Test creating AppConfig from individual parameters."""
        config = create_config_from_params(
            card_size_cm=6.0,
            gap_cm=0.8,
            margin_cm=1.5,
            page_size='A3',
            hanzi_font_size=50,
            pinyin_font_size=20,
            english_font_size=16,
            hanzi_font_family='Arial',
            background_color='#f0f0f0',
            preview_mode='🔲 简单网格',
            layout_rows=4,
            layout_cols=5,
            layout_auto_fill=False
        )
        
        # Check UI config
        assert config.ui.hanzi_font_family == 'Arial'
        assert config.ui.background_color == '#f0f0f0'
        assert config.ui.preview_mode == '🔲 简单网格'
        
        # Check layout config
        assert config.layout.card_size_cm == 6.0
        assert config.layout.gap_cm == 0.8
        assert config.layout.margin_cm == 1.5
        assert config.layout.page_size == 'A3'
        assert config.layout.hanzi_font_size == 50
        assert config.layout.pinyin_font_size == 20
        assert config.layout.english_font_size == 16
        assert config.layout.layout_rows == 4
        assert config.layout.layout_cols == 5
        assert config.layout.layout_auto_fill is False


if __name__ == '__main__':
    pytest.main([__file__])
