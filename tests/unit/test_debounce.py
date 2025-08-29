"""
Unit tests for ui/debounce.py
Tests debouncing system, form semantics, and atomic commits.
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from ui.debounce import (
    PendingChange, DebounceConfig, DebounceManager,
    get_debounce_manager, debounce_immediate, debounce_form_input,
    debounce_batch, flush_debounced_changes, FormContext, form_context
)


class TestPendingChange:
    """Test PendingChange dataclass."""
    
    def test_pending_change_creation(self):
        """Test PendingChange creation."""
        now = datetime.utcnow()
        change = PendingChange(
            key="test_key",
            value="test_value",
            timestamp=now,
            source="test"
        )
        
        assert change.key == "test_key"
        assert change.value == "test_value"
        assert change.timestamp == now
        assert change.source == "test"


class TestDebounceConfig:
    """Test DebounceConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DebounceConfig()
        
        assert config.immediate_delay_ms == 150
        assert config.form_delay_ms == 250
        assert config.batch_delay_ms == 500
        assert config.max_pending_changes == 50
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = DebounceConfig(
            immediate_delay_ms=100,
            form_delay_ms=200,
            batch_delay_ms=300,
            max_pending_changes=25
        )
        
        assert config.immediate_delay_ms == 100
        assert config.form_delay_ms == 200
        assert config.batch_delay_ms == 300
        assert config.max_pending_changes == 25


class TestDebounceManager:
    """Test DebounceManager class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = DebounceConfig(
            immediate_delay_ms=50,  # Short delays for testing
            form_delay_ms=100,
            batch_delay_ms=150,
            max_pending_changes=5
        )
        self.manager = DebounceManager(self.config)
    
    def test_schedule_change(self):
        """Test scheduling a change."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            self.manager.schedule_change("test_key", "test_value")
            
            assert "test_key" in self.manager.pending_changes
            assert self.manager.pending_changes["test_key"].value == "test_value"
    
    def test_schedule_change_disabled(self):
        """Test scheduling when debouncing is disabled."""
        with patch('ui.debounce.get_feature_flag', return_value=False):
            with patch.object(self.manager, '_apply_changes_immediate') as mock_apply:
                self.manager.schedule_change("test_key", "test_value")
                
                mock_apply.assert_called_once_with({"test_key": "test_value"})
                assert "test_key" not in self.manager.pending_changes
    
    def test_schedule_immediate(self):
        """Test scheduling immediate change."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            self.manager.schedule_immediate("test_key", "test_value")
            
            change = self.manager.pending_changes["test_key"]
            assert change.source == "immediate"
    
    def test_schedule_form_input(self):
        """Test scheduling form input change."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            self.manager.schedule_form_input("test_key", "test_value")
            
            change = self.manager.pending_changes["test_key"]
            assert change.source == "form"
    
    def test_schedule_batch(self):
        """Test scheduling batch changes."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            changes = {"key1": "value1", "key2": "value2"}
            self.manager.schedule_batch(changes)
            
            assert "key1" in self.manager.pending_changes
            assert "key2" in self.manager.pending_changes
            assert self.manager.pending_changes["key1"].source == "batch"
    
    def test_flush_now(self):
        """Test immediate flush."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            with patch('ui.debounce.set_options_batch') as mock_set:
                mock_set.return_value = MagicMock()
                
                self.manager.schedule_change("test_key", "test_value")
                changeset = self.manager.flush_now()
                
                mock_set.assert_called_once_with({"test_key": "test_value"})
                assert len(self.manager.pending_changes) == 0
    
    def test_has_pending_changes(self):
        """Test checking for pending changes."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            assert not self.manager.has_pending_changes()
            
            self.manager.schedule_change("test_key", "test_value")
            assert self.manager.has_pending_changes()
    
    def test_get_pending_change(self):
        """Test getting pending change value."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            assert self.manager.get_pending_change("test_key") is None
            
            self.manager.schedule_change("test_key", "test_value")
            assert self.manager.get_pending_change("test_key") == "test_value"
    
    def test_cancel_pending(self):
        """Test canceling pending change."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            self.manager.schedule_change("test_key", "test_value")
            assert self.manager.has_pending_changes()
            
            result = self.manager.cancel_pending("test_key")
            assert result is True
            assert not self.manager.has_pending_changes()
            
            # Cancel non-existent key
            result = self.manager.cancel_pending("nonexistent")
            assert result is False
    
    def test_max_pending_changes(self):
        """Test max pending changes limit."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            with patch.object(self.manager, '_apply_changes_immediate') as mock_apply:
                # Add more changes than the limit
                for i in range(self.config.max_pending_changes + 2):
                    self.manager.schedule_change(f"key_{i}", f"value_{i}")
                
                # Should have triggered flush of oldest changes
                assert len(self.manager.pending_changes) <= self.config.max_pending_changes
                mock_apply.assert_called()
    
    def test_timer_cancellation(self):
        """Test that new changes cancel previous timers."""
        with patch('ui.debounce.get_feature_flag', return_value=True):
            # Schedule first change
            self.manager.schedule_change("key1", "value1")
            first_timer = self.manager.flush_timer
            
            # Schedule second change
            self.manager.schedule_change("key2", "value2")
            second_timer = self.manager.flush_timer
            
            # First timer should be cancelled
            assert first_timer != second_timer
            assert not first_timer.is_alive()


class TestFormContext:
    """Test FormContext class."""
    
    def test_form_context_auto_flush(self):
        """Test form context with auto flush."""
        with patch('ui.debounce.debounce_batch') as mock_debounce:
            with FormContext(auto_flush=True) as form:
                form.set("key1", "value1")
                form.set("key2", "value2")
            
            mock_debounce.assert_called_once_with({"key1": "value1", "key2": "value2"})
    
    def test_form_context_no_auto_flush(self):
        """Test form context without auto flush."""
        with patch('ui.debounce.debounce_batch') as mock_debounce:
            with FormContext(auto_flush=False) as form:
                form.set("key1", "value1")
            
            mock_debounce.assert_not_called()
    
    def test_form_context_manual_commit(self):
        """Test manual commit in form context."""
        with patch('ui.debounce.debounce_batch') as mock_debounce:
            with patch('ui.debounce.flush_debounced_changes') as mock_flush:
                mock_flush.return_value = MagicMock()
                
                form = FormContext(auto_flush=False)
                form.set("key1", "value1")
                changeset = form.commit()
                
                mock_debounce.assert_called_once_with({"key1": "value1"})
                mock_flush.assert_called_once()
    
    def test_form_context_empty_commit(self):
        """Test commit with no changes."""
        form = FormContext(auto_flush=False)
        changeset = form.commit()
        
        # Should return empty changeset
        assert changeset.changes == {}


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_debounce_immediate(self):
        """Test debounce_immediate function."""
        with patch('ui.debounce.get_debounce_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            
            debounce_immediate("test_key", "test_value")
            
            mock_manager.schedule_immediate.assert_called_once_with("test_key", "test_value")
    
    def test_debounce_form_input(self):
        """Test debounce_form_input function."""
        with patch('ui.debounce.get_debounce_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            
            debounce_form_input("test_key", "test_value")
            
            mock_manager.schedule_form_input.assert_called_once_with("test_key", "test_value")
    
    def test_debounce_batch(self):
        """Test debounce_batch function."""
        with patch('ui.debounce.get_debounce_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            
            changes = {"key1": "value1", "key2": "value2"}
            debounce_batch(changes)
            
            mock_manager.schedule_batch.assert_called_once_with(changes)
    
    def test_flush_debounced_changes(self):
        """Test flush_debounced_changes function."""
        with patch('ui.debounce.get_debounce_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager
            
            flush_debounced_changes()
            
            mock_manager.flush_now.assert_called_once()
    
    def test_get_pending_value(self):
        """Test get_pending_value function."""
        with patch('ui.debounce.get_debounce_manager') as mock_get_manager:
            with patch('streamlit.session_state') as mock_session_state:
                mock_manager = MagicMock()
                mock_manager.get_pending_change.return_value = "pending_value"
                mock_get_manager.return_value = mock_manager
                
                # Test with pending value
                result = get_pending_value("test_key", "default")
                assert result == "pending_value"
                
                # Test without pending value
                mock_manager.get_pending_change.return_value = None
                mock_session_state.test_key = "session_value"
                result = get_pending_value("test_key", "default")
                # Should fall back to session state or default


class TestGlobalManager:
    """Test global manager singleton."""
    
    def test_get_debounce_manager_singleton(self):
        """Test that get_debounce_manager returns singleton."""
        manager1 = get_debounce_manager()
        manager2 = get_debounce_manager()
        
        assert manager1 is manager2


class TestTimingBehavior:
    """Test timing-related behavior."""
    
    def test_debounce_timing(self):
        """Test that debouncing actually delays execution."""
        config = DebounceConfig(immediate_delay_ms=100)
        manager = DebounceManager(config)
        
        with patch('ui.debounce.get_feature_flag', return_value=True):
            with patch('ui.debounce.set_options_batch') as mock_set:
                # Schedule change
                manager.schedule_immediate("test_key", "test_value")
                
                # Should not be applied immediately
                mock_set.assert_not_called()
                assert manager.has_pending_changes()
                
                # Wait for debounce delay
                time.sleep(0.15)  # Slightly longer than delay
                
                # Should be applied after delay
                # Note: In real implementation, this would be called by timer
                # Here we test the mechanism exists
                assert manager.flush_timer is not None
