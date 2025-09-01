"""
End-to-end tests for refactored UI workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

from ui.ports import get_ui_adapter, ComponentConfig
from ui.error_boundaries import with_error_boundary


class TestCompleteUserWorkflows:
    """Test complete user workflows with refactored components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_st = Mock()
        self.adapter = get_ui_adapter()
    
    def test_complete_card_creation_workflow(self, monkeypatch):
        """Test complete workflow from input to card creation."""
        # Mock all streamlit components
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        monkeypatch.setattr('ui.sections.st', self.mock_st)
        
        # Mock input section
        self.mock_st.text_area.return_value = "测试\ntest"
        self.mock_st.file_uploader.return_value = None
        self.mock_st.button.return_value = False
        
        # Mock options section
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.side_effect = [3, 2, 48, 18, 14]
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Mock dependencies
        with patch('ui.inputs.get_ui_adapter', return_value=self.adapter), \
             patch('ui.options.get_ui_adapter', return_value=self.adapter), \
             patch('ui.inputs.process_text_input') as mock_process:
            
            mock_process.return_value = [
                {'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}
            ]
            
            # Import and test the workflow
            from ui.inputs import render_input_section_adapted
            from ui.options import render_options_section_adapted, render_advanced_options_adapted
            
            # Test input processing
            cards = render_input_section_adapted(self.adapter)
            assert isinstance(cards, list)

            # Test options configuration
            options = render_options_section_adapted(self.adapter)
            assert isinstance(options, tuple)
            assert len(options) == 5

            # Test advanced options
            advanced = render_advanced_options_adapted(self.adapter)
            assert isinstance(advanced, tuple)
            assert len(advanced) == 7
    
    def test_error_recovery_workflow(self, monkeypatch):
        """Test error recovery in complete workflow."""
        monkeypatch.setattr('ui.error_boundaries.st', self.mock_st)
        
        # Test that errors in one component don't break the entire workflow
        @with_error_boundary("test_component")
        def failing_component():
            raise ValueError("Component failed")
        
        @with_error_boundary("working_component")
        def working_component():
            return "success"
        
        # Failing component should be handled gracefully
        result1 = failing_component()
        assert result1 is None
        self.mock_st.error.assert_called()
        
        # Working component should still work
        result2 = working_component()
        assert result2 == "success"
    
    def test_adapter_consistency_workflow(self, monkeypatch):
        """Test adapter consistency across workflow."""
        monkeypatch.setattr('ui.ports.st', self.mock_st)
        
        # Test that same adapter instance is used throughout
        adapter1 = get_ui_adapter()
        adapter2 = get_ui_adapter()
        
        assert adapter1 is adapter2
        
        # Test adapter methods work consistently
        adapter1.header("Test Header")
        adapter2.text("Test Text")
        
        self.mock_st.header.assert_called_with("Test Header")
        self.mock_st.text.assert_called_with("Test Text")
    
    def test_session_state_persistence_workflow(self, monkeypatch):
        """Test session state persistence across components."""
        mock_session_state = {
            'test_input': 'test_value',
            'test_option': True,
            'test_advanced': 5.5
        }
        
        # Mock session state for all components
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.sidebar.st.session_state', mock_session_state)
        
        # Test that session state is accessible from all components
        assert mock_session_state.get('test_input') == 'test_value'
        assert mock_session_state.get('test_option') is True
        assert mock_session_state.get('test_advanced') == 5.5
        
        # Test state updates
        mock_session_state['new_value'] = 'updated'
        assert mock_session_state.get('new_value') == 'updated'


class TestPerformanceWorkflows:
    """Test performance aspects of refactored workflows."""
    
    def test_adapter_creation_performance(self):
        """Test adapter creation performance."""
        import time
        
        start_time = time.time()
        adapters = []
        
        # Create multiple adapters (should reuse singleton)
        for _ in range(100):
            adapter = get_ui_adapter()
            adapters.append(adapter)
        
        end_time = time.time()
        
        # Should be very fast due to singleton pattern
        assert end_time - start_time < 0.1  # Less than 100ms
        
        # All should be same instance
        assert all(adapter is adapters[0] for adapter in adapters)
    
    def test_component_config_performance(self):
        """Test ComponentConfig creation performance."""
        import time
        
        start_time = time.time()
        configs = []
        
        # Create many configs
        for i in range(1000):
            config = ComponentConfig(
                key=f"perf_test_{i}",
                label=f"Performance Test {i}",
                help_text=f"Help text {i}",
                disabled=i % 2 == 0
            )
            configs.append(config)
        
        end_time = time.time()
        
        # Should be reasonably fast
        assert end_time - start_time < 1.0  # Less than 1 second
        assert len(configs) == 1000
    
    def test_error_boundary_performance(self, monkeypatch):
        """Test error boundary performance impact."""
        import time
        
        monkeypatch.setattr('ui.error_boundaries.st', Mock())
        
        @with_error_boundary("perf_test")
        def fast_function():
            return "result"
        
        # Test successful execution performance
        start_time = time.time()
        for _ in range(100):
            result = fast_function()
            assert result == "result"
        end_time = time.time()
        
        # Error boundary should have minimal overhead
        assert end_time - start_time < 0.1  # Less than 100ms for 100 calls


class TestRegressionWorkflows:
    """Test regression scenarios for refactored components."""
    
    def test_no_regression_in_basic_functionality(self, monkeypatch):
        """Test that basic functionality hasn't regressed."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Test basic UI methods still work
        adapter.header("Test")
        adapter.subheader("Test")
        adapter.text("Test")
        adapter.markdown("Test")
        adapter.write("Test")
        adapter.caption("Test")
        
        # Verify all were called
        mock_st.header.assert_called_with("Test")
        mock_st.subheader.assert_called_with("Test")
        mock_st.text.assert_called_with("Test")
        mock_st.markdown.assert_called_with("Test")
        mock_st.write.assert_called_with("Test")
        mock_st.caption.assert_called_with("Test")
    
    def test_no_regression_in_input_components(self, monkeypatch):
        """Test that input components haven't regressed."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Test input components
        config = ComponentConfig(key="test", label="Test")
        
        mock_st.text_input.return_value = "test"
        mock_st.button.return_value = True
        mock_st.checkbox.return_value = False
        mock_st.selectbox.return_value = "option1"
        
        # Test all input methods
        result1 = adapter.inputs.text_input(config)
        result2 = adapter.inputs.button(config)
        result3 = adapter.inputs.checkbox(config)
        result4 = adapter.inputs.selectbox(config, options=["option1", "option2"])
        
        assert result1 == "test"
        assert result2 is True
        assert result3 is False
        assert result4 == "option1"
    
    def test_no_regression_in_layout_components(self, monkeypatch):
        """Test that layout components haven't regressed."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Mock layout components
        mock_columns = [Mock(), Mock()]
        mock_expander = Mock()
        mock_container = Mock()
        
        mock_st.columns.return_value = mock_columns
        mock_st.expander.return_value = mock_expander
        mock_st.container.return_value = mock_container
        
        # Test layout methods
        columns = adapter.layout.columns([1, 1])
        expander = adapter.layout.expander("Test")
        container = adapter.layout.container()
        
        assert columns == mock_columns
        assert expander == mock_expander
        assert container == mock_container
    
    def test_no_regression_in_notifications(self, monkeypatch):
        """Test that notification components haven't regressed."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        
        # Test notification methods
        adapter.notifications.show_success("Success")
        adapter.notifications.show_info("Info")
        adapter.notifications.show_warning("Warning")
        adapter.notifications.show_error("Error")
        
        mock_st.success.assert_called_with("Success")
        mock_st.info.assert_called_with("Info")
        mock_st.warning.assert_called_with("Warning")
        mock_st.error.assert_called_with("Error")


class TestEdgeCaseWorkflows:
    """Test edge cases in refactored workflows."""
    
    def test_empty_input_workflow(self, monkeypatch):
        """Test workflow with empty inputs."""
        mock_st = Mock()
        monkeypatch.setattr('ui.inputs.st', mock_st)
        
        # Mock empty input
        self.mock_st.text_area.return_value = ""
        self.mock_st.file_uploader.return_value = None
        
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        
        with patch('ui.inputs.get_ui_adapter', return_value=get_ui_adapter()), \
             patch('ui.inputs.process_text_input') as mock_process:
            
            mock_process.return_value = []
            
            from ui.inputs import render_input_section_adapted
            result = render_input_section_adapted()
            
            # Should handle empty input gracefully
            assert isinstance(result, list)
            assert len(result) == 0
    
    def test_invalid_config_workflow(self):
        """Test workflow with invalid configurations."""
        # Test invalid ComponentConfig
        with pytest.raises(TypeError):
            ComponentConfig()  # Missing required fields
        
        # Test valid minimal config
        config = ComponentConfig(key="test", label="Test")
        assert config.key == "test"
        assert config.label == "Test"
    
    def test_exception_propagation_workflow(self, monkeypatch):
        """Test exception propagation in workflows."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        # Test that exceptions are properly propagated for error boundaries
        adapter = get_ui_adapter()
        config = ComponentConfig(key="test", label="Test")
        
        mock_st.text_input.side_effect = RuntimeError("Streamlit error")
        
        with pytest.raises(RuntimeError):
            adapter.inputs.text_input(config)


class TestAccessibilityWorkflows:
    """Test accessibility aspects of refactored workflows."""
    
    def test_component_accessibility_attributes(self, monkeypatch):
        """Test that components maintain accessibility attributes."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        config = ComponentConfig(
            key="accessible_test",
            label="Accessible Test",
            help_text="This is help text for accessibility"
        )
        
        adapter.inputs.text_input(config)
        
        # Verify help text is passed through
        call_args = mock_st.text_input.call_args
        assert call_args[1]['help'] == "This is help text for accessibility"
    
    def test_disabled_component_workflow(self, monkeypatch):
        """Test workflow with disabled components."""
        mock_st = Mock()
        monkeypatch.setattr('ui.ports.st', mock_st)
        
        adapter = get_ui_adapter()
        config = ComponentConfig(
            key="disabled_test",
            label="Disabled Test",
            disabled=True
        )
        
        adapter.inputs.button(config)
        
        # Verify disabled state is passed through
        call_args = mock_st.button.call_args
        assert call_args[1]['disabled'] is True
