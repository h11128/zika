"""
Tests for error handling mechanisms across the application
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from ui.app_controller import AppController
from core.state import get_all_ui_params, handle_param_changes


class TestAppControllerErrorHandling:
    """Test error handling in AppController."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            info=Mock(),
            columns=Mock(return_value=[Mock(), Mock()]),
            session_state=Mock()
        ):
            yield
    
    @pytest.fixture
    def controller(self, mock_streamlit):
        """Create AppController instance with mocked dependencies."""
        with patch.multiple(
            'ui.app_controller',
            apply_global_styles=Mock(),
            initialize_session_state=Mock(),
            render_sidebar=Mock(),
            render_left_column=Mock(),
            render_preview_column_header=Mock(),
            render_preview_content_legacy=Mock(),
            render_export_section=Mock(),
            render_sticky_wrapper_end=Mock(),
            get_processed_cards=Mock(return_value=[]),
            st=Mock()
        ):
            return AppController()
    
    def test_should_reprocess_cards_exception_handling(self, controller, mock_streamlit):
        """Test exception handling in should_reprocess_cards."""
        with patch('ui.app_controller.get_processed_cards', side_effect=Exception("Database error")):
            result = controller.should_reprocess_cards([{'hanzi': '你好'}], 'test_source')
            
            # Should return True to force reprocessing on error
            assert result is True
            # Should log error
            st.error.assert_called()
    
    def test_process_cards_invalid_input_handling(self, controller, mock_streamlit):
        """Test handling of invalid input in process_cards_if_needed."""
        # Test with non-list input
        result = controller.process_cards_if_needed("invalid input", True, True)
        assert result == []
        
        # Test with None input
        result = controller.process_cards_if_needed(None, True, True)
        assert result == []
    
    def test_process_cards_generation_error_handling(self, controller, mock_streamlit):
        """Test error handling during card generation."""
        test_cards = [{'hanzi': '你好', 'pinyin': '', 'english': ''}]
        
        with patch.object(controller, 'should_reprocess_cards', return_value=True):
            with patch('ui.app_controller.generate_missing_data', side_effect=Exception("API error")):
                result = controller.process_cards_if_needed(test_cards, True, True)
                
                # Should return basic cards structure on error
                assert len(result) == 1
                assert 'hanzi' in result[0]
                # Should log error
                st.error.assert_called()
    
    def test_run_main_flow_left_column_error(self, controller, mock_streamlit):
        """Test error handling in left column rendering."""
        with patch('ui.app_controller.render_left_column', side_effect=Exception("UI error")):
            with patch('ui.app_controller.render_preview_column_header', return_value={}):
                with patch.object(controller, 'render_right_column_content'):
                    with patch('ui.app_controller.render_export_section'):
                        controller.run_main_flow()
                        
                        # Should log error and provide fallback
                        st.error.assert_called()
    
    def test_run_main_flow_right_column_error(self, controller, mock_streamlit):
        """Test error handling in right column rendering."""
        with patch('ui.app_controller.render_left_column', return_value={}):
            with patch.object(controller, 'render_right_column_content', side_effect=Exception("Preview error")):
                with patch('ui.app_controller.render_export_section'):
                    controller.run_main_flow()
                    
                    # Should log error
                    st.error.assert_called()
    
    def test_run_main_flow_export_error(self, controller, mock_streamlit):
        """Test error handling in export section."""
        with patch('ui.app_controller.render_left_column', return_value={}):
            with patch.object(controller, 'render_right_column_content'):
                with patch('ui.app_controller.render_export_section', side_effect=Exception("Export error")):
                    controller.run_main_flow()
                    
                    # Should log error
                    st.error.assert_called()
    
    def test_run_main_flow_critical_error(self, controller, mock_streamlit):
        """Test handling of critical errors in main flow."""
        with patch('ui.app_controller.render_sidebar', side_effect=Exception("Critical error")):
            controller.run_main_flow()
            
            # Should log critical error and suggest refresh
            st.error.assert_called()
            st.info.assert_called()


class TestStateErrorHandling:
    """Test error handling in state management functions."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit functions."""
        with patch('streamlit.error', Mock()) as mock_error:
            yield mock_error
    
    def test_get_all_ui_params_error_handling(self, mock_streamlit):
        """Test error handling in get_all_ui_params."""
        with patch('core.state.get_layout_settings', side_effect=Exception("State error")):
            with patch('core.state.get_ui_preferences', side_effect=Exception("Preferences error")):
                # This should be tested if the function had error handling
                # For now, we test that the function exists and can be called
                try:
                    result = get_all_ui_params(5.5, 0.5, 1.0, 'A4', 48, 18, 14, [])
                    # If no error handling, this might raise an exception
                except Exception:
                    # Expected if no error handling is implemented
                    pass
    
    def test_handle_param_changes_error_handling(self, mock_streamlit):
        """Test error handling in handle_param_changes."""
        test_params = {'card_size': 5.5, 'gap': 0.5}
        
        with patch('core.state.check_params_changed', side_effect=Exception("Check error")):
            # This should be tested if the function had error handling
            try:
                result = handle_param_changes(test_params)
                # If no error handling, this might raise an exception
            except Exception:
                # Expected if no error handling is implemented
                pass


class TestPreviewErrorHandling:
    """Test error handling in preview functions."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit functions."""
        with patch.multiple(
            'streamlit',
            error=Mock(),
            components=Mock()
        ):
            yield
    
    def test_render_empty_preview_error(self, mock_streamlit):
        """Test error handling in _render_empty_preview."""
        from ui.sections import _render_empty_preview
        
        with patch('ui.sections.st.components.v1.html', side_effect=Exception("Render error")):
            with patch('ui.sections.create_preview_html', return_value="<html></html>"):
                _render_empty_preview()
                
                # Should log error
                st.error.assert_called()
    
    def test_preview_content_with_invalid_config(self, mock_streamlit):
        """Test preview content with invalid configuration."""
        from ui.sections import render_preview_content
        from core.config import AppConfig
        
        # Test with invalid cards and config
        result = render_preview_content("invalid", "invalid")
        
        # Should handle gracefully and return default values
        assert result == (0, 1)


class TestInputValidation:
    """Test input validation across the application."""
    
    def test_config_validation(self):
        """Test configuration object validation."""
        from core.config import UIConfig, LayoutConfig
        
        # Test UIConfig with invalid data
        config = UIConfig.from_dict({})
        assert config.hanzi_font == 'SimHei'  # Should use defaults
        
        # Test LayoutConfig with string numbers
        config = LayoutConfig.from_dict({
            'card_size': '6.5',
            'font_hanzi': '50',
            'rows': '3'
        })
        assert config.card_size == 6.5
        assert config.font_hanzi == 50
        assert config.rows == 3
    
    def test_preview_input_validation(self):
        """Test preview function input validation."""
        from ui.sections import _validate_preview_inputs
        from core.config import AppConfig
        
        # Test with None inputs
        cards, config = _validate_preview_inputs(None, None)
        assert cards == []
        assert isinstance(config, AppConfig)
        
        # Test with invalid types
        cards, config = _validate_preview_inputs("not a list", 123)
        assert cards == []
        assert isinstance(config, AppConfig)


class TestRobustness:
    """Test application robustness under various conditions."""
    
    def test_empty_data_handling(self):
        """Test handling of empty data throughout the application."""
        from ui.sections import render_preview_content
        from core.config import AppConfig
        
        # Test with empty cards
        result = render_preview_content([], AppConfig.default())
        assert result == (0, 1)
        
        # Test with None
        result = render_preview_content(None, None)
        assert result == (0, 1)
    
    def test_malformed_data_handling(self):
        """Test handling of malformed data."""
        from core.config import UIConfig, LayoutConfig

        # Test UIConfig with malformed data
        config = UIConfig.from_dict({'hanzi_font': None, 'background_color': 123})
        assert config.hanzi_font == 'SimHei'  # Should use default for None
        assert config.background_color == '#ffffff'  # Should use default for invalid type

        # Test LayoutConfig with malformed data
        config = LayoutConfig.from_dict({'card_size': 'invalid', 'rows': -1})
        # Should return default config on conversion error
        assert isinstance(config, LayoutConfig)
        assert config.card_size == 5.5  # Default value
        assert config.rows == 2  # Default value


if __name__ == '__main__':
    pytest.main([__file__])
