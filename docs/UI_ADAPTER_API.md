# UI Adapter System API Reference

## Overview

The UI Adapter system (`ui/ports.py`) provides a framework-agnostic abstraction layer that allows UI components to work with any underlying UI framework. This enables testing, framework migration, and consistent component behavior.

## Core Interfaces

### UIAdapter Interface

The main adapter interface that all UI frameworks must implement:

```python
class UIAdapter(ABC):
    """Abstract base class for UI framework adapters."""
    
    @abstractmethod
    def get_inputs_port(self) -> InputsPort:
        """Get the inputs port for this adapter."""
        pass
    
    @abstractmethod
    def get_preview_port(self) -> PreviewPort:
        """Get the preview port for this adapter."""
        pass
    
    @abstractmethod
    def get_notification_port(self) -> NotificationPort:
        """Get the notification port for this adapter."""
        pass
    
    @abstractmethod
    def get_refresh_port(self) -> RefreshPort:
        """Get the refresh port for this adapter."""
        pass
```

### InputsPort Interface

Handles all user input operations:

```python
class InputsPort(ABC):
    """Port for handling user inputs."""
    
    @abstractmethod
    def text_input(self, label: str, value: str = "", key: Optional[str] = None) -> str:
        """Create a text input field."""
        pass
    
    @abstractmethod
    def number_input(self, label: str, value: float, min_value: float, 
                    max_value: float, step: float, key: Optional[str] = None) -> float:
        """Create a number input field."""
        pass
    
    @abstractmethod
    def selectbox(self, label: str, options: List[str], index: int = 0, 
                 key: Optional[str] = None) -> str:
        """Create a select box."""
        pass
    
    @abstractmethod
    def checkbox(self, label: str, value: bool = False, 
                key: Optional[str] = None) -> bool:
        """Create a checkbox."""
        pass
    
    @abstractmethod
    def button(self, label: str, key: Optional[str] = None) -> bool:
        """Create a button."""
        pass
    
    @abstractmethod
    def file_uploader(self, label: str, type: List[str], 
                     key: Optional[str] = None) -> Optional[Any]:
        """Create a file uploader."""
        pass
```

### PreviewPort Interface

Handles preview display and navigation:

```python
class PreviewPort(ABC):
    """Port for handling preview display."""
    
    @abstractmethod
    def display_html(self, html: str, height: Optional[int] = None) -> None:
        """Display HTML content."""
        pass
    
    @abstractmethod
    def display_markdown(self, markdown: str) -> None:
        """Display markdown content."""
        pass
    
    @abstractmethod
    def display_error(self, message: str) -> None:
        """Display an error message."""
        pass
    
    @abstractmethod
    def display_info(self, message: str) -> None:
        """Display an info message."""
        pass
    
    @abstractmethod
    def display_success(self, message: str) -> None:
        """Display a success message."""
        pass
    
    @abstractmethod
    def pagination_controls(self, current_page: int, total_pages: int, 
                           key_prefix: str) -> Optional[int]:
        """Display pagination controls."""
        pass
```

### NotificationPort Interface

Handles user notifications and feedback:

```python
class NotificationPort(ABC):
    """Port for handling notifications."""
    
    @abstractmethod
    def show_success(self, message: str) -> None:
        """Show a success notification."""
        pass
    
    @abstractmethod
    def show_error(self, message: str) -> None:
        """Show an error notification."""
        pass
    
    @abstractmethod
    def show_warning(self, message: str) -> None:
        """Show a warning notification."""
        pass
    
    @abstractmethod
    def show_info(self, message: str) -> None:
        """Show an info notification."""
        pass
```

### RefreshPort Interface

Handles UI refresh and rerun operations:

```python
class RefreshPort(ABC):
    """Port for handling UI refresh operations."""
    
    @abstractmethod
    def rerun(self) -> None:
        """Trigger a UI rerun/refresh."""
        pass
    
    @abstractmethod
    def schedule_rerun(self, delay_ms: int = 0) -> None:
        """Schedule a UI rerun after a delay."""
        pass
```

## Adapter Implementations

### StreamlitAdapter

Production adapter for Streamlit framework:

```python
class StreamlitAdapter(UIAdapter):
    """Streamlit implementation of UIAdapter."""
    
    def __init__(self):
        self._inputs_port = StreamlitInputsPort()
        self._preview_port = StreamlitPreviewPort()
        self._notification_port = StreamlitNotificationPort()
        self._refresh_port = StreamlitRefreshPort()
    
    def get_inputs_port(self) -> InputsPort:
        return self._inputs_port
    
    def get_preview_port(self) -> PreviewPort:
        return self._preview_port
    
    def get_notification_port(self) -> NotificationPort:
        return self._notification_port
    
    def get_refresh_port(self) -> RefreshPort:
        return self._refresh_port
```

### FakeAdapter

Testing adapter for unit and integration tests:

```python
class FakeAdapter(UIAdapter):
    """Fake implementation for testing."""
    
    def __init__(self):
        self.inputs = {}
        self.displayed_content = []
        self.notifications = []
        self.refresh_calls = 0
    
    def set_input_value(self, key: str, value: Any) -> None:
        """Set input value for testing."""
        self.inputs[key] = value
    
    def get_displayed_content(self) -> List[str]:
        """Get all displayed content for verification."""
        return self.displayed_content.copy()
    
    def get_notifications(self) -> List[Dict[str, str]]:
        """Get all notifications for verification."""
        return self.notifications.copy()
    
    def clear_state(self) -> None:
        """Clear adapter state for test isolation."""
        self.inputs.clear()
        self.displayed_content.clear()
        self.notifications.clear()
        self.refresh_calls = 0
```

## Usage Examples

### Basic Component Usage

```python
from ui.ports import get_ui_adapter

def render_input_section():
    """Render input section using UI adapter."""
    adapter = get_ui_adapter()
    inputs = adapter.get_inputs_port()
    
    # Get user inputs
    text = inputs.text_input("Enter Chinese text:", key="input_text")
    rows = inputs.number_input("Rows:", value=3, min_value=1, max_value=10, key="rows")
    auto_fill = inputs.checkbox("Auto-fill cards", value=True, key="auto_fill")
    
    if inputs.button("Generate Cards", key="generate"):
        # Process inputs
        process_user_input(text, rows, auto_fill)
```

### Preview Display

```python
def render_preview_section(html_content: str):
    """Render preview section using UI adapter."""
    adapter = get_ui_adapter()
    preview = adapter.get_preview_port()
    
    try:
        # Display preview
        preview.display_html(html_content, height=600)
        
        # Show pagination if needed
        if total_pages > 1:
            new_page = preview.pagination_controls(
                current_page=current_page,
                total_pages=total_pages,
                key_prefix="preview"
            )
            if new_page is not None:
                navigate_to_page(new_page)
                
    except Exception as e:
        preview.display_error(f"Error displaying preview: {e}")
```

### Notification Handling

```python
def handle_export_operation():
    """Handle export with notifications."""
    adapter = get_ui_adapter()
    notifications = adapter.get_notification_port()
    
    try:
        # Perform export
        result = export_cards_to_pdf()
        
        if result.success:
            notifications.show_success("Export completed successfully!")
        else:
            notifications.show_warning(f"Export completed with warnings: {result.warnings}")
            
    except Exception as e:
        notifications.show_error(f"Export failed: {e}")
```

## Testing with UI Adapters

### Unit Testing

```python
import pytest
from ui.ports import FakeAdapter, set_ui_adapter

@pytest.fixture
def fake_adapter():
    """Provide fake adapter for testing."""
    adapter = FakeAdapter()
    set_ui_adapter(adapter)
    yield adapter
    # Cleanup after test
    adapter.clear_state()

def test_input_component(fake_adapter):
    """Test input component behavior."""
    # Set up test inputs
    fake_adapter.set_input_value("test_input", "test value")
    
    # Run component
    result = render_input_component()
    
    # Verify behavior
    assert result == "test value"
    
    # Check displayed content
    content = fake_adapter.get_displayed_content()
    assert any("Input field" in item for item in content)
```

### Integration Testing

```python
def test_complete_workflow(fake_adapter):
    """Test complete user workflow."""
    # Set up inputs
    fake_adapter.set_input_value("input_text", "你好 世界")
    fake_adapter.set_input_value("rows", 2)
    fake_adapter.set_input_value("cols", 2)
    fake_adapter.set_input_value("generate_button", True)
    
    # Run workflow
    run_complete_workflow()
    
    # Verify results
    content = fake_adapter.get_displayed_content()
    notifications = fake_adapter.get_notifications()
    
    assert any("preview" in item.lower() for item in content)
    assert any(notif["type"] == "success" for notif in notifications)
```

### Event-Driven Testing

```python
def test_pagination_navigation(fake_adapter):
    """Test pagination navigation."""
    # Set up multi-page content
    setup_multipage_content(total_pages=5)
    
    # Simulate page navigation
    fake_adapter.set_input_value("page_next", True)
    
    # Run navigation
    handle_pagination()
    
    # Verify page change
    assert get_current_page() == 2
    
    # Verify refresh was triggered
    assert fake_adapter.refresh_calls > 0
```

## Advanced Features

### Custom Adapter Implementation

```python
class WebAdapter(UIAdapter):
    """Web-based adapter for browser deployment."""
    
    def __init__(self, dom_manager):
        self.dom = dom_manager
        self._inputs_port = WebInputsPort(dom_manager)
        self._preview_port = WebPreviewPort(dom_manager)
        self._notification_port = WebNotificationPort(dom_manager)
        self._refresh_port = WebRefreshPort(dom_manager)
    
    # Implement required methods...
```

### Adapter Configuration

```python
# Configure adapter based on environment
def configure_ui_adapter():
    """Configure UI adapter based on environment."""
    if is_testing_environment():
        adapter = FakeAdapter()
    elif is_web_deployment():
        adapter = WebAdapter(get_dom_manager())
    else:
        adapter = StreamlitAdapter()
    
    set_ui_adapter(adapter)
    return adapter
```

### Performance Monitoring

```python
class MonitoredAdapter(UIAdapter):
    """Adapter wrapper with performance monitoring."""
    
    def __init__(self, base_adapter: UIAdapter):
        self.base_adapter = base_adapter
        self.metrics = {}
    
    def get_inputs_port(self) -> InputsPort:
        return MonitoredInputsPort(
            self.base_adapter.get_inputs_port(),
            self.metrics
        )
    
    # Wrap other ports similarly...
```

## Best Practices

### Component Design

1. **Use Adapters Consistently**: Always use adapter interfaces, never direct framework calls
2. **Handle Errors Gracefully**: Wrap adapter calls in try-catch blocks
3. **Test Both Paths**: Test with both real and fake adapters
4. **Keep Components Simple**: Each component should have a single responsibility

### Performance Considerations

1. **Minimize Adapter Calls**: Cache adapter references when possible
2. **Batch Operations**: Group related UI operations together
3. **Lazy Loading**: Only create UI elements when needed
4. **Memory Management**: Clean up adapter state in tests

### Error Handling

1. **Graceful Degradation**: Provide fallbacks for adapter failures
2. **User Feedback**: Use notification port for error communication
3. **Logging**: Log adapter errors for debugging
4. **Recovery**: Implement recovery mechanisms for transient failures

---

**Document Version**: 1.0  
**Last Updated**: August 2024  
**Next Review**: November 2024
