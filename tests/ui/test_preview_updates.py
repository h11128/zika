"""
Test suite for preview update functionality.
Tests all the bug fixes for preview not updating when parameters change.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the modules we're testing
from services.cache_v2 import clear_preview_cache_v2 as clear_preview_cache, cached_create_page_preview_html_v2 as cached_create_page_preview_html, cached_create_simple_grid_html_v2 as cached_create_simple_grid_html
from services.cache import create_page_preview_html_immediate, create_simple_grid_html_immediate
from ui.components import render_preview_section, render_color_palette
from ui.options import render_advanced_options
from core.state import get_all_ui_params, handle_param_changes


class TestPreviewCacheManagement:
    """Test cache management for preview updates."""
    
    def setup_method(self):
        """Setup test environment."""
        # Mock streamlit session state
        self.mock_session_state = {}
        
    @patch('streamlit.session_state')
    def test_clear_preview_cache(self, mock_session_state):
        """Test that cache clearing works properly."""
        # Setup mock cache functions
        with patch('services.cache_v2.cached_create_page_preview_html') as mock_page_cache:
            with patch('services.cache_v2.cached_create_simple_grid_html') as mock_grid_cache:
                mock_page_cache.clear = MagicMock()
                mock_grid_cache.clear = MagicMock()
                
                # Call clear function
                clear_preview_cache()
                
                # Verify cache clear was called
                mock_page_cache.clear.assert_called_once()
                mock_grid_cache.clear.assert_called_once()
    
    @patch('streamlit.session_state')
    def test_immediate_vs_cached_rendering(self, mock_session_state):
        """Test that immediate rendering bypasses cache."""
        mock_session_state.__getitem__ = lambda key: self.mock_session_state.get(key)
        mock_session_state.__setitem__ = lambda key, value: self.mock_session_state.update({key: value})
        mock_session_state.get = lambda key, default=None: self.mock_session_state.get(key, default)
        
        test_cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        
        # Test immediate rendering
        with patch('services.cache_v2.create_page_preview_html') as mock_create:
            mock_create.return_value = "<html>test</html>"
            
            result = create_page_preview_html_immediate(
                test_cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, 
                "A4", "SimHei", "#ffffff", 2, 3, True
            )
            
            assert result == "<html>test</html>"
            mock_create.assert_called_once()


class TestParameterChangeDetection:
    """Test parameter change detection and cache invalidation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_session_state = {
            'current_page': 0,
            'last_params': {},
            'export_ready': {},
            'export_data': {},
            'hanzi_font_family': 'SimHei',
            'background_color': '#ffffff',
            'layout_rows': 2,
            'layout_cols': 3,
            'layout_auto_fill': True
        }
    
    @patch('streamlit.session_state')
    @patch('core.state.get_layout_settings')
    @patch('core.state.get_ui_preferences')
    def test_get_all_ui_params(self, mock_prefs, mock_layout, mock_session_state):
        """Test parameter collection for change detection."""
        mock_session_state.__getitem__ = lambda key: self.mock_session_state.get(key)
        mock_session_state.get = lambda key, default=None: self.mock_session_state.get(key, default)
        
        mock_layout.return_value = {'layout_rows': 2, 'layout_cols': 3, 'layout_auto_fill': True}
        mock_prefs.return_value = {'hanzi_font_family': 'SimHei', 'background_color': '#ffffff'}
        
        test_cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        
        params = get_all_ui_params(5.5, 0.5, 1.0, 'A4', 48, 18, 14, test_cards)
        
        expected_keys = [
            'card_size_cm', 'gap_cm', 'margin_cm', 'page_size',
            'hanzi_font_size', 'pinyin_font_size', 'english_font_size',
            'hanzi_font_family', 'background_color', 'layout_rows', 'layout_cols', 'layout_auto_fill', 'total_cards'
        ]
        
        for key in expected_keys:
            assert key in params
        
        assert params['total_cards'] == 1
        assert params['card_size_cm'] == 5.5
        assert params['hanzi_font_family'] == 'SimHei'
    
    @patch('streamlit.session_state')
    @patch('core.state.check_params_changed')
    @patch('core.state.set_current_page')
    @patch('core.state.update_last_params')
    @patch('core.state.clear_export_data')
    def test_handle_param_changes(self, mock_clear_export, mock_update_params, 
                                 mock_set_page, mock_check_changed, mock_session_state):
        """Test parameter change handling."""
        mock_check_changed.return_value = True
        
        test_params = {'card_size_cm': 6.0, 'gap_cm': 0.8}
        result = handle_param_changes(test_params)
        
        assert result is True
        mock_set_page.assert_called_once_with(0)
        mock_update_params.assert_called_once_with(test_params)
        mock_clear_export.assert_called_once()


class TestUIComponentUpdates:
    """Test UI component updates trigger preview refresh."""

    def test_cache_clear_function_exists(self):
        """Test that cache clear function exists and is callable."""
        from services.cache_v2 import clear_preview_cache

        # Should not raise an exception
        clear_preview_cache()

        # Function should be callable
        assert callable(clear_preview_cache)

    def test_immediate_rendering_functions_exist(self):
        """Test that immediate rendering functions exist."""
        from services.cache_v2 import create_page_preview_html_immediate, create_simple_grid_html_immediate

        assert callable(create_page_preview_html_immediate)
        assert callable(create_simple_grid_html_immediate)

        # Test with minimal parameters
        test_cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]

        result1 = create_page_preview_html_immediate(
            test_cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
            "A4", "SimHei", "#ffffff", 2, 3, True
        )

        result2 = create_simple_grid_html_immediate(
            test_cards, "SimHei", "#ffffff", 2, 3
        )

        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert len(result1) > 0
        assert len(result2) > 0


class TestPreviewSectionRendering:
    """Test preview section rendering with parameter changes."""
    
    def setup_method(self):
        """Setup test environment."""
        self.mock_session_state = {
            'current_page': 0,
            'last_preview_params': None
        }
    
    @patch('streamlit.session_state')
    @patch('streamlit.empty')
    @patch('streamlit.components.v1.html')
    @patch('core.state.get_all_ui_params')
    @patch('core.state.check_params_changed')
    def test_render_preview_section_immediate_mode(self, mock_check_changed, mock_get_params,
                                                  mock_html, mock_empty, mock_session_state):
        """Test preview section uses immediate rendering when parameters change."""
        mock_session_state.__getitem__ = lambda key: self.mock_session_state.get(key)
        mock_session_state.__setitem__ = lambda key, value: self.mock_session_state.update({key: value})
        mock_session_state.get = lambda key, default=None: self.mock_session_state.get(key, default)
        
        mock_check_changed.return_value = True  # Parameters changed
        mock_get_params.return_value = {'test': 'params'}
        mock_empty.return_value.container.return_value.__enter__ = lambda x: None
        mock_empty.return_value.container.return_value.__exit__ = lambda x, y, z, w: None
        
        test_cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        
        with patch('services.cache_v2.create_page_preview_html_immediate') as mock_immediate:
            mock_immediate.return_value = "<html>immediate</html>"
            
            render_preview_section(
                test_cards, "📄 完整页面", 5.5, 0.5, 1.0, 48, 18, 14,
                "A4", "SimHei", "#ffffff", 2, 3, True
            )
            
            # Verify immediate rendering was used
            mock_immediate.assert_called_once()
            mock_html.assert_called_once_with("<html>immediate</html>", height_cm=850)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
