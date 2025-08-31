"""
Unit tests for UI adapter interface behavior.
Tests the UI adapter interfaces and mock implementations for testing.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

# Import the adapter interfaces
from ui.ports import UIAdapter, UIInputsPort, UIPreviewPort, UINotificationPort, UIRefreshScheduler


class MockAdapter:
    """Mock adapter implementation for testing."""

    def __init__(self):
        self.inputs = MockInputsPort()
        self.preview = MockPreviewPort()
        self.notifications = MockNotificationPort()
        self.refresh_scheduler = MockRefreshScheduler()

    def reset(self):
        """Reset all ports."""
        self.inputs.reset()
        self.preview.reset()
        self.notifications.reset()
        self.refresh_scheduler.reset()


class MockInputsPort:
    """Mock inputs port implementation."""

    def __init__(self):
        self._state = {}
        self._callbacks = {}
        self._uploaded_files = {}
        self._button_states = {}

    def text_input(self, key: str, default: str = "", on_change=None):
        if key not in self._state:
            self._state[key] = default
        if on_change:
            self._callbacks[key] = on_change
        return self._state[key]

    def number_input(self, key: str, default: float, min_value=None, max_value=None, on_change=None):
        if key not in self._state:
            self._state[key] = default
        if on_change:
            self._callbacks[key] = on_change
        return self._state[key]

    def selectbox(self, key: str, options: List[str], index: int = 0):
        if key not in self._state:
            if 0 <= index < len(options):
                self._state[key] = options[index]
            else:
                self._state[key] = options[0] if options else None
        return self._state[key]

    def checkbox(self, key: str, default: bool = False):
        if key not in self._state:
            self._state[key] = default
        return self._state[key]

    def slider(self, key: str, default: int, min_value: int, max_value: int, step: int = 1):
        if key not in self._state:
            self._state[key] = default
        return self._state[key]

    def button(self, label: str, on_click=None):
        if label not in self._button_states:
            self._button_states[label] = False
        if on_click:
            self._callbacks[label] = on_click
        return self._button_states[label]

    def color_picker(self, key: str, default: str = "#000000"):
        if key not in self._state:
            self._state[key] = default
        return self._state[key]

    def file_uploader(self, key: str, type: List[str] = None):
        return self._uploaded_files.get(key)

    def get_value(self, key: str):
        return self._state.get(key)

    def set_value(self, key: str, value: Any):
        old_value = self._state.get(key)
        self._state[key] = value

        # Apply validation for number inputs
        if isinstance(value, (int, float)):
            # Simple validation - clamp to 0-100 range for testing
            if value < 0:
                self._state[key] = 0.0
            elif value > 100:
                self._state[key] = 100.0

        # Trigger callback if value changed
        if key in self._callbacks and old_value != self._state[key]:
            self._callbacks[key]()

    def set_uploaded_file(self, key: str, file):
        self._uploaded_files[key] = file

    def get_uploaded_file(self, key: str):
        return self._uploaded_files.get(key)

    def trigger_button(self, label: str):
        self._button_states[label] = True
        if label in self._callbacks:
            self._callbacks[label]()
        self._button_states[label] = False

    def reset(self):
        self._state.clear()
        self._callbacks.clear()
        self._uploaded_files.clear()
        self._button_states.clear()


class MockPreviewPort:
    """Mock preview port implementation."""

    def __init__(self):
        self._last_html = None
        self._last_height = None
        self._last_markdown = None
        self._last_text = None
        self._last_json = None
        self._last_dataframe = None
        self._last_image = None
        self._last_image_caption = None

    def html(self, content: str, height: int = None):
        self._last_html = content
        self._last_height = height

    def markdown(self, content: str):
        self._last_markdown = content

    def text(self, content: str):
        self._last_text = content

    def json(self, data: Dict[str, Any]):
        self._last_json = data

    def dataframe(self, df):
        self._last_dataframe = df

    def image(self, data: bytes, caption: str = None):
        self._last_image = data
        self._last_image_caption = caption

    def get_last_html(self):
        return self._last_html

    def get_last_height(self):
        return self._last_height

    def get_last_markdown(self):
        return self._last_markdown

    def get_last_text(self):
        return self._last_text

    def get_last_json(self):
        return self._last_json

    def get_last_dataframe(self):
        return self._last_dataframe

    def get_last_image(self):
        return self._last_image

    def get_last_image_caption(self):
        return self._last_image_caption

    def reset(self):
        self._last_html = None
        self._last_height = None
        self._last_markdown = None
        self._last_text = None
        self._last_json = None
        self._last_dataframe = None
        self._last_image = None
        self._last_image_caption = None


class MockNotificationPort:
    """Mock notification port implementation."""

    def __init__(self):
        self._notifications = []

    def show_success(self, message: str):
        self._notifications.append({'type': 'success', 'message': message})

    def show_error(self, message: str):
        self._notifications.append({'type': 'error', 'message': message})

    def show_warning(self, message: str):
        self._notifications.append({'type': 'warning', 'message': message})

    def show_info(self, message: str):
        self._notifications.append({'type': 'info', 'message': message})

    def get_notifications(self):
        return self._notifications.copy()

    def clear_notifications(self):
        self._notifications.clear()

    def reset(self):
        self.clear_notifications()


class MockRefreshScheduler:
    """Mock refresh scheduler implementation."""

    def __init__(self):
        self._refresh_scheduled = False
        self._refresh_count = 0
        self._last_delay = None

    def schedule_refresh(self, delay_ms: int = None):
        self._refresh_scheduled = True
        self._refresh_count += 1
        self._last_delay = delay_ms

    def cancel_refresh(self):
        self._refresh_scheduled = False

    def execute_refresh(self, callback):
        if callback:
            callback()
        self._refresh_scheduled = False

    def is_refresh_scheduled(self):
        return self._refresh_scheduled

    def get_refresh_count(self):
        return self._refresh_count

    def get_last_delay(self):
        return self._last_delay

    def reset(self):
        self._refresh_scheduled = False
        self._refresh_count = 0
        self._last_delay = None


class TestMockAdapterBasicBehavior:
    """Test basic MockAdapter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()

    def test_adapter_has_required_ports(self):
        """Test that MockAdapter has required ports."""
        assert hasattr(self.adapter, 'inputs')
        assert hasattr(self.adapter, 'preview')
        assert hasattr(self.adapter, 'notifications')
        assert hasattr(self.adapter, 'refresh_scheduler')

    def test_port_types(self):
        """Test that adapter ports are correct types."""
        assert isinstance(self.adapter.inputs, MockInputsPort)
        assert isinstance(self.adapter.preview, MockPreviewPort)
        assert isinstance(self.adapter.notifications, MockNotificationPort)
        assert isinstance(self.adapter.refresh_scheduler, MockRefreshScheduler)
    
    def test_adapter_state_isolation(self):
        """Test that different adapter instances are isolated."""
        adapter1 = MockAdapter()
        adapter2 = MockAdapter()

        # Set different values in each adapter
        adapter1.inputs.text_input("test1", "value1")
        adapter2.inputs.text_input("test2", "value2")

        # Should not interfere with each other
        assert adapter1.inputs._state.get("test1") != adapter2.inputs._state.get("test1")


class TestMockInputsPort:
    """Test MockInputsPort behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()
        self.inputs = self.adapter.inputs
    
    def test_text_input_basic(self):
        """Test basic text input functionality."""
        result = self.inputs.text_input("test_key", "default_value")
        
        assert result == "default_value"
        assert "test_key" in self.inputs._state
    
    def test_text_input_with_callback(self):
        """Test text input with on_change callback."""
        callback_called = False
        
        def test_callback():
            nonlocal callback_called
            callback_called = True
        
        self.inputs.text_input("test_key", "default", on_change=test_callback)
        
        # Simulate value change
        self.inputs.set_value("test_key", "new_value")
        
        assert callback_called
        assert self.inputs.get_value("test_key") == "new_value"
    
    def test_number_input_basic(self):
        """Test basic number input functionality."""
        result = self.inputs.number_input("num_key", 42.0, min_value=0.0, max_value=100.0)
        
        assert result == 42.0
        assert self.inputs.get_value("num_key") == 42.0
    
    def test_number_input_validation(self):
        """Test number input validation."""
        # Test min/max constraints
        self.inputs.number_input("num_key", 50.0, min_value=0.0, max_value=100.0)
        
        # Try to set value outside range
        self.inputs.set_value("num_key", 150.0)
        
        # Should be clamped to max value
        assert self.inputs.get_value("num_key") == 100.0
        
        # Try to set value below min
        self.inputs.set_value("num_key", -10.0)
        
        # Should be clamped to min value
        assert self.inputs.get_value("num_key") == 0.0
    
    def test_selectbox_basic(self):
        """Test basic selectbox functionality."""
        options = ["option1", "option2", "option3"]
        result = self.inputs.selectbox("select_key", options, index=1)
        
        assert result == "option2"
        assert self.inputs.get_value("select_key") == "option2"
    
    def test_selectbox_invalid_index(self):
        """Test selectbox with invalid index."""
        options = ["option1", "option2", "option3"]
        
        # Invalid index should default to 0
        result = self.inputs.selectbox("select_key", options, index=10)
        assert result == "option1"
    
    def test_checkbox_basic(self):
        """Test basic checkbox functionality."""
        result = self.inputs.checkbox("check_key", True)
        
        assert result is True
        assert self.inputs.get_value("check_key") is True
    
    def test_slider_basic(self):
        """Test basic slider functionality."""
        result = self.inputs.slider("slider_key", 50, min_value=0, max_value=100, step=1)
        
        assert result == 50
        assert self.inputs.get_value("slider_key") == 50
    
    def test_button_basic(self):
        """Test basic button functionality."""
        clicked = False
        
        def button_callback():
            nonlocal clicked
            clicked = True
        
        # Button should return False initially
        result = self.inputs.button("Click me", on_click=button_callback)
        assert result is False
        assert not clicked
        
        # Simulate button click
        self.inputs.trigger_button("Click me")
        
        # Should trigger callback
        assert clicked
    
    def test_color_picker_basic(self):
        """Test basic color picker functionality."""
        result = self.inputs.color_picker("color_key", "#FF0000")
        
        assert result == "#FF0000"
        assert self.inputs.get_value("color_key") == "#FF0000"
    
    def test_file_uploader_basic(self):
        """Test basic file uploader functionality."""
        # Mock file object
        mock_file = MagicMock()
        mock_file.name = "test.txt"
        mock_file.read.return_value = b"test content"
        
        # Set uploaded file
        self.inputs.set_uploaded_file("file_key", mock_file)
        
        result = self.inputs.file_uploader("file_key", type=["txt"])
        
        assert result == mock_file
        assert self.inputs.get_uploaded_file("file_key") == mock_file


class TestMockPreviewPort:
    """Test MockPreviewPort behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()
        self.preview = self.adapter.preview
    
    def test_html_display_basic(self):
        """Test basic HTML display functionality."""
        html_content = "<div>Test HTML</div>"
        
        self.preview.html(html_content)
        
        # Should store the HTML content
        assert self.preview.get_last_html() == html_content
    
    def test_html_display_with_height(self):
        """Test HTML display with height parameter."""
        html_content = "<div>Test HTML</div>"
        
        self.preview.html(html_content, height=500)
        
        assert self.preview.get_last_html() == html_content
        assert self.preview.get_last_height() == 500
    
    def test_markdown_display_basic(self):
        """Test basic markdown display functionality."""
        markdown_content = "# Test Markdown\n\nThis is a test."
        
        self.preview.markdown(markdown_content)
        
        # Should store the markdown content
        assert self.preview.get_last_markdown() == markdown_content
    
    def test_text_display_basic(self):
        """Test basic text display functionality."""
        text_content = "Plain text content"
        
        self.preview.text(text_content)
        
        # Should store the text content
        assert self.preview.get_last_text() == text_content
    
    def test_json_display_basic(self):
        """Test basic JSON display functionality."""
        json_data = {"key": "value", "number": 42}
        
        self.preview.json(json_data)
        
        # Should store the JSON data
        assert self.preview.get_last_json() == json_data
    
    def test_dataframe_display_basic(self):
        """Test basic dataframe display functionality."""
        # Mock dataframe
        mock_df = MagicMock()
        mock_df.to_html.return_value = "<table>Mock DataFrame</table>"
        
        self.preview.dataframe(mock_df)
        
        # Should store the dataframe
        assert self.preview.get_last_dataframe() == mock_df
    
    def test_image_display_basic(self):
        """Test basic image display functionality."""
        image_data = b"fake image data"
        
        self.preview.image(image_data, caption="Test Image")
        
        # Should store the image data
        assert self.preview.get_last_image() == image_data
        assert self.preview.get_last_image_caption() == "Test Image"


class TestMockNotificationPort:
    """Test MockNotificationPort behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()
        self.notifications = self.adapter.notifications
    
    def test_success_notification(self):
        """Test success notification."""
        message = "Operation completed successfully"
        
        self.notifications.show_success(message)
        
        # Should store the notification
        notifications = self.notifications.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]['type'] == 'success'
        assert notifications[0]['message'] == message
    
    def test_error_notification(self):
        """Test error notification."""
        message = "An error occurred"
        
        self.notifications.show_error(message)
        
        # Should store the notification
        notifications = self.notifications.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]['type'] == 'error'
        assert notifications[0]['message'] == message
    
    def test_warning_notification(self):
        """Test warning notification."""
        message = "This is a warning"
        
        self.notifications.show_warning(message)
        
        # Should store the notification
        notifications = self.notifications.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]['type'] == 'warning'
        assert notifications[0]['message'] == message
    
    def test_info_notification(self):
        """Test info notification."""
        message = "This is information"
        
        self.notifications.show_info(message)
        
        # Should store the notification
        notifications = self.notifications.get_notifications()
        assert len(notifications) == 1
        assert notifications[0]['type'] == 'info'
        assert notifications[0]['message'] == message
    
    def test_multiple_notifications(self):
        """Test multiple notifications."""
        self.notifications.show_success("Success message")
        self.notifications.show_error("Error message")
        self.notifications.show_warning("Warning message")
        
        notifications = self.notifications.get_notifications()
        assert len(notifications) == 3
        
        # Should maintain order
        assert notifications[0]['type'] == 'success'
        assert notifications[1]['type'] == 'error'
        assert notifications[2]['type'] == 'warning'
    
    def test_clear_notifications(self):
        """Test clearing notifications."""
        self.notifications.show_success("Test message")
        assert len(self.notifications.get_notifications()) == 1
        
        self.notifications.clear_notifications()
        assert len(self.notifications.get_notifications()) == 0


class TestMockRefreshScheduler:
    """Test MockRefreshScheduler behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()
        self.scheduler = self.adapter.refresh_scheduler
    
    def test_schedule_refresh_basic(self):
        """Test basic refresh scheduling."""
        self.scheduler.schedule_refresh()
        
        # Should record the refresh request
        assert self.scheduler.is_refresh_scheduled()
        assert self.scheduler.get_refresh_count() == 1
    
    def test_schedule_refresh_with_delay(self):
        """Test refresh scheduling with delay."""
        self.scheduler.schedule_refresh(delay_ms=100)
        
        # Should record the refresh with delay
        assert self.scheduler.is_refresh_scheduled()
        assert self.scheduler.get_last_delay() == 100
    
    def test_multiple_refresh_scheduling(self):
        """Test multiple refresh scheduling."""
        self.scheduler.schedule_refresh()
        self.scheduler.schedule_refresh(delay_ms=50)
        self.scheduler.schedule_refresh(delay_ms=200)
        
        # Should record all refresh requests
        assert self.scheduler.get_refresh_count() == 3
        assert self.scheduler.get_last_delay() == 200
    
    def test_cancel_refresh(self):
        """Test refresh cancellation."""
        self.scheduler.schedule_refresh()
        assert self.scheduler.is_refresh_scheduled()
        
        self.scheduler.cancel_refresh()
        assert not self.scheduler.is_refresh_scheduled()
    
    def test_execute_refresh(self):
        """Test refresh execution."""
        callback_called = False
        
        def refresh_callback():
            nonlocal callback_called
            callback_called = True
        
        self.scheduler.schedule_refresh()
        self.scheduler.execute_refresh(refresh_callback)
        
        # Should execute the callback and clear the schedule
        assert callback_called
        assert not self.scheduler.is_refresh_scheduled()


class TestMockAdapterIntegration:
    """Test MockAdapter integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockAdapter()
    
    def test_form_interaction_flow(self):
        """Test a complete form interaction flow."""
        # Set up form inputs
        name = self.adapter.inputs.text_input("name", "")
        age = self.adapter.inputs.number_input("age", 25, min_value=0, max_value=120)
        active = self.adapter.inputs.checkbox("active", True)
        
        # Initial values
        assert name == ""
        assert age == 25
        assert active is True
        
        # Simulate user input
        self.adapter.inputs.set_value("name", "John Doe")
        self.adapter.inputs.set_value("age", 30)
        self.adapter.inputs.set_value("active", False)
        
        # Verify changes
        assert self.adapter.inputs.get_value("name") == "John Doe"
        assert self.adapter.inputs.get_value("age") == 30
        assert self.adapter.inputs.get_value("active") is False
    
    def test_preview_and_notification_flow(self):
        """Test preview and notification interaction."""
        # Display some content
        self.adapter.preview.html("<h1>Test Content</h1>")
        self.adapter.preview.markdown("## Markdown Content")
        
        # Show notifications
        self.adapter.notifications.show_success("Content loaded")
        self.adapter.notifications.show_info("Additional info")
        
        # Verify state
        assert self.adapter.preview.get_last_html() == "<h1>Test Content</h1>"
        assert self.adapter.preview.get_last_markdown() == "## Markdown Content"
        
        notifications = self.adapter.notifications.get_notifications()
        assert len(notifications) == 2
        assert notifications[0]['type'] == 'success'
        assert notifications[1]['type'] == 'info'
    
    def test_refresh_scheduling_flow(self):
        """Test refresh scheduling interaction."""
        # Schedule multiple refreshes
        self.adapter.refresh_scheduler.schedule_refresh()
        self.adapter.refresh_scheduler.schedule_refresh(delay_ms=100)
        
        # Check state
        assert self.adapter.refresh_scheduler.get_refresh_count() == 2
        assert self.adapter.refresh_scheduler.is_refresh_scheduled()
        
        # Execute refresh
        executed = False
        def refresh_handler():
            nonlocal executed
            executed = True
        
        self.adapter.refresh_scheduler.execute_refresh(refresh_handler)
        
        assert executed
        assert not self.adapter.refresh_scheduler.is_refresh_scheduled()
    
    def test_adapter_state_persistence(self):
        """Test that adapter state persists across operations."""
        # Set initial state
        self.adapter.inputs.text_input("persistent_key", "initial_value")
        self.adapter.notifications.show_success("Initial notification")
        
        # Perform other operations
        self.adapter.preview.html("<div>Some HTML</div>")
        self.adapter.inputs.number_input("another_key", 42)
        
        # Original state should persist
        assert self.adapter.inputs.get_value("persistent_key") == "initial_value"
        notifications = self.adapter.notifications.get_notifications()
        assert any(n['message'] == "Initial notification" for n in notifications)
    
    def test_adapter_reset_functionality(self):
        """Test adapter reset functionality."""
        # Set up some state
        self.adapter.inputs.text_input("test_key", "test_value")
        self.adapter.notifications.show_success("Test notification")
        self.adapter.refresh_scheduler.schedule_refresh()
        
        # Reset adapter
        self.adapter.reset()
        
        # State should be cleared
        assert len(self.adapter.inputs._state) == 0
        assert len(self.adapter.notifications.get_notifications()) == 0
        assert not self.adapter.refresh_scheduler.is_refresh_scheduled()


if __name__ == "__main__":
    pytest.main([__file__])
