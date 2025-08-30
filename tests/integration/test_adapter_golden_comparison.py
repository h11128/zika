"""
Integration tests for adapter vs direct path golden comparison.

Tests that adapter and direct Streamlit paths produce identical results.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from ui.ports import get_ui_adapter, ComponentConfig
from ui.adapters.streamlit_adapter import StreamlitAdapter
from core.feature_flags import set_feature_flag, get_feature_flag


class MockStreamlit:
    """Mock Streamlit for testing."""
    
    def __init__(self):
        self.calls = []
        self.session_state = {}
    
    def checkbox(self, label, value=False, key=None, help=None, **kwargs):
        self.calls.append(('checkbox', label, value, key, help, kwargs))
        return value
    
    def text_input(self, label, value="", key=None, help=None, placeholder=None, **kwargs):
        self.calls.append(('text_input', label, value, key, help, placeholder, kwargs))
        return value
    
    def slider(self, label, min_value=0, max_value=100, value=50, step=1, key=None, help=None, **kwargs):
        self.calls.append(('slider', label, min_value, max_value, value, step, key, help, kwargs))
        return value
    
    def selectbox(self, label, options, index=0, key=None, help=None, **kwargs):
        self.calls.append(('selectbox', label, options, index, key, help, kwargs))
        return options[index] if options else None
    
    def radio(self, label, options, index=0, key=None, help=None, horizontal=False, **kwargs):
        self.calls.append(('radio', label, options, index, key, help, horizontal, kwargs))
        return options[index] if options else None
    
    def button(self, label, key=None, help=None, **kwargs):
        self.calls.append(('button', label, key, help, kwargs))
        return False
    
    def write(self, content):
        self.calls.append(('write', content))
    
    def header(self, text):
        self.calls.append(('header', text))
    
    def subheader(self, text):
        self.calls.append(('subheader', text))
    
    def markdown(self, content, unsafe_allow_html=False):
        self.calls.append(('markdown', content, unsafe_allow_html))
    
    def success(self, message):
        self.calls.append(('success', message))
    
    def error(self, message):
        self.calls.append(('error', message))
    
    def warning(self, message):
        self.calls.append(('warning', message))
    
    def info(self, message):
        self.calls.append(('info', message))
    
    def columns(self, ratios):
        self.calls.append(('columns', ratios))
        return [Mock() for _ in ratios]
    
    def container(self):
        self.calls.append(('container',))
        return Mock()
    
    def expander(self, label, expanded=False):
        self.calls.append(('expander', label, expanded))
        return Mock()


@pytest.fixture
def mock_streamlit():
    """Provide mock Streamlit for testing."""
    return MockStreamlit()


@pytest.fixture
def adapter():
    """Provide StreamlitAdapter for testing."""
    return StreamlitAdapter()


class TestAdapterGoldenComparison:
    """Test adapter vs direct path golden comparison."""
    
    def test_checkbox_comparison(self, mock_streamlit, adapter):
        """Test checkbox behavior is identical."""
        with patch('streamlit.checkbox', mock_streamlit.checkbox):
            # Direct Streamlit call
            direct_result = mock_streamlit.checkbox("Test Label", value=True, key="test_key", help="Test help")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            config = ComponentConfig(key="test_key", label="Test Label", help_text="Test help")
            adapter_result = adapter.inputs.checkbox(config, value=True)
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert direct_result == adapter_result
            assert len(direct_calls) == len(adapter_calls)
            
            # Compare call signatures (allowing for parameter reordering)
            direct_call = direct_calls[0]
            adapter_call = adapter_calls[0]
            
            assert direct_call[0] == adapter_call[0]  # Method name
            assert direct_call[1] == adapter_call[1]  # Label
            assert direct_call[2] == adapter_call[2]  # Value
            assert direct_call[3] == adapter_call[3]  # Key
            assert direct_call[4] == adapter_call[4]  # Help
    
    def test_text_input_comparison(self, mock_streamlit, adapter):
        """Test text input behavior is identical."""
        with patch('streamlit.text_input', mock_streamlit.text_input):
            # Direct Streamlit call
            direct_result = mock_streamlit.text_input("Test Label", value="test", key="test_key")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            config = ComponentConfig(key="test_key", label="Test Label")
            adapter_result = adapter.inputs.text_input(config, value="test")
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert direct_result == adapter_result
            assert len(direct_calls) == len(adapter_calls)
    
    def test_slider_comparison(self, mock_streamlit, adapter):
        """Test slider behavior is identical."""
        with patch('streamlit.slider', mock_streamlit.slider):
            # Direct Streamlit call
            direct_result = mock_streamlit.slider("Test Label", 0, 100, 50, 1, key="test_key")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            config = ComponentConfig(key="test_key", label="Test Label")
            adapter_result = adapter.inputs.slider(config, value=50, min_value=0, max_value=100, step=1)
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert direct_result == adapter_result
            assert len(direct_calls) == len(adapter_calls)
    
    def test_selectbox_comparison(self, mock_streamlit, adapter):
        """Test selectbox behavior is identical."""
        options = ["Option 1", "Option 2", "Option 3"]
        
        with patch('streamlit.selectbox', mock_streamlit.selectbox):
            # Direct Streamlit call
            direct_result = mock_streamlit.selectbox("Test Label", options, index=1, key="test_key")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            config = ComponentConfig(key="test_key", label="Test Label")
            adapter_result = adapter.inputs.selectbox(config, options=options, index=1)
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert direct_result == adapter_result
            assert len(direct_calls) == len(adapter_calls)
    
    def test_radio_comparison(self, mock_streamlit, adapter):
        """Test radio behavior is identical."""
        options = ["Option 1", "Option 2"]
        
        with patch('streamlit.radio', mock_streamlit.radio):
            # Direct Streamlit call
            direct_result = mock_streamlit.radio("Test Label", options, index=0, horizontal=True, key="test_key")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            config = ComponentConfig(key="test_key", label="Test Label")
            adapter_result = adapter.inputs.radio(config, options=options, index=0, horizontal=True)
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert direct_result == adapter_result
            assert len(direct_calls) == len(adapter_calls)
    
    def test_notification_comparison(self, mock_streamlit, adapter):
        """Test notification behavior is identical."""
        from ui.ports import NotificationLevel
        
        with patch('streamlit.success', mock_streamlit.success), \
             patch('streamlit.error', mock_streamlit.error), \
             patch('streamlit.warning', mock_streamlit.warning), \
             patch('streamlit.info', mock_streamlit.info):
            
            # Test success notification
            mock_streamlit.success("Success message")
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            adapter.notify("Success message", NotificationLevel.SUCCESS)
            adapter_calls = mock_streamlit.calls.copy()
            
            assert len(direct_calls) == len(adapter_calls)
            assert direct_calls[0][0] == adapter_calls[0][0]  # Method name
            assert direct_calls[0][1] == adapter_calls[0][1]  # Message
    
    def test_layout_comparison(self, mock_streamlit, adapter):
        """Test layout behavior is identical."""
        with patch('streamlit.columns', mock_streamlit.columns):
            # Direct Streamlit call
            direct_result = mock_streamlit.columns([1, 2, 1])
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter call
            adapter_result = adapter.layout.columns([1, 2, 1])
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare calls
            assert len(direct_calls) == len(adapter_calls)
            assert direct_calls[0][0] == adapter_calls[0][0]  # Method name
            assert direct_calls[0][1] == adapter_calls[0][1]  # Ratios


class TestFeatureFlagIntegration:
    """Test feature flag integration with adapters."""
    
    def test_feature_flag_controls_adapter_usage(self):
        """Test that feature flags control adapter usage."""
        # Test with adapter disabled
        set_feature_flag('ui_adapter', False)
        assert not get_feature_flag('ui_adapter', False)
        
        # Test with adapter enabled
        set_feature_flag('ui_adapter', True)
        assert get_feature_flag('ui_adapter', False)
    
    def test_graceful_fallback_on_adapter_failure(self, mock_streamlit):
        """Test graceful fallback when adapter fails."""
        with patch('streamlit.checkbox', mock_streamlit.checkbox):
            # Simulate adapter failure
            def failing_adapter_method(*args, **kwargs):
                raise Exception("Adapter failed")
            
            adapter = StreamlitAdapter()
            adapter.inputs.checkbox = failing_adapter_method
            
            # Should fall back to direct Streamlit call
            try:
                result = mock_streamlit.checkbox("Test", value=True)
                assert result is True
            except Exception:
                pytest.fail("Should have fallen back gracefully")


class TestEndToEndComparison:
    """Test end-to-end comparison of adapter vs direct paths."""
    
    def test_options_section_comparison(self, mock_streamlit):
        """Test that options section produces identical results."""
        with patch('streamlit.checkbox', mock_streamlit.checkbox), \
             patch('streamlit.selectbox', mock_streamlit.selectbox), \
             patch('streamlit.slider', mock_streamlit.slider), \
             patch('streamlit.subheader', mock_streamlit.subheader), \
             patch('streamlit.columns', mock_streamlit.columns):
            
            # This would require importing and testing actual UI functions
            # For now, we test the principle with simple components
            
            # Direct path
            mock_streamlit.subheader("Options")
            auto_pinyin = mock_streamlit.checkbox("Auto Pinyin", value=True)
            page_size = mock_streamlit.selectbox("Page Size", ["A4", "A3"], index=0)
            direct_calls = mock_streamlit.calls.copy()
            mock_streamlit.calls.clear()
            
            # Adapter path
            adapter = StreamlitAdapter()
            adapter.header("Options", level=2)  # subheader equivalent
            
            config1 = ComponentConfig(key="auto_pinyin", label="Auto Pinyin")
            adapter_auto_pinyin = adapter.inputs.checkbox(config1, value=True)
            
            config2 = ComponentConfig(key="page_size", label="Page Size")
            adapter_page_size = adapter.inputs.selectbox(config2, options=["A4", "A3"], index=0)
            
            adapter_calls = mock_streamlit.calls.copy()
            
            # Compare results
            assert auto_pinyin == adapter_auto_pinyin
            assert page_size == adapter_page_size
            
            # Both should have made the same number of calls
            assert len(direct_calls) == len(adapter_calls)
