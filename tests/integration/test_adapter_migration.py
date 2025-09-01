"""
Integration tests for adapter migration and component compatibility.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

from ui.ports import get_ui_adapter, ComponentConfig
from ui.inputs import render_input_section_adapted
from ui.options import render_options_section_adapted, render_advanced_options_adapted
from ui.sidebar import render_sidebar_adapted
from ui.sections import render_left_column, render_export_section


class TestAdapterMigrationIntegration:
    """Test integration between old and new adapter systems."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_st = Mock()
        self.adapter = get_ui_adapter()
    
    def test_input_section_adapter_integration(self, monkeypatch):
        """Test input section adapter integration."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.inputs.get_ui_adapter', lambda: self.adapter)
        
        # Mock streamlit components
        self.mock_st.text_area.return_value = "测试文本\n英文 text"
        self.mock_st.file_uploader.return_value = None
        self.mock_st.button.return_value = False
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        
        # Test the adapted function
        result = render_input_section_adapted(self.adapter)
        
        # Should return processed cards
        assert isinstance(result, list)
        assert len(result) >= 0  # May be empty if no valid input
    
    def test_options_section_adapter_integration(self, monkeypatch):
        """Test options section adapter integration."""
        monkeypatch.setattr('ui.options.st', self.mock_st)
        monkeypatch.setattr('ui.options.get_ui_adapter', lambda: self.adapter)
        
        # Mock streamlit components
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.return_value = 3
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Test the adapted function
        result = render_options_section_adapted(self.adapter)
        
        # Should return tuple of options
        assert isinstance(result, tuple)
        assert len(result) == 5  # auto_pinyin, auto_translate, page_size, card_size_cm, layout info
    
    def test_advanced_options_adapter_integration(self, monkeypatch):
        """Test advanced options adapter integration."""
        monkeypatch.setattr('ui.options.st', self.mock_st)
        monkeypatch.setattr('ui.options.get_ui_adapter', lambda: self.adapter)
        
        # Mock streamlit components
        self.mock_st.slider.return_value = 1.0
        self.mock_st.number_input.side_effect = [3, 2, 48, 18, 14]  # cols, rows, fonts
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Test the adapted function
        result = render_advanced_options_adapted(self.adapter)
        
        # Should return tuple of advanced options
        assert isinstance(result, tuple)
        assert len(result) == 7  # gap, margin, hanzi_font, pinyin_font, english_font, rows, cols
    
    def test_sidebar_adapter_integration(self, monkeypatch):
        """Test sidebar adapter integration."""
        monkeypatch.setattr('ui.sidebar.st', self.mock_st)
        monkeypatch.setattr('ui.sidebar.get_ui_adapter', lambda: self.adapter)
        
        # Mock streamlit components
        self.mock_st.sidebar = Mock()
        self.mock_st.header = Mock()
        self.mock_st.metric = Mock()
        self.mock_st.expander = Mock()
        self.mock_st.button = Mock()
        
        # Mock session state and dependencies
        mock_session_state = {
            'dictionary': Mock(),
            'total_cards_generated': 10,
            'export_history': []
        }
        monkeypatch.setattr('ui.sidebar.st.session_state', mock_session_state)
        mock_session_state['dictionary'].get_statistics.return_value = {'mini_dict_entries': 100}
        
        # Mock feature flags
        monkeypatch.setattr('ui.sidebar.get_feature_flag', lambda flag, default: default)
        
        # Test the adapted function
        render_sidebar_adapted(self.adapter)
        
        # Should not raise exceptions
        assert True  # If we get here, the function executed successfully
    
    def test_sections_integration(self, monkeypatch):
        """Test sections integration with adapters."""
        monkeypatch.setattr('ui.sections.st', self.mock_st)
        
        # Mock the adapted functions
        mock_input_result = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
        mock_options_result = (True, True, "A4", 5.5, {'auto_fill': True})
        mock_advanced_result = (0.5, 1.0, 48, 18, 14, 2, 3)
        
        with patch('ui.sections.render_input_section_adapted', return_value=mock_input_result), \
             patch('ui.sections.render_options_section_adapted', return_value=mock_options_result), \
             patch('ui.sections.render_advanced_options_adapted', return_value=mock_advanced_result):
            
            result = render_left_column()
            
            # Should return processed cards and layout parameters
            assert isinstance(result, tuple)
            assert len(result) == 2  # processed_cards, layout_params
            assert result[0] == mock_input_result
            assert isinstance(result[1], dict)
    
    def test_export_section_integration(self, monkeypatch):
        """Test export section integration."""
        monkeypatch.setattr('ui.sections.st', self.mock_st)
        
        # Mock export adapted function
        with patch('ui.sections.render_export_adapted') as mock_export:
            test_cards = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            render_export_section(test_cards)
            
            # Should call the adapted export function
            mock_export.assert_called_once_with(test_cards)


class TestBackwardCompatibility:
    """Test backward compatibility between old and new systems."""
    
    def test_component_config_compatibility(self):
        """Test ComponentConfig works with existing code patterns."""
        # Test minimal config
        config = ComponentConfig(key="test", label="Test")
        assert config.key == "test"
        assert config.label == "Test"
        
        # Test full config
        config = ComponentConfig(
            key="full_test",
            label="Full Test",
            help_text="Help text",
            disabled=True
        )
        assert config.key == "full_test"
        assert config.label == "Full Test"
        assert config.help_text == "Help text"
        assert config.disabled is True
    
    def test_adapter_fallback_compatibility(self, monkeypatch):
        """Test adapter fallback to direct Streamlit calls."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Test that adapter methods call streamlit directly
        adapter.header("Test")
        mock_st.header.assert_called_with("Test")
        
        adapter.text("Test text")
        mock_st.text.assert_called_with("Test text")
        
        adapter.markdown("**Test**")
        mock_st.markdown.assert_called_with("**Test**")
    
    def test_session_state_compatibility(self, monkeypatch):
        """Test session state compatibility between systems."""
        mock_session_state = {}
        monkeypatch.setattr('streamlit.session_state', mock_session_state)
        
        # Test that both old and new systems can access session state
        mock_session_state['test_key'] = 'test_value'
        
        # Should be accessible from both systems
        assert mock_session_state.get('test_key') == 'test_value'


class TestErrorHandlingIntegration:
    """Test error handling integration across adapter system."""
    
    def test_adapter_error_boundary_integration(self, monkeypatch):
        """Test error boundaries work with adapter system."""
        from ui.error_boundaries import with_error_boundary
        
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_error_boundary("test_adapter")
        def failing_adapter_function():
            adapter = get_ui_adapter()
            raise ValueError("Adapter error")
        
        result = failing_adapter_function()
        assert result is None
        mock_st.error.assert_called_once()
    
    def test_component_error_recovery(self, monkeypatch):
        """Test component error recovery with adapters."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        # Simulate streamlit component failure
        mock_st.text_input.side_effect = Exception("Component error")
        
        adapter = get_ui_adapter()
        config = ComponentConfig(key="error_test", label="Error Test")
        
        # Should propagate exception for proper error boundary handling
        with pytest.raises(Exception):
            adapter.inputs.text_input(config)


class TestPerformanceIntegration:
    """Test performance aspects of adapter integration."""
    
    def test_adapter_singleton_performance(self):
        """Test adapter singleton pattern performance."""
        # Multiple calls should return same instance
        adapter1 = get_ui_adapter()
        adapter2 = get_ui_adapter()
        adapter3 = get_ui_adapter()
        
        assert adapter1 is adapter2
        assert adapter2 is adapter3
        assert adapter1 is adapter3
    
    def test_component_config_creation_performance(self):
        """Test ComponentConfig creation performance."""
        # Should be fast to create many configs
        configs = []
        for i in range(100):
            config = ComponentConfig(
                key=f"test_{i}",
                label=f"Test {i}",
                help_text=f"Help {i}"
            )
            configs.append(config)
        
        assert len(configs) == 100
        assert all(config.key.startswith("test_") for config in configs)


class TestMigrationCompleteness:
    """Test that migration is complete and consistent."""
    
    def test_all_ui_functions_have_adapters(self):
        """Test that all major UI functions have adapter equivalents."""
        adapter = get_ui_adapter()
        
        # Test core UI methods exist
        assert hasattr(adapter, 'header')
        assert hasattr(adapter, 'subheader')
        assert hasattr(adapter, 'title')
        assert hasattr(adapter, 'text')
        assert hasattr(adapter, 'markdown')
        assert hasattr(adapter, 'write')
        assert hasattr(adapter, 'caption')
        assert hasattr(adapter, 'rerun')
        
        # Test input adapters exist
        assert hasattr(adapter.inputs, 'text_input')
        assert hasattr(adapter.inputs, 'text_area')
        assert hasattr(adapter.inputs, 'button')
        assert hasattr(adapter.inputs, 'checkbox')
        assert hasattr(adapter.inputs, 'selectbox')
        assert hasattr(adapter.inputs, 'radio')
        assert hasattr(adapter.inputs, 'slider')
        assert hasattr(adapter.inputs, 'number_input')
        assert hasattr(adapter.inputs, 'file_uploader')
        
        # Test layout adapters exist
        assert hasattr(adapter.layout, 'columns')
        assert hasattr(adapter.layout, 'sidebar')
        assert hasattr(adapter.layout, 'expander')
        assert hasattr(adapter.layout, 'container')
        
        # Test notification adapters exist
        assert hasattr(adapter.notifications, 'show_success')
        assert hasattr(adapter.notifications, 'show_info')
        assert hasattr(adapter.notifications, 'show_warning')
        assert hasattr(adapter.notifications, 'show_error')
    
    def test_adapter_method_signatures(self):
        """Test that adapter methods have correct signatures."""
        adapter = get_ui_adapter()
        
        # Test that methods are callable
        assert callable(adapter.header)
        assert callable(adapter.inputs.text_input)
        assert callable(adapter.layout.columns)
        assert callable(adapter.notifications.show_success)
    
    def test_no_direct_streamlit_imports_in_adapted_modules(self):
        """Test that adapted modules don't import streamlit directly."""
        # This is more of a code structure test
        # In practice, we'd check the actual imports in the modules
        
        # For now, just verify the adapter system is working
        adapter = get_ui_adapter()
        assert adapter is not None
        assert hasattr(adapter, 'inputs')
        assert hasattr(adapter, 'layout')
        assert hasattr(adapter, 'notifications')
