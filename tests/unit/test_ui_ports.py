"""
Unit tests for ui/ports.py
Tests UI adapter pattern implementation.
"""

import pytest
from unittest.mock import patch, MagicMock

from ui.ports import (
    ComponentConfig, NotificationLevel, UIEvent,
    FakeAdapter, FakeInputsAdapter, FakePreviewAdapter,
    FakeNotificationAdapter, FakeLayoutAdapter, FakeRefreshAdapter,
    get_ui_adapter, set_ui_adapter, reset_ui_adapter
)


class TestComponentConfig:
    """Test ComponentConfig dataclass."""
    
    def test_component_config_creation(self):
        """Test ComponentConfig creation."""
        config = ComponentConfig(
            key="test_key",
            label="Test Label",
            help_text="Test help",
            disabled=True,
            visible=False
        )
        
        assert config.key == "test_key"
        assert config.label == "Test Label"
        assert config.help_text == "Test help"
        assert config.disabled is True
        assert config.visible is False
    
    def test_component_config_defaults(self):
        """Test ComponentConfig default values."""
        config = ComponentConfig(key="test", label="Test")
        
        assert config.help_text is None
        assert config.disabled is False
        assert config.visible is True


class TestNotificationLevel:
    """Test NotificationLevel enum."""
    
    def test_notification_levels(self):
        """Test notification level values."""
        assert NotificationLevel.INFO.value == "info"
        assert NotificationLevel.SUCCESS.value == "success"
        assert NotificationLevel.WARNING.value == "warning"
        assert NotificationLevel.ERROR.value == "error"


class TestUIEvent:
    """Test UIEvent dataclass."""
    
    def test_ui_event_creation(self):
        """Test UIEvent creation."""
        event = UIEvent(
            event_type="click",
            component_id="button1",
            value=True,
            metadata={"source": "user"}
        )
        
        assert event.event_type == "click"
        assert event.component_id == "button1"
        assert event.value is True
        assert event.metadata == {"source": "user"}


class TestFakeInputsAdapter:
    """Test FakeInputsAdapter implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakeInputsAdapter()
        self.config = ComponentConfig(key="test_key", label="Test Label")
    
    def test_text_input(self):
        """Test text input component."""
        result = self.adapter.text_input(self.config, value="test", placeholder="hint")
        
        assert result == "test"  # Default return
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'text_input'
        assert self.adapter.interactions[0]['key'] == 'test_key'
        assert self.adapter.interactions[0]['value'] == 'test'
        assert self.adapter.interactions[0]['placeholder'] == 'hint'
    
    def test_text_area(self):
        """Test text area component."""
        result = self.adapter.text_area(self.config, value="content", height=300)
        
        assert result == "content"
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'text_area'
        assert self.adapter.interactions[0]['height'] == 300
    
    def test_number_input(self):
        """Test number input component."""
        result = self.adapter.number_input(
            self.config, value=5.0, min_value=0.0, max_value=10.0, step=0.5
        )
        
        assert result == 5.0
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'number_input'
        assert self.adapter.interactions[0]['min_value'] == 0.0
        assert self.adapter.interactions[0]['max_value'] == 10.0
        assert self.adapter.interactions[0]['step'] == 0.5
    
    def test_slider(self):
        """Test slider component."""
        result = self.adapter.slider(
            self.config, value=3.0, min_value=1.0, max_value=5.0, step=0.1
        )
        
        assert result == 3.0
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'slider'
    
    def test_selectbox(self):
        """Test selectbox component."""
        options = ['Option 1', 'Option 2', 'Option 3']
        result = self.adapter.selectbox(self.config, options=options, index=1)
        
        assert result == 'Option 2'
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'selectbox'
        assert self.adapter.interactions[0]['options'] == options
        assert self.adapter.interactions[0]['index'] == 1
    
    def test_checkbox(self):
        """Test checkbox component."""
        result = self.adapter.checkbox(self.config, value=True)
        
        assert result is True
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'checkbox'
        assert self.adapter.interactions[0]['value'] is True
    
    def test_radio(self):
        """Test radio component."""
        options = ['Radio 1', 'Radio 2']
        result = self.adapter.radio(
            self.config, options=options, index=0, horizontal=True
        )
        
        assert result == 'Radio 1'
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'radio'
        assert self.adapter.interactions[0]['horizontal'] is True
    
    def test_button(self):
        """Test button component."""
        result = self.adapter.button(self.config)
        
        assert result is False  # Default
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'button'
    
    def test_file_uploader(self):
        """Test file uploader component."""
        accepted_types = ['csv', 'txt']
        result = self.adapter.file_uploader(self.config, accepted_types=accepted_types)
        
        assert result is None  # Default
        assert len(self.adapter.interactions) == 1
        assert self.adapter.interactions[0]['type'] == 'file_uploader'
        assert self.adapter.interactions[0]['accepted_types'] == accepted_types
    
    def test_set_value(self):
        """Test setting values for testing."""
        self.adapter.set_value("test_key", "custom_value")
        
        result = self.adapter.text_input(self.config, value="default")
        assert result == "custom_value"


class TestFakePreviewAdapter:
    """Test FakePreviewAdapter implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakePreviewAdapter()
    
    def test_html_component(self):
        """Test HTML component rendering."""
        html_content = "<div>Test HTML</div>"
        self.adapter.html_component(html_content, height=500)
        
        assert len(self.adapter.html_renders) == 1
        assert self.adapter.html_renders[0]['content'] == html_content
        assert self.adapter.html_renders[0]['height'] == 500
    
    def test_empty_placeholder(self):
        """Test empty placeholder creation."""
        placeholder1 = self.adapter.empty_placeholder()
        placeholder2 = self.adapter.empty_placeholder()
        
        assert placeholder1 == "placeholder_0"
        assert placeholder2 == "placeholder_1"
        assert len(self.adapter.placeholders) == 2
    
    def test_container(self):
        """Test container creation."""
        container1 = self.adapter.container()
        container2 = self.adapter.container()
        
        assert container1 == "container_0"
        assert container2 == "container_1"
        assert len(self.adapter.containers) == 2


class TestFakeNotificationAdapter:
    """Test FakeNotificationAdapter implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakeNotificationAdapter()
    
    def test_show_message(self):
        """Test message display."""
        self.adapter.show_message("Test message", NotificationLevel.WARNING)
        
        assert len(self.adapter.messages) == 1
        assert self.adapter.messages[0]['message'] == "Test message"
        assert self.adapter.messages[0]['level'] == NotificationLevel.WARNING
    
    def test_show_progress(self):
        """Test progress display."""
        self.adapter.show_progress(0.75, "Loading...")
        
        assert len(self.adapter.progress_updates) == 1
        assert self.adapter.progress_updates[0]['progress'] == 0.75
        assert self.adapter.progress_updates[0]['text'] == "Loading..."
    
    def test_show_spinner(self):
        """Test spinner display."""
        spinner = self.adapter.show_spinner("Processing...")
        
        assert spinner == "spinner_1"
        assert len(self.adapter.spinners) == 1
        assert self.adapter.spinners[0] == "Processing..."


class TestFakeLayoutAdapter:
    """Test FakeLayoutAdapter implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakeLayoutAdapter()
    
    def test_columns(self):
        """Test column layout."""
        ratios = [1, 2, 1]
        columns = self.adapter.columns(ratios)
        
        assert columns == ["col_0", "col_1", "col_2"]
        assert len(self.adapter.column_layouts) == 1
        assert self.adapter.column_layouts[0] == ratios
    
    def test_expander(self):
        """Test expander creation."""
        expander = self.adapter.expander("Test Expander", expanded=True)
        
        assert expander == "expander_1"
        assert len(self.adapter.expanders) == 1
        assert self.adapter.expanders[0]['label'] == "Test Expander"
        assert self.adapter.expanders[0]['expanded'] is True
    
    def test_tabs(self):
        """Test tabs creation."""
        labels = ["Tab 1", "Tab 2", "Tab 3"]
        tabs = self.adapter.tabs(labels)
        
        assert tabs == ["tab_0", "tab_1", "tab_2"]
        assert len(self.adapter.tab_groups) == 1
        assert self.adapter.tab_groups[0] == labels
    
    def test_sidebar(self):
        """Test sidebar access."""
        sidebar = self.adapter.sidebar()
        assert sidebar == "sidebar"


class TestFakeRefreshAdapter:
    """Test FakeRefreshAdapter implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakeRefreshAdapter()
    
    def test_schedule_rerun(self):
        """Test rerun scheduling."""
        self.adapter.schedule_rerun(100)
        self.adapter.schedule_rerun(0)
        
        assert len(self.adapter.rerun_calls) == 2
        assert self.adapter.rerun_calls[0] == 100
        assert self.adapter.rerun_calls[1] == 0
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        self.adapter.invalidate_cache("specific_key")
        self.adapter.invalidate_cache()
        
        assert len(self.adapter.cache_invalidations) == 2
        assert self.adapter.cache_invalidations[0] == "specific_key"
        assert self.adapter.cache_invalidations[1] == "all"


class TestFakeAdapter:
    """Test FakeAdapter main implementation."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = FakeAdapter()
    
    def test_adapter_properties(self):
        """Test adapter property access."""
        assert isinstance(self.adapter.inputs, FakeInputsAdapter)
        assert isinstance(self.adapter.preview, FakePreviewAdapter)
        assert isinstance(self.adapter.notifications, FakeNotificationAdapter)
        assert isinstance(self.adapter.layout, FakeLayoutAdapter)
        assert isinstance(self.adapter.refresh, FakeRefreshAdapter)
    
    def test_header(self):
        """Test header rendering."""
        self.adapter.header("Test Header", level=1)
        self.adapter.header("Sub Header", level=2)
        
        assert len(self.adapter.headers) == 2
        assert self.adapter.headers[0]['text'] == "Test Header"
        assert self.adapter.headers[0]['level'] == 1
        assert self.adapter.headers[1]['text'] == "Sub Header"
        assert self.adapter.headers[1]['level'] == 2
    
    def test_subheader(self):
        """Test subheader rendering."""
        self.adapter.subheader("Test Subheader")
        
        assert len(self.adapter.headers) == 1
        assert self.adapter.headers[0]['text'] == "Test Subheader"
        assert self.adapter.headers[0]['level'] == 2
    
    def test_markdown(self):
        """Test markdown rendering."""
        self.adapter.markdown("**Bold text**", unsafe_allow_html=True)
        
        assert len(self.adapter.markdown_renders) == 1
        assert self.adapter.markdown_renders[0]['text'] == "**Bold text**"
        assert self.adapter.markdown_renders[0]['unsafe_allow_html'] is True


class TestAdapterManagement:
    """Test adapter management functions."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_ui_adapter()
    
    def teardown_method(self):
        """Cleanup test environment."""
        reset_ui_adapter()
    
    def test_get_ui_adapter_default(self):
        """Test getting default UI adapter."""
        with patch('ui.ports.get_feature_flag', return_value=False):
            adapter = get_ui_adapter()
            assert adapter.__class__.__name__ == "StreamlitAdapter"
    
    def test_get_ui_adapter_fake(self):
        """Test getting fake UI adapter."""
        with patch('ui.ports.get_feature_flag', return_value=True):
            adapter = get_ui_adapter()
            assert isinstance(adapter, FakeAdapter)
    
    def test_set_ui_adapter(self):
        """Test setting custom UI adapter."""
        custom_adapter = FakeAdapter()
        set_ui_adapter(custom_adapter)
        
        adapter = get_ui_adapter()
        assert adapter is custom_adapter
    
    def test_reset_ui_adapter(self):
        """Test resetting UI adapter."""
        custom_adapter = FakeAdapter()
        set_ui_adapter(custom_adapter)
        
        reset_ui_adapter()
        
        # Should create new adapter on next call
        with patch('ui.ports.get_feature_flag', return_value=True):
            adapter = get_ui_adapter()
            assert adapter is not custom_adapter
            assert isinstance(adapter, FakeAdapter)
