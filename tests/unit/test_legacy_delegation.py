"""
Unit tests for legacy preview function delegation to v2 implementation.
Tests that legacy functions properly delegate to v2 and maintain backward compatibility.
"""

import pytest
import warnings
from unittest.mock import patch, MagicMock

from services.cache_v2 import (
    create_page_preview_html_v2,
    cached_create_page_preview_html_v2,
    create_simple_grid_html_v2,
    cached_create_simple_grid_html_v2
)
from services.cache_v2 import (
    create_page_preview_html_immediate,
    create_simple_grid_html_immediate
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

def cached_create_page_preview_html(cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                                  hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                                  layout_rows=2, layout_cols=3, hanzi_font_family="SimSun",
                                  background_color="#FFFFFF", **kwargs):
    """Cached compatibility wrapper for v2 API."""
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
    return cached_create_page_preview_html_v2(cards, page_num, layout, typography, visual)

def cached_create_simple_grid_html(cards, hanzi_font_family="SimSun", background_color="#FFFFFF", **kwargs):
    """Cached compatibility wrapper for v2 API."""
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
    return cached_create_simple_grid_html_v2(cards, layout, typography, visual)


class TestLegacyDelegation:
    """Test legacy preview functions delegate to v2 implementation."""
    
    def test_create_page_preview_html_delegation(self):
        """Test that create_page_preview_html delegates to v2 when enabled."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.create_page_preview_html_v2') as mock_v2, \
             patch('services.preview_types.convert_legacy_params_to_preview_params') as mock_convert:
            
            # Mock the conversion
            mock_params = MagicMock()
            mock_params.layout = MagicMock()
            mock_params.typography = MagicMock()
            mock_params.visual = MagicMock()
            mock_convert.return_value = mock_params
            
            # Mock v2 function
            mock_v2.return_value = '<html>v2 result</html>'
            
            # Test delegation
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = create_page_preview_html(
                    cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                    'A4', 'SimHei', '#ffffff', 3, 2, True
                )
                
                # Verify deprecation warning
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message)
            
            # Verify v2 was called
            assert mock_v2.called
            assert result == '<html>v2 result</html>'
            
            # Verify conversion was called with correct parameters
            mock_convert.assert_called_once_with(
                5.5, 0.5, 1.0, 'A4',
                48, 18, 14,
                'SimHei', '#ffffff', '📄 完整页面',
                3, 2, True
            )
    
    def test_create_page_preview_html_fallback(self):
        """Test that create_page_preview_html falls back to legacy when v2 fails."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.create_page_preview_html_v2', side_effect=Exception("V2 failed")), \
             patch('services.cache_v2._slice_cards_for_page') as mock_slice, \
             patch('services.cache_v2._compute_page_layout_metrics') as mock_metrics, \
             patch('services.cache_v2._compute_page_card_box') as mock_box, \
             patch('services.cache_v2._compute_font_px') as mock_font:
            
            # Mock legacy implementation components
            mock_slice.return_value = (4, cards)
            mock_metrics.return_value = MagicMock()
            mock_box.return_value = MagicMock()
            mock_font.return_value = MagicMock()
            
            # Mock Jinja2 template
            with patch('jinja2.Environment') as mock_env:
                mock_template = MagicMock()
                mock_template.render.return_value = '<html>legacy result</html>'
                mock_env.return_value.get_template.return_value = mock_template
                
                # Test fallback
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("always")
                    result = create_page_preview_html(
                        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                        'A4', 'SimHei', '#ffffff', 3, 2, True
                    )
                
                # Verify fallback was used
                assert result == '<html>legacy result</html>'
    
    def test_create_simple_grid_html_delegation(self):
        """Test that create_simple_grid_html delegates to v2 when enabled."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.create_simple_grid_html_v2') as mock_v2, \
             patch('services.preview_types.convert_legacy_params_to_preview_params') as mock_convert:
            
            # Mock the conversion
            mock_params = MagicMock()
            mock_params.layout = MagicMock()
            mock_params.typography = MagicMock()
            mock_params.visual = MagicMock()
            mock_convert.return_value = mock_params
            
            # Mock v2 function
            mock_v2.return_value = '<html>v2 grid result</html>'
            
            # Test delegation
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = create_simple_grid_html(
                    cards, 'SimHei', '#ffffff', 3, 2, 48, 18, 14, 5.5, True
                )
                
                # Verify deprecation warning
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message)
            
            # Verify v2 was called
            assert mock_v2.called
            assert result == '<html>v2 grid result</html>'
    
    def test_cached_functions_delegation(self):
        """Test that cached functions also delegate to v2."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.cached_create_page_preview_html_v2') as mock_v2, \
             patch('services.preview_types.convert_legacy_params_to_preview_params') as mock_convert:
            
            # Mock the conversion
            mock_params = MagicMock()
            mock_params.layout = MagicMock()
            mock_params.typography = MagicMock()
            mock_params.visual = MagicMock()
            mock_convert.return_value = mock_params
            
            # Mock v2 function
            mock_v2.return_value = '<html>cached v2 result</html>'
            
            # Test cached delegation
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = cached_create_page_preview_html(
                    cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                    'A4', 'SimHei', '#ffffff', 3, 2, True
                )
            
            # Verify v2 was called
            assert mock_v2.called
            assert result == '<html>cached v2 result</html>'
    
    def test_immediate_functions_delegation(self):
        """Test that immediate functions delegate through main functions."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('services.cache_v2.create_page_preview_html') as mock_main:
            mock_main.return_value = '<html>immediate result</html>'
            
            # Test immediate delegation
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = create_page_preview_html_immediate(
                    cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                    'A4', 'SimHei', '#ffffff', 3, 2, True
                )
                
                # Verify deprecation warning
                assert len(w) == 1
                assert issubclass(w[0].category, DeprecationWarning)
                assert "deprecated" in str(w[0].message)
            
            # Verify main function was called
            assert mock_main.called
            assert result == '<html>immediate result</html>'
    
    def test_feature_flag_disabled(self):
        """Test that legacy implementation is used when feature flag is disabled."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=False), \
             patch('services.cache_v2._slice_cards_for_page') as mock_slice, \
             patch('services.cache_v2._compute_page_layout_metrics') as mock_metrics, \
             patch('services.cache_v2._compute_page_card_box') as mock_box, \
             patch('services.cache_v2._compute_font_px') as mock_font:
            
            # Mock legacy implementation components
            mock_slice.return_value = (4, cards)
            mock_metrics.return_value = MagicMock()
            mock_box.return_value = MagicMock()
            mock_font.return_value = MagicMock()
            
            # Mock Jinja2 template
            with patch('jinja2.Environment') as mock_env:
                mock_template = MagicMock()
                mock_template.render.return_value = '<html>legacy result</html>'
                mock_env.return_value.get_template.return_value = mock_template
                
                # Test with feature flag disabled
                with warnings.catch_warnings(record=True):
                    warnings.simplefilter("always")
                    result = create_page_preview_html(
                        cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                        'A4', 'SimHei', '#ffffff', 3, 2, True
                    )
                
                # Verify legacy was used
                assert result == '<html>legacy result</html>'
                assert mock_slice.called
    
    def test_empty_cards_handling(self):
        """Test that empty cards are handled correctly in both legacy and v2."""
        cards = []
        
        # Test with v2 delegation
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.create_simple_grid_html_v2') as mock_v2:
            
            mock_v2.return_value = '<div>empty v2 result</div>'
            
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = create_simple_grid_html(cards)
            
            # Should still delegate to v2 even with empty cards
            assert mock_v2.called
            assert result == '<div>empty v2 result</div>'
    
    def test_parameter_validation_preserved(self):
        """Test that parameter validation is preserved through delegation."""
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        
        with patch('core.feature_flags.get_feature_flag', return_value=True), \
             patch('services.cache_v2.create_page_preview_html_v2') as mock_v2, \
             patch('services.preview_types.convert_legacy_params_to_preview_params') as mock_convert:
            
            # Mock the conversion
            mock_params = MagicMock()
            mock_params.layout = MagicMock()
            mock_params.typography = MagicMock()
            mock_params.visual = MagicMock()
            mock_convert.return_value = mock_params
            
            mock_v2.return_value = '<html>result</html>'
            
            # Test with invalid parameters (should be normalized)
            with warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                result = create_page_preview_html(
                    cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
                    'A4', 'SimHei', '#ffffff', 0, 0, True  # Invalid rows/cols
                )
            
            # Verify conversion was called (legacy validation happens before conversion)
            assert mock_convert.called
            assert result == '<html>result</html>'
