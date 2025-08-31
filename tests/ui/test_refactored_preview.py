"""
Tests for refactored preview functions in ui/sections.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.config import UIConfig, LayoutConfig, AppConfig
from ui.sections import (
    _validate_preview_inputs,
    _calculate_pagination,
    _manage_page_state,
    _render_preview_ui,
    _render_empty_preview,
    render_preview_content,
    render_preview_content_legacy
)


class TestValidatePreviewInputs:
    """Test _validate_preview_inputs function."""
    
    def test_valid_inputs(self):
        """Test with valid inputs."""
        cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        config = AppConfig.default()
        
        result_cards, result_config = _validate_preview_inputs(cards, config)
        
        assert result_cards == cards
        assert result_config == config
    
    def test_invalid_cards_input(self):
        """Test with invalid cards input."""
        cards = "not a list"
        config = AppConfig.default()
        
        result_cards, result_config = _validate_preview_inputs(cards, config)
        
        assert result_cards == []
        assert isinstance(result_config, AppConfig)
    
    def test_invalid_config_input(self):
        """Test with invalid config input."""
        cards = [{'hanzi': '你好'}]
        config = "not a config"
        
        result_cards, result_config = _validate_preview_inputs(cards, config)
        
        assert result_cards == cards
        assert isinstance(result_config, AppConfig)
    
    def test_none_inputs(self):
        """Test with None inputs."""
        result_cards, result_config = _validate_preview_inputs(None, None)
        
        assert result_cards == []
        assert isinstance(result_config, AppConfig)


class TestCalculatePagination:
    """Test _calculate_pagination function."""
    
    @patch('ui.sections.get_layout_settings')
    def test_normal_pagination(self, mock_get_layout):
        """Test normal pagination calculation."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3}
        cards = [{'hanzi': f'卡片{i}'} for i in range(10)]
        
        cards_per_page, total_pages = _calculate_pagination(cards)
        
        assert cards_per_page == 6  # 2 * 3
        assert total_pages == 2     # ceil(10 / 6)
    
    @patch('ui.sections.get_layout_settings')
    def test_empty_cards(self, mock_get_layout):
        """Test pagination with empty cards."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3}
        cards = []
        
        cards_per_page, total_pages = _calculate_pagination(cards)
        
        assert cards_per_page == 6
        assert total_pages == 1  # At least 1 page
    
    @patch('ui.sections.get_layout_settings')
    def test_single_card(self, mock_get_layout):
        """Test pagination with single card."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3}
        cards = [{'hanzi': '你好'}]
        
        cards_per_page, total_pages = _calculate_pagination(cards)
        
        assert cards_per_page == 6
        assert total_pages == 1
    
    @patch('ui.sections.get_layout_settings')
    def test_exact_page_boundary(self, mock_get_layout):
        """Test pagination at exact page boundary."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3}
        cards = [{'hanzi': f'卡片{i}'} for i in range(6)]  # Exactly one page
        
        cards_per_page, total_pages = _calculate_pagination(cards)
        
        assert cards_per_page == 6
        assert total_pages == 1


class TestManagePageState:
    """Test _manage_page_state function."""
    
    @patch('ui.sections.get_current_page')
    @patch('ui.sections.set_current_page')
    def test_page_within_range(self, mock_set_page, mock_get_page):
        """Test page state when current page is within range."""
        mock_get_page.return_value = 1
        total_pages = 3
        
        _manage_page_state(total_pages)
        
        mock_set_page.assert_not_called()  # Should not reset page
    
    @patch('ui.sections.get_current_page')
    @patch('ui.sections.set_current_page')
    def test_page_out_of_range(self, mock_set_page, mock_get_page):
        """Test page state when current page is out of range."""
        mock_get_page.return_value = 5
        total_pages = 3
        
        _manage_page_state(total_pages)
        
        mock_set_page.assert_called_once_with(0)  # Should reset to page 0
    
    @patch('ui.sections.get_current_page')
    @patch('ui.sections.set_current_page')
    def test_page_equal_to_total(self, mock_set_page, mock_get_page):
        """Test page state when current page equals total pages."""
        mock_get_page.return_value = 3
        total_pages = 3
        
        _manage_page_state(total_pages)
        
        mock_set_page.assert_called_once_with(0)  # Should reset (page is 0-indexed)


class TestRenderPreviewUI:
    """Test _render_preview_ui function."""
    
    @patch('ui.sections.get_layout_settings')
    @patch('ui.sections.render_page_navigation')
    @patch('ui.sections.render_preview_section')
    @patch('ui.sections.render_page_info')
    def test_render_preview_ui(self, mock_page_info, mock_preview_section, 
                              mock_page_nav, mock_get_layout):
        """Test _render_preview_ui function."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3, 'layout_auto_fill': True}
        
        cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        config = AppConfig.default()
        cards_per_page = 6
        total_pages = 1
        
        _render_preview_ui(cards, config, cards_per_page, total_pages)
        
        # Verify all render functions were called
        mock_page_nav.assert_called_once_with(total_pages)
        mock_preview_section.assert_called_once()
        mock_page_info.assert_called_once_with(cards, cards_per_page, total_pages)


class TestRenderEmptyPreview:
    """Test _render_empty_preview function."""
    
    @patch('ui.sections.st.components.v1.html')
    @patch('ui.sections.create_preview_html')
    def test_render_empty_preview_success(self, mock_create_html, mock_st_html):
        """Test _render_empty_preview with successful rendering."""
        mock_create_html.return_value = "<html>Empty preview</html>"
        
        _render_empty_preview()
        
        mock_create_html.assert_called_once_with([])
        mock_st_html.assert_called_once()
    
    @patch('ui.sections.st.components.v1.html')
    @patch('ui.sections.create_preview_html')
    @patch('ui.sections.st.error')
    def test_render_empty_preview_error(self, mock_st_error, mock_create_html, mock_st_html):
        """Test _render_empty_preview with rendering error."""
        mock_st_html.side_effect = Exception("Rendering error")
        
        _render_empty_preview()
        
        mock_st_error.assert_called_once()


class TestRenderPreviewContent:
    """Test main render_preview_content function."""
    
    @patch('ui.sections._validate_preview_inputs')
    @patch('ui.sections._calculate_pagination')
    @patch('ui.sections._manage_page_state')
    @patch('ui.sections._render_preview_ui')
    def test_render_with_cards(self, mock_render_ui, mock_manage_page, 
                              mock_calc_pagination, mock_validate):
        """Test render_preview_content with cards."""
        # Setup mocks
        cards = [{'hanzi': '你好'}]
        config = AppConfig.default()
        mock_validate.return_value = (cards, config)
        mock_calc_pagination.return_value = (6, 1)
        
        result = render_preview_content(cards, config)
        
        # Verify function calls
        mock_validate.assert_called_once_with(cards, config)
        mock_calc_pagination.assert_called_once_with(cards)
        mock_manage_page.assert_called_once_with(1)
        mock_render_ui.assert_called_once_with(cards, config, 6, 1)
        
        # Verify return value
        assert result == (6, 1)
    
    @patch('ui.sections._validate_preview_inputs')
    @patch('ui.sections._render_empty_preview')
    def test_render_without_cards(self, mock_render_empty, mock_validate):
        """Test render_preview_content without cards."""
        config = AppConfig.default()
        mock_validate.return_value = ([], config)
        
        result = render_preview_content([], config)
        
        mock_validate.assert_called_once()
        mock_render_empty.assert_called_once()
        assert result == (0, 1)


class TestRenderPreviewContentLegacy:
    """Test legacy render_preview_content_legacy function."""
    
    @patch('ui.sections.get_layout_settings')
    @patch('ui.sections.render_preview_content')
    def test_legacy_function(self, mock_render_content, mock_get_layout):
        """Test legacy function converts parameters correctly."""
        mock_get_layout.return_value = {'layout_rows': 2, 'layout_cols': 3, 'layout_auto_fill': True}
        mock_render_content.return_value = (6, 1)
        
        cards = [{'hanzi': '你好'}]
        preview_params = {
            'hanzi_font_family': 'Arial',
            'background_color': '#f0f0f0',
            'preview_mode': '🔲 简单网格'
        }
        layout_params = {
            'card_size_cm': 6.0,
            'gap_cm': 0.8,
            'margin_cm': 1.5,
            'page_size': 'A3',
            'hanzi_font_size': 50,
            'pinyin_font_size': 20,
            'english_font_size': 16
        }
        
        result = render_preview_content_legacy(cards, preview_params, layout_params)
        
        # Verify the new function was called
        mock_render_content.assert_called_once()
        
        # Verify return value
        assert result == (6, 1)


if __name__ == '__main__':
    pytest.main([__file__])
