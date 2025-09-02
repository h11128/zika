"""
Unit tests for enhanced browser storage bridge.
Tests hydrate_once(), schedule_save(), flush_if_due() with single rerun and debounced saves.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import time
import json

# Import the module directly to ensure it's available for patching
import components.browser_storage
from components.browser_storage import (
    BrowserStorageManager, get_storage_manager, hydrate_once, schedule_save, flush_if_due,
    STORAGE_KEY, SAVE_DEBOUNCE_SECONDS, HYDRATION_SESSION_KEY, SAVE_SCHEDULE_KEY
)
from services.persistence import UserSnapshot


class MockSessionState:
    """Mock Streamlit session state for testing."""

    def __init__(self):
        self._data = {}

    def __getattribute__(self, name):
        # Handle internal attributes normally
        if name.startswith('_') or name in ['get']:
            return super().__getattribute__(name)

        # Check if attribute exists in data
        data = super().__getattribute__('_data')
        if name in data:
            return data[name]

        # Raise AttributeError for missing attributes (this makes hasattr() work)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __contains__(self, key):
        return key in self._data

    def __delitem__(self, key):
        if key in self._data:
            del self._data[key]

    def get(self, key, default=None):
        return self._data.get(key, default)


class TestBrowserStorageManager:
    """Test browser storage manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = BrowserStorageManager()
        self.mock_session_state = MockSessionState()
    
    def test_hydrate_once_disabled_persistence(self):
        """Test hydrate_once when persistence is disabled."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=False) as mock_persistence, \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            result = self.manager.hydrate_once()

            assert result is False
            assert not self.manager.hydrated
    
    def test_hydrate_once_already_hydrated(self):
        """Test hydrate_once when already hydrated."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=True) as mock_persistence, \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            # Mark as already hydrated
            self.mock_session_state._data[HYDRATION_SESSION_KEY] = True

            result = self.manager.hydrate_once()

            assert result is False
            assert self.manager.hydrated is True
    
    def test_hydrate_once_successful(self):
        """Test successful hydration with single rerun."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=True) as mock_persistence, \
             patch.object(components.browser_storage, 'load_snapshot_from_data') as mock_load_snapshot, \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            # Mock snapshot data
            mock_snapshot = MagicMock()
            mock_snapshot.cards = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            mock_load_snapshot.return_value = mock_snapshot

            # Mock localStorage data retrieval
            with patch.object(self.manager, '_get_from_localstorage_reliable') as mock_get_data:
                mock_get_data.return_value = {'version': 1, 'cards': []}

                result = self.manager.hydrate_once()

                # Should return True when data is found and applied
                assert result is True
                assert self.manager.hydrated is True
                assert HYDRATION_SESSION_KEY in self.mock_session_state
                assert f"{HYDRATION_SESSION_KEY}_success" in self.mock_session_state
                mock_snapshot.apply_to_session_state.assert_called_once_with(self.mock_session_state)
    
    def test_hydrate_once_no_data(self):
        """Test hydration when no localStorage data exists."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=True), \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            # Mock no localStorage data
            with patch.object(self.manager, '_get_from_localstorage_reliable') as mock_get_data:
                mock_get_data.return_value = None

                result = self.manager.hydrate_once()

                assert result is False
                assert self.manager.hydrated is True
                assert HYDRATION_SESSION_KEY in self.mock_session_state
                assert f"{HYDRATION_SESSION_KEY}_attempted" in self.mock_session_state
    
    def test_schedule_save_disabled_persistence(self):
        """Test schedule_save when persistence is disabled."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=False), \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            self.manager.schedule_save()

            assert not self.manager.pending_save
            assert not self.manager.save_scheduled
    
    def test_schedule_save_enabled(self):
        """Test schedule_save when persistence is enabled."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=True), \
             patch.object(components.browser_storage, 'st') as mock_st, \
             patch.object(components.browser_storage, 'time') as mock_time:
            mock_st.session_state = self.mock_session_state
            mock_time.time.return_value = 1000.0

            self.manager.schedule_save()

            assert self.manager.pending_save is True
            assert self.manager.save_scheduled is True
            assert self.mock_session_state.get(SAVE_SCHEDULE_KEY) == 1000.0
    
    def test_flush_if_due_disabled_persistence(self):
        """Test flush_if_due when persistence is disabled."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=False), \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            result = self.manager.flush_if_due()

            assert result is False

    def test_flush_if_due_no_pending_save(self):
        """Test flush_if_due when no save is pending."""
        with patch.object(components.browser_storage, 'is_persistence_enabled', return_value=True), \
             patch.object(components.browser_storage, 'st') as mock_st:
            mock_st.session_state = self.mock_session_state

            result = self.manager.flush_if_due()

            assert result is False
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.create_snapshot_from_session')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_flush_if_due_debounce_not_elapsed(self, mock_time, mock_st, mock_create_snapshot, mock_persistence):
        """Test flush_if_due when debounce period hasn't elapsed."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state

        # Set up timing
        schedule_time = 1000.0
        current_time = 1000.5  # Only 0.5 seconds later
        mock_time.time.return_value = current_time

        # Schedule a save
        self.mock_session_state._data[SAVE_SCHEDULE_KEY] = schedule_time
        self.manager.pending_save = True
        self.manager.last_save_time = 999.0  # Recent save to trigger debounce

        result = self.manager.flush_if_due()

        assert result is False
        mock_create_snapshot.assert_not_called()
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.create_snapshot_from_session')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_flush_if_due_successful_save(self, mock_time, mock_st, mock_create_snapshot, mock_persistence):
        """Test successful flush_if_due with save."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state

        # Set up timing
        schedule_time = 1000.0
        current_time = 1003.0  # 3 seconds later (> debounce)
        mock_time.time.return_value = current_time

        # Mock snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.cards = [{'hanzi': '测试'}]
        mock_snapshot.input_text = "test input"
        mock_snapshot.to_dict.return_value = {'version': 1, 'cards': []}
        mock_create_snapshot.return_value = mock_snapshot

        # Schedule a save
        self.mock_session_state._data[SAVE_SCHEDULE_KEY] = schedule_time
        self.manager.pending_save = True
        self.manager.last_save_time = 0  # Long ago
        
        # Mock save method
        with patch.object(self.manager, '_should_save_snapshot') as mock_should_save, \
             patch.object(self.manager, '_save_to_localstorage') as mock_save:
            mock_should_save.return_value = True
            mock_save.return_value = True
            
            result = self.manager.flush_if_due()
            
            assert result is True
            assert self.manager.last_save_time == current_time
            assert not self.manager.pending_save
            assert not self.manager.save_scheduled
            assert SAVE_SCHEDULE_KEY not in self.mock_session_state
            mock_save.assert_called_once()
    
    def test_should_save_snapshot_with_cards(self):
        """Test _should_save_snapshot with cards."""
        snapshot = MagicMock()
        snapshot.cards = [{'hanzi': '测试'}]
        snapshot.input_text = ""
        snapshot.options = {}
        snapshot.layout = {}
        snapshot.typography = {}
        snapshot.visual = {}
        snapshot.preview = {}
        snapshot.export_history = []
        
        result = self.manager._should_save_snapshot(snapshot)
        assert result is True
    
    def test_should_save_snapshot_with_input_text(self):
        """Test _should_save_snapshot with input text."""
        snapshot = MagicMock()
        snapshot.cards = []
        snapshot.input_text = "test input"
        snapshot.options = {}
        snapshot.layout = {}
        snapshot.typography = {}
        snapshot.visual = {}
        snapshot.preview = {}
        snapshot.export_history = []
        
        result = self.manager._should_save_snapshot(snapshot)
        assert result is True
    
    def test_should_save_snapshot_empty(self):
        """Test _should_save_snapshot with empty data."""
        snapshot = MagicMock()
        snapshot.cards = []
        snapshot.input_text = ""
        snapshot.options = {}
        snapshot.layout = {}
        snapshot.typography = {}
        snapshot.visual = {}
        snapshot.preview = {}
        snapshot.export_history = []
        
        result = self.manager._should_save_snapshot(snapshot)
        assert result is False
    
    def test_get_storage_info(self):
        """Test get_storage_info method."""
        with patch('components.browser_storage.st') as mock_st, \
             patch('components.browser_storage.is_persistence_enabled') as mock_persistence:
            mock_st.session_state = self.mock_session_state
            mock_persistence.return_value = True
            
            self.manager.hydrated = True
            self.manager.pending_save = True
            self.manager.last_save_time = 1000.0
            
            info = self.manager.get_storage_info()
            
            assert info['hydrated'] is True
            assert info['pending_save'] is True
            assert info['last_save_time'] == 1000.0
            assert info['persistence_enabled'] is True


class TestGlobalFunctions:
    """Test global browser storage functions."""
    
    def test_get_storage_manager_singleton(self):
        """Test that get_storage_manager returns singleton."""
        manager1 = get_storage_manager()
        manager2 = get_storage_manager()
        
        assert manager1 is manager2
        assert isinstance(manager1, BrowserStorageManager)
    
    @patch('components.browser_storage.get_storage_manager')
    def test_hydrate_once_function(self, mock_get_manager):
        """Test hydrate_once convenience function."""
        mock_manager = MagicMock()
        mock_manager.hydrate_once.return_value = True
        mock_get_manager.return_value = mock_manager
        
        result = hydrate_once()
        
        assert result is True
        mock_manager.hydrate_once.assert_called_once()
    
    @patch('components.browser_storage.get_storage_manager')
    def test_schedule_save_function(self, mock_get_manager):
        """Test schedule_save convenience function."""
        mock_manager = MagicMock()
        mock_get_manager.return_value = mock_manager
        
        schedule_save()
        
        mock_manager.schedule_save.assert_called_once()
    
    @patch('components.browser_storage.get_storage_manager')
    def test_flush_if_due_function(self, mock_get_manager):
        """Test flush_if_due convenience function."""
        mock_manager = MagicMock()
        mock_manager.flush_if_due.return_value = True
        mock_get_manager.return_value = mock_manager
        
        result = flush_if_due()
        
        assert result is True
        mock_manager.flush_if_due.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
