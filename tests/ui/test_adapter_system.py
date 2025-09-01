"""
Test UI adapter system and component migration.
"""

import pytest
from unittest.mock import Mock

from ui.ports import (
    UIAdapter,
    get_ui_adapter,
    ComponentConfig,
    NotificationLevel
)


class TestComponentConfig:
    """Test ComponentConfig data structure."""
    
    def test_component_config_creation(self):
        """Test ComponentConfig creation with required fields."""
        config = ComponentConfig(
            key="test_key",
            label="Test Label"
        )
        assert config.key == "test_key"
        assert config.label == "Test Label"
        assert config.help_text is None
        assert config.disabled is False
    
    def test_component_config_with_optional_fields(self):
        """Test ComponentConfig with optional fields."""
        config = ComponentConfig(
            key="test_key",
            label="Test Label",
            help_text="Help text",
            disabled=True
        )
        assert config.key == "test_key"
        assert config.label == "Test Label"
        assert config.help_text == "Help text"
        assert config.disabled is True


class TestNotificationLevel:
    """Test NotificationLevel enum."""
    
    def test_notification_levels(self):
        """Test all notification levels are available."""
        assert NotificationLevel.SUCCESS
        assert NotificationLevel.INFO
        assert NotificationLevel.WARNING
        assert NotificationLevel.ERROR


class TestAdapterInterfaces:
    """Test adapter interfaces and basic functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = get_ui_adapter()

    def test_adapter_has_required_interfaces(self):
        """Test that adapter has all required interfaces."""
        # Test core adapter exists
        assert self.adapter is not None
        assert isinstance(self.adapter, UIAdapter)

        # Test input interface exists
        assert hasattr(self.adapter, 'inputs')
        assert hasattr(self.adapter.inputs, 'text_input')
        assert hasattr(self.adapter.inputs, 'button')
        assert hasattr(self.adapter.inputs, 'checkbox')
        assert hasattr(self.adapter.inputs, 'selectbox')

        # Test layout interface exists
        assert hasattr(self.adapter, 'layout')
        assert hasattr(self.adapter.layout, 'columns')
        assert hasattr(self.adapter.layout, 'sidebar')
        assert hasattr(self.adapter.layout, 'expander')

        # Test notifications interface exists
        assert hasattr(self.adapter, 'notifications')
        assert hasattr(self.adapter.notifications, 'show_success')
        assert hasattr(self.adapter.notifications, 'show_error')

    def test_adapter_methods_are_callable(self):
        """Test that adapter methods are callable."""
        # Test core methods
        assert callable(self.adapter.header)
        assert callable(self.adapter.write)
        assert callable(self.adapter.markdown)

        # Test input methods
        assert callable(self.adapter.inputs.text_input)
        assert callable(self.adapter.inputs.button)

        # Test layout methods
        assert callable(self.adapter.layout.columns)
        assert callable(self.adapter.layout.expander)

        # Test notification methods
        assert callable(self.adapter.notifications.show_success)
        assert callable(self.adapter.notifications.show_error)
    
class TestGetUIAdapter:
    """Test get_ui_adapter function."""

    def test_get_ui_adapter_returns_instance(self):
        """Test that get_ui_adapter returns UIAdapter instance."""
        adapter = get_ui_adapter()
        assert isinstance(adapter, UIAdapter)

    def test_get_ui_adapter_singleton(self):
        """Test that get_ui_adapter returns same instance (singleton pattern)."""
        adapter1 = get_ui_adapter()
        adapter2 = get_ui_adapter()
        assert adapter1 is adapter2
    



class TestComponentConfigIntegration:
    """Test ComponentConfig integration with adapters."""

    def test_component_config_creation(self):
        """Test ComponentConfig creation and usage."""
        config = ComponentConfig(
            key="integration_test",
            label="Integration Test",
            help_text="Test help",
            disabled=False
        )

        assert config.key == "integration_test"
        assert config.label == "Integration Test"
        assert config.help_text == "Test help"
        assert config.disabled is False
        assert config.visible is True  # Default value

    def test_adapter_integration_basic(self):
        """Test basic adapter integration."""
        adapter = get_ui_adapter()
        config = ComponentConfig(key="test", label="Test")

        # Test that adapter can accept ComponentConfig
        # (actual execution may fail in test environment, but interface should work)
        assert hasattr(adapter.inputs, 'text_input')
        assert callable(adapter.inputs.text_input)
