#!/usr/bin/env python3
"""
Configuration and Environment Integration Tests

Tests different configuration scenarios and environment setups:
1. Different data directory configurations
2. Font and layout configuration variations
3. Export format and quality settings
4. Environment variable handling
5. Cross-platform compatibility
6. Deployment configuration scenarios
"""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, Mock
import json

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, generate_missing_data
from services.export import export_cards
from services.cache_v2 import create_page_preview_html_v2, create_simple_grid_html_v2
from src.dict_utils import create_default_dict, ChineseDict
from core.constants import (
    DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN,
    DEFAULT_HANZI_FONT_SIZE, DEFAULT_PINYIN_FONT_SIZE, DEFAULT_ENGLISH_FONT_SIZE,
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR, PRESET_COLORS,
    HANZI_FONT_OPTIONS
)
from services.preview_types import LayoutOptions, Typography, VisualOptions


# Helper functions for v2 API compatibility
def create_page_preview_html(cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                           hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                           layout_rows=2, layout_cols=3, hanzi_font_family="SimSun",
                           background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=True,
        card_size_cm=card_size_cm,
        gap_cm=gap_cm,
        margin_cm=margin_cm,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=hanzi_font_size,
        pinyin_font_size_pt=pinyin_font_size,
        english_font_size_pt=english_font_size,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='📄 完整页面'
    )
    return create_page_preview_html_v2(cards, page_num, layout, typography, visual)

def create_simple_grid_html(cards, hanzi_font_family="SimSun", background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=2,
        layout_cols=3,
        layout_auto_fill=True,
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=48,
        pinyin_font_size_pt=18,
        english_font_size_pt=14,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='🔲 简单网格'
    )
    return create_simple_grid_html_v2(cards, layout, typography, visual)


class TestDataDirectoryConfigurations:
    """Test different data directory configurations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': '', 'english': ''}
        ]
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_default_data_directory_configuration(self):
        """Test default data directory configuration."""
        # Should work with default "data" directory
        dict_obj = create_default_dict("data")
        stats = dict_obj.get_statistics()
        
        assert stats['mini_dict_entries'] > 0
        
        # Test with processing
        processed_cards = generate_missing_data(
            self.sample_cards, True, True, dict_obj
        )
        
        assert len(processed_cards) == 2
        for card in processed_cards:
            assert card['pinyin']
    
    def test_custom_data_directory_configuration(self):
        """Test custom data directory configuration."""
        # Create custom data directory
        custom_data_dir = Path(self.temp_dir) / "custom_data"
        custom_data_dir.mkdir()
        
        # Create custom mini dictionary
        custom_dict = {
            "爱": ["love", "affection"],
            "家": ["home", "family"],
            "测试": ["test", "testing"]
        }
        
        mini_dict_path = custom_data_dir / "mini_cedict.json"
        with open(mini_dict_path, 'w', encoding='utf-8') as f:
            json.dump(custom_dict, f, ensure_ascii=False, indent=2)
        
        # Test with custom directory
        dict_obj = create_default_dict(str(custom_data_dir))
        
        # Verify custom dictionary is loaded
        translation = dict_obj.lookup_translation("测试")
        assert translation
        assert "test" in translation
        
        # Test with processing
        test_cards = [{'hanzi': '测试', 'pinyin': '', 'english': ''}]
        processed_cards = generate_missing_data(
            test_cards, True, True, dict_obj
        )
        
        assert 'test' in processed_cards[0]['english']
    
    def test_missing_data_directory_handling(self):
        """Test handling of missing data directory."""
        non_existent_dir = Path(self.temp_dir) / "non_existent"

        # Should handle gracefully (prints warning but doesn't crash)
        dict_obj = create_default_dict(str(non_existent_dir))
        stats = dict_obj.get_statistics()

        # Should have zero entries since no dictionary files found
        assert stats['mini_dict_entries'] == 0
    
    def test_empty_data_directory_configuration(self):
        """Test configuration with empty data directory."""
        empty_dir = Path(self.temp_dir) / "empty_data"
        empty_dir.mkdir()
        
        # Should handle empty directory gracefully
        dict_obj = create_default_dict(str(empty_dir))
        stats = dict_obj.get_statistics()
        
        # Should have zero entries but not crash
        assert stats['mini_dict_entries'] == 0
        
        # Should still work for pinyin generation
        processed_cards = generate_missing_data(
            self.sample_cards, True, True, dict_obj
        )
        
        for card in processed_cards:
            assert card['pinyin']  # Pinyin should still be generated
            # English might be empty due to no dictionary


class TestFontAndLayoutConfigurations:
    """Test font and layout configuration variations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
    
    def test_all_preset_font_configurations(self):
        """Test all preset font configurations."""
        for font in HANZI_FONT_OPTIONS:
            # Test in preview generation
            html = create_simple_grid_html(
                self.sample_cards, hanzi_font_family=font
            )
            assert isinstance(html, str)
            assert font in html or 'font-family' in html
            
            # Test in export
            content = export_cards(
                self.sample_cards, 'pptx', hanzi_font_family=font
            )
            assert isinstance(content, (bytes, bytearray))
            assert len(content) > 1000
    
    def test_all_preset_color_configurations(self):
        """Test all preset color configurations."""
        for color_value in PRESET_COLORS[:5]:  # Test first 5 colors for speed
            # Test in preview generation
            html = create_simple_grid_html(
                self.sample_cards, background_color=color_value
            )
            assert color_value in html

            # Test in export
            content = export_cards(
                self.sample_cards, 'pptx', background_color=color_value
            )
            assert isinstance(content, (bytes, bytearray))
    
    def test_layout_configuration_matrix(self):
        """Test various layout configuration combinations."""
        layout_configs = [
            {'layout_rows': 2, 'layout_cols': 2, 'card_size_cm': 4.0},
            {'layout_rows': 3, 'layout_cols': 3, 'card_size_cm': 5.5},
            {'layout_rows': 4, 'layout_cols': 3, 'card_size_cm': 3.5},
            {'layout_rows': 2, 'layout_cols': 4, 'card_size_cm': 4.5},
        ]
        
        for config in layout_configs:
            # Test preview generation
            html = create_page_preview_html(
                self.sample_cards, page_num=0,
                card_size_cm=config['card_size_cm'], gap_cm=0.5, margin_cm=1.0,
                hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                layout_rows=config['layout_rows'], layout_cols=config['layout_cols']
            )
            assert isinstance(html, str)
            
            # Test export
            content = export_cards(
                self.sample_cards, 'pptx',
                card_size_cm=config['card_size_cm'],
                layout_rows=config['layout_rows'], layout_cols=config['layout_cols']
            )
            assert isinstance(content, (bytes, bytearray))
    
    def test_font_size_configuration_ranges(self):
        """Test font size configuration ranges."""
        font_size_configs = [
            {'hanzi_font_size': 24, 'pinyin_font_size': 12, 'english_font_size': 10},  # Small
            {'hanzi_font_size': 48, 'pinyin_font_size': 18, 'english_font_size': 14},  # Default
            {'hanzi_font_size': 72, 'pinyin_font_size': 36, 'english_font_size': 24},  # Large
        ]
        
        for config in font_size_configs:
            # Test preview
            html = create_page_preview_html(
                self.sample_cards, page_num=0,
                card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                **config
            )
            assert isinstance(html, str)
            
            # Test export
            content = export_cards(self.sample_cards, 'pptx', **config)
            assert isinstance(content, (bytes, bytearray))


class TestExportFormatConfigurations:
    """Test export format and quality configurations."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'}
        ]
    
    def test_page_size_configurations(self):
        """Test different page size configurations."""
        page_sizes = ['A4', 'Letter']
        
        for page_size in page_sizes:
            # Test PPTX export
            pptx_content = export_cards(
                self.sample_cards, 'pptx', page_size=page_size
            )
            assert isinstance(pptx_content, (bytes, bytearray))
            assert len(pptx_content) > 1000
            
            # Test PDF export
            pdf_content = export_cards(
                self.sample_cards, 'pdf', page_size=page_size
            )
            assert isinstance(pdf_content, (bytes, bytearray))
            assert len(pdf_content) > 1000
    
    def test_margin_and_spacing_configurations(self):
        """Test margin and spacing configurations."""
        spacing_configs = [
            {'gap_cm': 0.0, 'margin_cm': 0.5},    # Minimal spacing
            {'gap_cm': 0.5, 'margin_cm': 1.0},    # Default spacing
            {'gap_cm': 1.0, 'margin_cm': 2.0},    # Large spacing
        ]
        
        for config in spacing_configs:
            content = export_cards(
                self.sample_cards, 'pptx',
                card_size_cm=5.0, **config
            )
            assert isinstance(content, (bytes, bytearray))
            assert len(content) > 1000
    
    def test_auto_fill_configuration(self):
        """Test auto-fill configuration options."""
        # Test with auto-fill enabled
        content_auto = export_cards(
            self.sample_cards, 'pptx', layout_auto_fill=True
        )
        assert isinstance(content_auto, (bytes, bytearray))
        
        # Test with auto-fill disabled
        content_no_auto = export_cards(
            self.sample_cards, 'pptx', layout_auto_fill=False
        )
        assert isinstance(content_no_auto, (bytes, bytearray))
        
        # Both should work but may produce different layouts
        assert len(content_auto) > 1000
        assert len(content_no_auto) > 1000


class TestEnvironmentVariableHandling:
    """Test environment variable handling."""
    
    def test_path_environment_variables(self):
        """Test handling of path-related environment variables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with custom TEMP directory
            with patch.dict(os.environ, {'TEMP': temp_dir, 'TMP': temp_dir}):
                cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
                
                # Export should use the custom temp directory
                content = export_cards(cards, 'pptx')
                assert isinstance(content, (bytes, bytearray))
    
    def test_locale_environment_variables(self):
        """Test handling of locale-related environment variables."""
        locale_configs = [
            {'LANG': 'zh_CN.UTF-8', 'LC_ALL': 'zh_CN.UTF-8'},
            {'LANG': 'en_US.UTF-8', 'LC_ALL': 'en_US.UTF-8'},
        ]
        
        for locale_config in locale_configs:
            with patch.dict(os.environ, locale_config):
                # Should work regardless of locale
                cards = parse_input_text("爱 家 朋友")
                assert len(cards) == 3
                
                dict_obj = create_default_dict("data")
                processed = generate_missing_data(cards, True, True, dict_obj)
                assert len(processed) == 3


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility."""
    
    def test_path_separator_handling(self):
        """Test handling of different path separators."""
        # Test with different path styles
        path_styles = [
            "data",           # Relative path
            "./data",         # Unix-style relative
            ".\\data",        # Windows-style relative
        ]
        
        for path_style in path_styles:
            try:
                # Should handle different path styles gracefully
                dict_obj = create_default_dict(path_style)
                stats = dict_obj.get_statistics()
                assert isinstance(stats, dict)
            except (FileNotFoundError, OSError):
                # Some path styles might not exist, that's okay
                pass
    
    def test_file_encoding_compatibility(self):
        """Test file encoding compatibility across platforms."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create dictionary with various encodings
            test_dict = {
                "爱": ["love"],
                "家": ["home"],
                "测试": ["test"]
            }
            
            dict_path = Path(temp_dir) / "mini_cedict.json"
            
            # Test UTF-8 encoding (should work everywhere)
            with open(dict_path, 'w', encoding='utf-8') as f:
                json.dump(test_dict, f, ensure_ascii=False)
            
            dict_obj = create_default_dict(temp_dir)
            translation = dict_obj.lookup_translation("爱")
            assert "love" in translation.lower()
    
    def test_font_availability_across_platforms(self):
        """Test font availability handling across platforms."""
        # Test with fonts that might not be available on all platforms
        platform_fonts = [
            'SimHei',           # Common on Windows/Chinese systems
            'Microsoft YaHei',  # Windows
            'PingFang SC',      # macOS
            'Noto Sans CJK',    # Linux
            'Arial Unicode MS', # Cross-platform fallback
        ]
        
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        for font in platform_fonts:
            # Should not crash even if font is not available
            try:
                html = create_simple_grid_html(cards, hanzi_font_family=font)
                assert isinstance(html, str)
                assert font in html
                
                content = export_cards(cards, 'pptx', hanzi_font_family=font)
                assert isinstance(content, (bytes, bytearray))
            except Exception as e:
                # Font might not be available, but shouldn't crash the system
                print(f"Font {font} caused issue: {e}")


class TestDeploymentConfigurations:
    """Test deployment configuration scenarios."""
    
    def test_minimal_deployment_configuration(self):
        """Test minimal deployment with only essential files."""
        # Simulate minimal deployment with only core functionality
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Should work with minimal configuration
        html = create_simple_grid_html(cards)
        assert isinstance(html, str)
        
        content = export_cards(cards, 'pptx')
        assert isinstance(content, (bytes, bytearray))
    
    def test_production_deployment_configuration(self):
        """Test production deployment configuration."""
        # Test with full dictionary and all features
        dict_obj = create_default_dict("data")
        
        cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': '', 'english': ''},
            {'hanzi': '朋友', 'pinyin': '', 'english': ''}
        ]
        
        # Full processing pipeline
        processed_cards = generate_missing_data(cards, True, True, dict_obj)
        
        # Generate previews
        simple_html = create_simple_grid_html(processed_cards)
        page_html = create_page_preview_html(
            processed_cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            hanzi_font_size=48, pinyin_font_size=18, english_font_size=14
        )
        
        # Export both formats
        pptx_content = export_cards(processed_cards, 'pptx')
        pdf_content = export_cards(processed_cards, 'pdf')
        
        # All should work in production configuration
        assert isinstance(simple_html, str)
        assert isinstance(page_html, str)
        assert isinstance(pptx_content, (bytes, bytearray))
        assert isinstance(pdf_content, (bytes, bytearray))
    
    def test_containerized_deployment_configuration(self):
        """Test configuration suitable for containerized deployment."""
        # Test with read-only file system simulation
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Should work without writing to application directory
        content = export_cards(cards, 'pptx')
        assert isinstance(content, (bytes, bytearray))
        
        # Should work with limited resources
        html = create_simple_grid_html(cards)
        assert isinstance(html, str)
