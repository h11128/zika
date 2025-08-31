#!/usr/bin/env python3
"""
Test page reset policy alignment.

Verifies that current_page is only reset when cards_per_page or cards_count changes,
NOT for style-only changes.
"""

import pytest
import streamlit as st
from unittest.mock import patch, MagicMock

from ui.state import get_state_service
# Import ChangeSet directly from the module file
import importlib.util
spec = importlib.util.spec_from_file_location("ui_state_module", "ui/state.py")
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)
ChangeSet = ui_state_module.ChangeSet

from core.state import handle_param_changes, _should_reset_navigation


class TestPageResetPolicy:
    """Test page reset policy implementation."""
    
    @pytest.fixture
    def state_service(self):
        """Provide state service for testing."""
        return get_state_service()
    
    @pytest.fixture
    def mock_session_state(self):
        """Mock Streamlit session state."""
        with patch('streamlit.session_state') as mock_st:
            mock_st.current_page = 0
            mock_st.last_params = {}
            yield mock_st
    
    def test_style_changes_do_not_reset_page(self, state_service, mock_session_state):
        """Test that style-only changes do not reset current_page."""
        # Set initial page
        mock_session_state.current_page = 3
        
        # Make style-only changes
        style_changes = {
            'hanzi_font_size': 48,
            'pinyin_font_size': 18,
            'background_color': '#FFFFFF'
        }
        
        changeset = state_service.set_options_batch(style_changes)
        
        # Verify changeset affects style but not navigation reset
        assert changeset.affects_style is True
        assert changeset.nav_reset_required is False
        
        # Verify current_page was NOT reset
        assert mock_session_state.current_page == 3
    
    def test_layout_changes_reset_page(self, state_service, mock_session_state):
        """Test that layout changes reset current_page."""
        # Set initial page
        mock_session_state.current_page = 3
        
        # Make layout changes that affect cards_per_page
        layout_changes = {
            'layout_rows': 4,
            'layout_cols': 3
        }
        
        changeset = state_service.set_options_batch(layout_changes)
        
        # Verify changeset affects layout and requires navigation reset
        assert changeset.affects_layout is True
        assert changeset.nav_reset_required is True
        
        # Verify current_page was reset to 0
        assert mock_session_state.current_page == 0
    
    def test_processing_changes_reset_page(self, state_service, mock_session_state):
        """Test that processing changes reset current_page."""
        # Set initial page
        mock_session_state.current_page = 2
        
        # Make processing changes that affect cards count
        processing_changes = {
            'input_text': '你好 世界 中国',
            'auto_pinyin': True
        }
        
        changeset = state_service.set_options_batch(processing_changes)
        
        # Verify changeset affects processing and requires navigation reset
        assert changeset.affects_processing is True
        assert changeset.nav_reset_required is True
        
        # Verify current_page was reset to 0
        assert mock_session_state.current_page == 0
    
    def test_mixed_changes_reset_page_when_needed(self, state_service, mock_session_state):
        """Test mixed changes reset page only when layout/processing changes are included."""
        # Set initial page
        mock_session_state.current_page = 2
        
        # Make mixed changes including layout
        mixed_changes = {
            'layout_rows': 3,  # This should trigger reset
            'hanzi_font_size': 48,  # Style change
            'background_color': '#F0F0F0'  # Style change
        }
        
        changeset = state_service.set_options_batch(mixed_changes)
        
        # Verify changeset affects both layout and style
        assert changeset.affects_layout is True
        assert changeset.affects_style is True
        assert changeset.nav_reset_required is True
        
        # Verify current_page was reset due to layout change
        assert mock_session_state.current_page == 0
    
    def test_should_reset_navigation_function(self):
        """Test the _should_reset_navigation helper function."""
        # Test layout changes
        current_params = {'layout_rows': 4, 'layout_cols': 3, 'processed_cards': []}
        
        with patch('core.state._ss_get') as mock_get:
            mock_get.return_value = {'layout_rows': 3, 'layout_cols': 3, 'processed_cards': []}
            assert _should_reset_navigation(current_params) is True
        
        # Test style-only changes
        current_params = {'hanzi_font_size': 48, 'background_color': '#FFFFFF', 'processed_cards': []}
        
        with patch('core.state._ss_get') as mock_get:
            mock_get.return_value = {'hanzi_font_size': 36, 'background_color': '#000000', 'processed_cards': []}
            assert _should_reset_navigation(current_params) is False
        
        # Test cards count changes
        current_params = {'processed_cards': [{'hanzi': '你好'}, {'hanzi': '世界'}]}
        
        with patch('core.state._ss_get') as mock_get:
            mock_get.return_value = {'processed_cards': [{'hanzi': '你好'}]}
            assert _should_reset_navigation(current_params) is True
    
    def test_handle_param_changes_respects_policy(self):
        """Test that handle_param_changes respects the reset policy."""
        # Test with style-only changes
        style_params = {
            'hanzi_font_size': 48,
            'background_color': '#FFFFFF',
            'processed_cards': []
        }
        
        with patch('core.state.check_params_changed', return_value=True), \
             patch('core.state._should_reset_navigation', return_value=False) as mock_should_reset, \
             patch('core.state.set_current_page') as mock_set_page, \
             patch('core.state.update_last_params'), \
             patch('core.state.clear_export_data'):
            
            result = handle_param_changes(style_params)
            
            assert result is True
            mock_should_reset.assert_called_once_with(style_params)
            mock_set_page.assert_not_called()  # Should NOT reset page
        
        # Test with layout changes
        layout_params = {
            'layout_rows': 4,
            'layout_cols': 3,
            'processed_cards': []
        }
        
        with patch('core.state.check_params_changed', return_value=True), \
             patch('core.state._should_reset_navigation', return_value=True) as mock_should_reset, \
             patch('core.state.set_current_page') as mock_set_page, \
             patch('core.state.update_last_params'), \
             patch('core.state.clear_export_data'):
            
            result = handle_param_changes(layout_params)
            
            assert result is True
            mock_should_reset.assert_called_once_with(layout_params)
            mock_set_page.assert_called_once_with(0)  # Should reset page
    
    def test_changeset_computation_accuracy(self, state_service):
        """Test that changeset computation accurately identifies domains."""
        # Test style-only changes
        style_changes = {'hanzi_font_size': 48, 'background_color': '#FFFFFF'}
        changeset = state_service._compute_changeset(style_changes)
        
        assert changeset.affects_style is True
        assert changeset.affects_layout is False
        assert changeset.affects_processing is False
        assert changeset.nav_reset_required is False
        
        # Test layout changes
        layout_changes = {'layout_rows': 4, 'gap_cm': 0.5}
        changeset = state_service._compute_changeset(layout_changes)
        
        assert changeset.affects_layout is True
        assert changeset.affects_style is False
        assert changeset.nav_reset_required is True  # rows change triggers reset
        
        # Test processing changes
        processing_changes = {'input_text': '你好', 'auto_pinyin': True}
        changeset = state_service._compute_changeset(processing_changes)
        
        assert changeset.affects_processing is True
        assert changeset.affects_layout is False
        assert changeset.affects_style is False
        assert changeset.nav_reset_required is True  # processing affects cards count


if __name__ == "__main__":
    pytest.main([__file__])
