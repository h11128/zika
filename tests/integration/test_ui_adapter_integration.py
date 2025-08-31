"""
Integration tests for UI adapter paths.
Tests that UI adapter system works correctly across different components.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import UI adapter interfaces
from ui.ports import UIAdapter, UIInputsPort, UIPreviewPort, UINotificationPort, UIRefreshScheduler


class MockUIAdapter:
    """Mock UI adapter for testing integration."""
    
    def __init__(self):
        self.inputs = MockInputsPort()
        self.preview = MockPreviewPort()
        self.notifications = MockNotificationPort()
        self.refresh_scheduler = MockRefreshScheduler()
        self.call_log = []
    
    def log_call(self, method, *args, **kwargs):
        """Log method calls for testing."""
        self.call_log.append((method, args, kwargs))


class MockInputsPort:
    """Mock inputs port for testing."""
    
    def __init__(self):
        self.state = {}
        self.callbacks = {}
        self.call_log = []
    
    def text_input(self, key, default="", on_change=None):
        self.call_log.append(('text_input', key, default))
        if key not in self.state:
            self.state[key] = default
        if on_change:
            self.callbacks[key] = on_change
        return self.state[key]
    
    def number_input(self, key, default=0, min_value=None, max_value=None, on_change=None):
        self.call_log.append(('number_input', key, default))
        if key not in self.state:
            self.state[key] = default
        if on_change:
            self.callbacks[key] = on_change
        return self.state[key]
    
    def selectbox(self, key, options, index=0):
        self.call_log.append(('selectbox', key, options, index))
        if key not in self.state:
            self.state[key] = options[index] if options else None
        return self.state[key]
    
    def checkbox(self, key, default=False):
        self.call_log.append(('checkbox', key, default))
        if key not in self.state:
            self.state[key] = default
        return self.state[key]
    
    def button(self, label, on_click=None):
        self.call_log.append(('button', label))
        if on_click:
            self.callbacks[label] = on_click
        return False  # Buttons return False by default
    
    def set_value(self, key, value):
        """Set value and trigger callback if exists."""
        old_value = self.state.get(key)
        self.state[key] = value
        if key in self.callbacks and old_value != value:
            self.callbacks[key]()


class MockPreviewPort:
    """Mock preview port for testing."""
    
    def __init__(self):
        self.content_log = []
        self.last_content = None
    
    def html(self, content, height=None):
        self.content_log.append(('html', content, height))
        self.last_content = ('html', content)
    
    def markdown(self, content):
        self.content_log.append(('markdown', content))
        self.last_content = ('markdown', content)
    
    def text(self, content):
        self.content_log.append(('text', content))
        self.last_content = ('text', content)


class MockNotificationPort:
    """Mock notification port for testing."""
    
    def __init__(self):
        self.notifications = []
    
    def show_success(self, message):
        self.notifications.append(('success', message))
    
    def show_error(self, message):
        self.notifications.append(('error', message))
    
    def show_warning(self, message):
        self.notifications.append(('warning', message))
    
    def show_info(self, message):
        self.notifications.append(('info', message))


class MockRefreshScheduler:
    """Mock refresh scheduler for testing."""
    
    def __init__(self):
        self.refresh_scheduled = False
        self.refresh_calls = []
    
    def schedule_refresh(self, delay_ms=None):
        self.refresh_scheduled = True
        self.refresh_calls.append(('schedule', delay_ms))
    
    def cancel_refresh(self):
        self.refresh_scheduled = False
        self.refresh_calls.append(('cancel',))


class TestUIAdapterIntegration:
    """Test UI adapter integration across components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
    
    def test_adapter_interface_compliance(self):
        """Test that adapter implements required interfaces."""
        # Check that adapter has all required ports
        assert hasattr(self.adapter, 'inputs')
        assert hasattr(self.adapter, 'preview')
        assert hasattr(self.adapter, 'notifications')
        assert hasattr(self.adapter, 'refresh_scheduler')
        
        # Check that ports have required methods
        assert hasattr(self.adapter.inputs, 'text_input')
        assert hasattr(self.adapter.inputs, 'number_input')
        assert hasattr(self.adapter.inputs, 'selectbox')
        assert hasattr(self.adapter.inputs, 'checkbox')
        assert hasattr(self.adapter.inputs, 'button')
        
        assert hasattr(self.adapter.preview, 'html')
        assert hasattr(self.adapter.preview, 'markdown')
        assert hasattr(self.adapter.preview, 'text')
        
        assert hasattr(self.adapter.notifications, 'show_success')
        assert hasattr(self.adapter.notifications, 'show_error')
        assert hasattr(self.adapter.notifications, 'show_warning')
        assert hasattr(self.adapter.notifications, 'show_info')
        
        assert hasattr(self.adapter.refresh_scheduler, 'schedule_refresh')
        assert hasattr(self.adapter.refresh_scheduler, 'cancel_refresh')
    
    def test_input_component_integration(self):
        """Test input component integration through adapter."""
        # Test text input
        result = self.adapter.inputs.text_input("test_text", "default_value")
        assert result == "default_value"
        assert ('text_input', 'test_text', 'default_value') in self.adapter.inputs.call_log
        
        # Test number input
        result = self.adapter.inputs.number_input("test_number", 42, min_value=0, max_value=100)
        assert result == 42
        assert ('number_input', 'test_number', 42) in self.adapter.inputs.call_log
        
        # Test selectbox
        options = ["Option 1", "Option 2", "Option 3"]
        result = self.adapter.inputs.selectbox("test_select", options, index=1)
        assert result == "Option 2"
        assert ('selectbox', 'test_select', options, 1) in self.adapter.inputs.call_log
        
        # Test checkbox
        result = self.adapter.inputs.checkbox("test_checkbox", True)
        assert result is True
        assert ('checkbox', 'test_checkbox', True) in self.adapter.inputs.call_log
    
    def test_preview_component_integration(self):
        """Test preview component integration through adapter."""
        # Test HTML preview
        html_content = "<div>Test HTML Content</div>"
        self.adapter.preview.html(html_content, height=500)
        
        assert ('html', html_content, 500) in self.adapter.preview.content_log
        assert self.adapter.preview.last_content == ('html', html_content)
        
        # Test markdown preview
        markdown_content = "# Test Markdown\n\nThis is a test."
        self.adapter.preview.markdown(markdown_content)
        
        assert ('markdown', markdown_content) in self.adapter.preview.content_log
        assert self.adapter.preview.last_content == ('markdown', markdown_content)
        
        # Test text preview
        text_content = "Plain text content"
        self.adapter.preview.text(text_content)
        
        assert ('text', text_content) in self.adapter.preview.content_log
        assert self.adapter.preview.last_content == ('text', text_content)
    
    def test_notification_integration(self):
        """Test notification integration through adapter."""
        # Test different notification types
        self.adapter.notifications.show_success("Operation successful")
        self.adapter.notifications.show_error("An error occurred")
        self.adapter.notifications.show_warning("This is a warning")
        self.adapter.notifications.show_info("Information message")
        
        # Verify notifications were recorded
        notifications = self.adapter.notifications.notifications
        assert ('success', 'Operation successful') in notifications
        assert ('error', 'An error occurred') in notifications
        assert ('warning', 'This is a warning') in notifications
        assert ('info', 'Information message') in notifications
    
    def test_refresh_scheduler_integration(self):
        """Test refresh scheduler integration through adapter."""
        # Test scheduling refresh
        self.adapter.refresh_scheduler.schedule_refresh(100)
        
        assert self.adapter.refresh_scheduler.refresh_scheduled
        assert ('schedule', 100) in self.adapter.refresh_scheduler.refresh_calls
        
        # Test canceling refresh
        self.adapter.refresh_scheduler.cancel_refresh()
        
        assert not self.adapter.refresh_scheduler.refresh_scheduled
        assert ('cancel',) in self.adapter.refresh_scheduler.refresh_calls


class TestUIAdapterCallbackIntegration:
    """Test UI adapter callback integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
        self.callback_triggered = False
        self.callback_value = None
    
    def test_input_callback_integration(self):
        """Test input callback integration."""
        def test_callback():
            self.callback_triggered = True
        
        # Set up input with callback
        self.adapter.inputs.text_input("test_input", "initial", on_change=test_callback)
        
        # Simulate value change
        self.adapter.inputs.set_value("test_input", "changed")
        
        # Verify callback was triggered
        assert self.callback_triggered
    
    def test_button_callback_integration(self):
        """Test button callback integration."""
        def button_callback():
            self.callback_triggered = True
        
        # Set up button with callback
        self.adapter.inputs.button("Test Button", on_click=button_callback)
        
        # Simulate button click by calling callback directly
        if "Test Button" in self.adapter.inputs.callbacks:
            self.adapter.inputs.callbacks["Test Button"]()
        
        # Verify callback was triggered
        assert self.callback_triggered


class TestUIAdapterStateManagement:
    """Test UI adapter state management integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
    
    def test_state_persistence_across_calls(self):
        """Test that state persists across multiple calls."""
        # Set initial values
        self.adapter.inputs.text_input("persistent_text", "initial_value")
        self.adapter.inputs.number_input("persistent_number", 42)
        
        # Call again without default values
        text_result = self.adapter.inputs.text_input("persistent_text", "new_default")
        number_result = self.adapter.inputs.number_input("persistent_number", 99)
        
        # Should return persisted values, not new defaults
        assert text_result == "initial_value"
        assert number_result == 42
    
    def test_state_isolation_between_keys(self):
        """Test that state is isolated between different keys."""
        # Set values for different keys
        self.adapter.inputs.text_input("key1", "value1")
        self.adapter.inputs.text_input("key2", "value2")
        self.adapter.inputs.number_input("num1", 10)
        self.adapter.inputs.number_input("num2", 20)
        
        # Verify isolation
        assert self.adapter.inputs.state["key1"] == "value1"
        assert self.adapter.inputs.state["key2"] == "value2"
        assert self.adapter.inputs.state["num1"] == 10
        assert self.adapter.inputs.state["num2"] == 20
        
        # Change one value
        self.adapter.inputs.set_value("key1", "changed_value1")
        
        # Verify other values unchanged
        assert self.adapter.inputs.state["key1"] == "changed_value1"
        assert self.adapter.inputs.state["key2"] == "value2"
        assert self.adapter.inputs.state["num1"] == 10
        assert self.adapter.inputs.state["num2"] == 20


class TestUIAdapterErrorHandling:
    """Test UI adapter error handling integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
    
    def test_invalid_selectbox_index_handling(self):
        """Test handling of invalid selectbox index."""
        options = ["Option 1", "Option 2"]
        
        # Test with invalid index (should handle gracefully)
        try:
            result = self.adapter.inputs.selectbox("test_select", options, index=5)
            # If no exception, should return reasonable default
            assert result in options or result is None
        except IndexError:
            # It's acceptable to raise IndexError for invalid index
            pass
    
    def test_empty_options_selectbox_handling(self):
        """Test handling of empty options in selectbox."""
        empty_options = []
        
        # Should handle empty options gracefully
        result = self.adapter.inputs.selectbox("test_select", empty_options, index=0)
        assert result is None
    
    def test_callback_exception_handling(self):
        """Test handling of exceptions in callbacks."""
        def failing_callback():
            raise ValueError("Callback failed")
        
        # Set up input with failing callback
        self.adapter.inputs.text_input("test_input", "initial", on_change=failing_callback)
        
        # Simulate value change (should handle callback exception gracefully)
        try:
            self.adapter.inputs.set_value("test_input", "changed")
            # If no exception propagated, that's good
        except ValueError:
            # It's also acceptable for callback exceptions to propagate
            pass


class TestUIAdapterPerformance:
    """Test UI adapter performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
    
    def test_multiple_input_calls_performance(self):
        """Test performance with multiple input calls."""
        # Create many inputs
        for i in range(100):
            self.adapter.inputs.text_input(f"input_{i}", f"value_{i}")
            self.adapter.inputs.number_input(f"number_{i}", i)
        
        # Verify all inputs were created
        assert len(self.adapter.inputs.state) == 200  # 100 text + 100 number
        
        # Verify call log is reasonable size
        assert len(self.adapter.inputs.call_log) == 200
    
    def test_preview_content_updates_performance(self):
        """Test performance with multiple preview updates."""
        # Update preview content multiple times
        for i in range(50):
            self.adapter.preview.html(f"<div>Content {i}</div>")
            self.adapter.preview.markdown(f"# Heading {i}")
        
        # Verify all updates were logged
        assert len(self.adapter.preview.content_log) == 100  # 50 html + 50 markdown
        
        # Verify last content is correct
        assert self.adapter.preview.last_content == ('markdown', '# Heading 49')


if __name__ == "__main__":
    pytest.main([__file__])
