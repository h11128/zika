"""
Unit tests for storage quota management system.
Tests quota detection, graceful degradation, and storage status handling.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import time
import json

from components.browser_storage import (
    BrowserStorageManager, StorageStatus, get_storage_manager,
    STORAGE_QUOTA_WARNING_THRESHOLD, STORAGE_QUOTA_CRITICAL_THRESHOLD,
    QUOTA_CHECK_INTERVAL_SECONDS, LAST_QUOTA_CHECK_KEY
)
from services.persistence import UserSnapshot, MAX_INPUT_TEXT_LENGTH


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


class TestStorageQuotaManagement:
    """Test storage quota management functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = BrowserStorageManager()
        self.mock_session_state = MockSessionState()
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.st')
    def test_check_storage_quota_disabled_persistence(self, mock_st, mock_persistence):
        """Test quota check when persistence is disabled."""
        mock_persistence.return_value = False
        mock_st.session_state = self.mock_session_state
        
        status, info = self.manager.check_storage_quota()
        
        assert status == StorageStatus.DISABLED
        assert info['reason'] == 'persistence_disabled'
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_check_storage_quota_throttled(self, mock_time, mock_st, mock_persistence):
        """Test quota check throttling."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        
        # Set up recent check
        current_time = 1000.0
        recent_check = current_time - 10  # 10 seconds ago (< 30 second interval)
        mock_time.time.return_value = current_time
        
        self.mock_session_state._data[LAST_QUOTA_CHECK_KEY] = recent_check
        self.mock_session_state._data['_cached_storage_status'] = StorageStatus.AVAILABLE.value
        self.mock_session_state._data['_cached_quota_info'] = {'usage_ratio': 0.5}
        
        status, info = self.manager.check_storage_quota()
        
        assert status == StorageStatus.AVAILABLE
        assert info['usage_ratio'] == 0.5
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_check_storage_quota_warning_threshold(self, mock_time, mock_st, mock_persistence):
        """Test quota check with warning threshold."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        mock_time.time.return_value = 1000.0
        
        # Mock quota detection
        with patch.object(self.manager, '_detect_storage_quota') as mock_detect:
            mock_detect.return_value = {
                'quota_available': True,
                'quota_bytes': 1000000,
                'used_bytes': 850000,  # 85% usage (> warning threshold)
                'usage_ratio': 0.85,
                'quota_exceeded': False
            }
            
            status, info = self.manager.check_storage_quota()
            
            assert status == StorageStatus.WARNING
            assert info['usage_ratio'] == 0.85
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_check_storage_quota_critical_threshold(self, mock_time, mock_st, mock_persistence):
        """Test quota check with critical threshold."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        mock_time.time.return_value = 1000.0
        
        # Mock quota detection
        with patch.object(self.manager, '_detect_storage_quota') as mock_detect:
            mock_detect.return_value = {
                'quota_available': True,
                'quota_bytes': 1000000,
                'used_bytes': 970000,  # 97% usage (> critical threshold)
                'usage_ratio': 0.97,
                'quota_exceeded': False
            }
            
            status, info = self.manager.check_storage_quota()
            
            assert status == StorageStatus.CRITICAL
            assert info['usage_ratio'] == 0.97
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_check_storage_quota_exceeded(self, mock_time, mock_st, mock_persistence):
        """Test quota check when quota is exceeded."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        mock_time.time.return_value = 1000.0
        
        # Mock quota detection
        with patch.object(self.manager, '_detect_storage_quota') as mock_detect:
            mock_detect.return_value = {
                'quota_available': True,
                'quota_bytes': 1000000,
                'used_bytes': 1100000,  # 110% usage (exceeded)
                'usage_ratio': 1.1,
                'quota_exceeded': True
            }
            
            status, info = self.manager.check_storage_quota()
            
            assert status == StorageStatus.EXCEEDED
            assert info['quota_exceeded'] is True
    
    def test_detect_storage_quota_with_current_data(self):
        """Test storage quota detection with current data."""
        # Mock localStorage data
        mock_data = {'cards': [{'hanzi': '测试'}] * 100, 'input_text': 'test' * 1000}

        with patch.object(self.manager, '_get_from_localstorage') as mock_get_data, \
             patch.object(self.manager, '_get_storage_estimate') as mock_estimate, \
             patch.object(self.manager, '_test_storage_capacity') as mock_test:
            mock_get_data.return_value = mock_data
            mock_estimate.return_value = None  # Storage API not available
            mock_test.return_value = None  # Skip write test

            quota_info = self.manager._detect_storage_quota()

            assert quota_info['detection_method'] == 'data_estimation'
            assert quota_info['used_bytes'] > 0
            assert quota_info['quota_available'] is True
    
    def test_handle_quota_exceeded(self):
        """Test handling quota exceeded scenario."""
        # Mock localStorage data with export history
        mock_data = {
            'cards': [{'hanzi': '测试'}],
            'export_history': [{'timestamp': '2023-01-01'}] * 50,
            'input_text': 'test'
        }
        
        with patch.object(self.manager, '_get_from_localstorage') as mock_get_data, \
             patch.object(self.manager, '_save_to_localstorage') as mock_save:
            mock_get_data.return_value = mock_data
            mock_save.return_value = True
            
            result = self.manager._handle_quota_exceeded()
            
            assert result is True
            # Should have called save with reduced data (no export_history)
            mock_save.assert_called_once()
            saved_data = mock_save.call_args[0][0]
            assert 'export_history' not in saved_data
    
    def test_handle_quota_exceeded_clear_all(self):
        """Test handling quota exceeded with full clear."""
        with patch.object(self.manager, '_get_from_localstorage') as mock_get_data, \
             patch.object(self.manager, '_save_to_localstorage') as mock_save, \
             patch.object(self.manager, 'clear_storage') as mock_clear:
            mock_get_data.return_value = {'cards': []}
            mock_save.return_value = False  # Save fails
            mock_clear.return_value = True
            
            result = self.manager._handle_quota_exceeded()
            
            assert result is False
            mock_clear.assert_called_once()
    
    def test_apply_graceful_degradation_critical(self):
        """Test graceful degradation for critical quota status."""
        # Create snapshot with large data
        snapshot = MagicMock()
        snapshot.input_text = "x" * (MAX_INPUT_TEXT_LENGTH + 1000)  # Oversized
        snapshot.export_history = [{'id': i} for i in range(50)]  # Large history
        snapshot.cards = [{'hanzi': f'测试{i}'} for i in range(150)]  # Many cards
        
        result = self.manager._apply_graceful_degradation(snapshot, StorageStatus.CRITICAL)
        
        # Should truncate input text
        assert len(result.input_text) == MAX_INPUT_TEXT_LENGTH // 2
        
        # Should clear export history
        assert result.export_history == []
        
        # Should reduce card count
        assert len(result.cards) == 100
    
    def test_apply_graceful_degradation_warning(self):
        """Test graceful degradation for warning quota status."""
        # Create snapshot with moderate data
        snapshot = MagicMock()
        snapshot.input_text = "x" * int(MAX_INPUT_TEXT_LENGTH * 0.9)  # Near limit
        snapshot.export_history = [{'id': i} for i in range(20)]  # Moderate history
        snapshot.cards = [{'hanzi': f'测试{i}'} for i in range(50)]  # Moderate cards
        
        result = self.manager._apply_graceful_degradation(snapshot, StorageStatus.WARNING)
        
        # Should truncate input text
        assert len(result.input_text) == int(MAX_INPUT_TEXT_LENGTH * 0.8)
        
        # Should limit export history
        assert len(result.export_history) == 10
        
        # Should not reduce card count for warning
        assert len(result.cards) == 50
    
    def test_apply_graceful_degradation_available(self):
        """Test graceful degradation for available quota status."""
        # Create snapshot
        snapshot = MagicMock()
        snapshot.input_text = "test input"
        snapshot.export_history = [{'id': 1}]
        snapshot.cards = [{'hanzi': '测试'}]
        
        result = self.manager._apply_graceful_degradation(snapshot, StorageStatus.AVAILABLE)
        
        # Should not modify anything for available status
        assert result.input_text == "test input"
        assert len(result.export_history) == 1
        assert len(result.cards) == 1


class TestStorageQuotaIntegration:
    """Test storage quota integration with save flow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = BrowserStorageManager()
        self.mock_session_state = MockSessionState()
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.create_snapshot_from_session')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_flush_if_due_with_quota_exceeded(self, mock_time, mock_st, mock_create_snapshot, mock_persistence):
        """Test flush_if_due when quota is exceeded."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        mock_time.time.return_value = 1003.0
        
        # Schedule a save
        self.mock_session_state._data['_browser_storage_save_scheduled'] = 1000.0
        self.manager.pending_save = True
        self.manager.last_save_time = 0
        
        # Mock quota check to return exceeded
        with patch.object(self.manager, 'check_storage_quota') as mock_quota_check, \
             patch.object(self.manager, '_handle_quota_exceeded') as mock_handle_exceeded:
            mock_quota_check.return_value = (StorageStatus.EXCEEDED, {'quota_exceeded': True})
            mock_handle_exceeded.return_value = False
            
            result = self.manager.flush_if_due()
            
            assert result is False
            mock_handle_exceeded.assert_called_once()
            mock_create_snapshot.assert_not_called()
    
    @patch('components.browser_storage.is_persistence_enabled')
    @patch('components.browser_storage.create_snapshot_from_session')
    @patch('components.browser_storage.st')
    @patch('components.browser_storage.time')
    def test_flush_if_due_with_graceful_degradation(self, mock_time, mock_st, mock_create_snapshot, mock_persistence):
        """Test flush_if_due with graceful degradation."""
        mock_persistence.return_value = True
        mock_st.session_state = self.mock_session_state
        mock_time.time.return_value = 1003.0
        
        # Schedule a save
        self.mock_session_state._data['_browser_storage_save_scheduled'] = 1000.0
        self.manager.pending_save = True
        self.manager.last_save_time = 0
        
        # Mock snapshot
        mock_snapshot = MagicMock()
        mock_snapshot.cards = [{'hanzi': '测试'}]
        mock_snapshot.input_text = "test input"
        mock_snapshot.to_dict.return_value = {'version': 1, 'cards': []}
        mock_create_snapshot.return_value = mock_snapshot
        
        # Mock quota check to return critical
        with patch.object(self.manager, 'check_storage_quota') as mock_quota_check, \
             patch.object(self.manager, '_apply_graceful_degradation') as mock_degrade, \
             patch.object(self.manager, '_should_save_snapshot') as mock_should_save, \
             patch.object(self.manager, '_save_to_localstorage') as mock_save:
            
            mock_quota_check.return_value = (StorageStatus.CRITICAL, {'usage_ratio': 0.97})
            mock_degrade.return_value = mock_snapshot
            mock_should_save.return_value = True
            mock_save.return_value = True
            
            result = self.manager.flush_if_due()
            
            assert result is True
            mock_degrade.assert_called_once_with(mock_snapshot, StorageStatus.CRITICAL)
            mock_save.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
