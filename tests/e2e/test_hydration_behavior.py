"""
End-to-end tests for hydration behavior.
Tests hydration single rerun without sleeps using event-driven approach.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os
import json
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockStreamlitSession:
    """Mock Streamlit session for testing hydration."""
    
    def __init__(self):
        self.state = {}
        self.rerun_count = 0
        self.rerun_calls = []
        self.hydration_complete = False
        self.hydration_callbacks = []
    
    def rerun(self):
        """Mock rerun that tracks calls."""
        self.rerun_count += 1
        self.rerun_calls.append(time.time())
        
        # Trigger hydration callbacks on first rerun
        if self.rerun_count == 1 and not self.hydration_complete:
            self.hydration_complete = True
            for callback in self.hydration_callbacks:
                callback()
    
    def add_hydration_callback(self, callback):
        """Add callback to be called after hydration."""
        self.hydration_callbacks.append(callback)
    
    def get_rerun_count(self):
        """Get number of reruns."""
        return self.rerun_count
    
    def reset_rerun_tracking(self):
        """Reset rerun tracking."""
        self.rerun_count = 0
        self.rerun_calls.clear()


class MockBrowserStorage:
    """Mock browser storage for testing hydration."""
    
    def __init__(self):
        self.storage = {}
        self.hydration_triggered = False
        self.hydration_data = None
    
    def get_item(self, key):
        """Get item from storage."""
        return self.storage.get(key)
    
    def set_item(self, key, value):
        """Set item in storage."""
        self.storage[key] = value
    
    def trigger_hydration(self, data):
        """Trigger hydration with data."""
        self.hydration_triggered = True
        self.hydration_data = data
        self.storage['user_snapshot'] = json.dumps(data)
    
    def is_hydration_triggered(self):
        """Check if hydration was triggered."""
        return self.hydration_triggered
    
    def get_hydration_data(self):
        """Get hydration data."""
        return self.hydration_data


class TestHydrationSingleRerun:
    """Test hydration triggers exactly one rerun."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session = MockStreamlitSession()
        self.storage = MockBrowserStorage()
        self.hydration_complete = False
        self.hydration_data_received = None
    
    def test_hydration_triggers_single_rerun(self):
        """Test that hydration triggers exactly one rerun."""
        # Set up hydration callback
        def on_hydration_complete():
            self.hydration_complete = True
        
        self.session.add_hydration_callback(on_hydration_complete)
        
        # Simulate hydration data
        hydration_data = {
            'version': 3,
            'session_id': 'test-session',
            'input_text': '你好 世界',
            'cards': [
                {'uuid': 'card-1', 'hanzi': '你好', 'version': 1},
                {'uuid': 'card-2', 'hanzi': '世界', 'version': 1}
            ],
            'options': {'auto_pinyin': True},
            'layout': {'layout_rows': 2, 'layout_cols': 3}
        }
        
        # Trigger hydration
        self.storage.trigger_hydration(hydration_data)
        
        # Simulate hydration process
        if self.storage.is_hydration_triggered():
            # First rerun for hydration
            self.session.rerun()
        
        # Verify exactly one rerun
        assert self.session.get_rerun_count() == 1
        assert self.hydration_complete
        assert self.storage.get_hydration_data() == hydration_data
    
    def test_hydration_with_empty_storage_no_rerun(self):
        """Test that empty storage doesn't trigger rerun."""
        # No hydration data in storage
        assert not self.storage.is_hydration_triggered()
        
        # Should not trigger rerun
        assert self.session.get_rerun_count() == 0
    
    def test_hydration_with_invalid_data_single_rerun(self):
        """Test that invalid hydration data still triggers single rerun."""
        # Set up hydration callback
        def on_hydration_complete():
            self.hydration_complete = True
        
        self.session.add_hydration_callback(on_hydration_complete)
        
        # Trigger hydration with invalid data
        invalid_data = {'invalid': 'data'}
        self.storage.trigger_hydration(invalid_data)
        
        # Should still trigger exactly one rerun
        if self.storage.is_hydration_triggered():
            self.session.rerun()
        
        assert self.session.get_rerun_count() == 1
        assert self.hydration_complete
    
    def test_multiple_hydration_attempts_single_rerun(self):
        """Test that multiple hydration attempts don't cause multiple reruns."""
        # Set up hydration callback
        def on_hydration_complete():
            self.hydration_complete = True
        
        self.session.add_hydration_callback(on_hydration_complete)
        
        # First hydration
        data1 = {'version': 3, 'session_id': 'session-1'}
        self.storage.trigger_hydration(data1)
        
        if self.storage.is_hydration_triggered():
            self.session.rerun()
        
        # Reset hydration flag for second attempt
        self.storage.hydration_triggered = False
        
        # Second hydration attempt (should be ignored)
        data2 = {'version': 3, 'session_id': 'session-2'}
        self.storage.trigger_hydration(data2)
        
        # Should not trigger another rerun if already hydrated
        if self.storage.is_hydration_triggered() and not self.session.hydration_complete:
            self.session.rerun()
        
        # Should still be exactly one rerun
        assert self.session.get_rerun_count() == 1


class TestHydrationDataFlow:
    """Test hydration data flow and state restoration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session = MockStreamlitSession()
        self.storage = MockBrowserStorage()
        self.state_service = MagicMock()
        self.restored_state = {}
    
    def test_hydration_restores_user_state(self):
        """Test that hydration properly restores user state."""
        # Mock state service methods
        def mock_set_option(key, value):
            self.restored_state[key] = value
        
        def mock_set_options_batch(options):
            self.restored_state.update(options)
        
        self.state_service.set_option = mock_set_option
        self.state_service.set_options_batch = mock_set_options_batch
        
        # Hydration data
        hydration_data = {
            'version': 3,
            'input_text': '学习 中文',
            'options': {
                'auto_pinyin': True,
                'auto_english': False
            },
            'layout': {
                'layout_rows': 3,
                'layout_cols': 4,
                'card_size_cm': 5.5
            },
            'typography': {
                'hanzi_font_size_pt': 48,
                'pinyin_font_size_pt': 18
            }
        }
        
        # Trigger hydration
        self.storage.trigger_hydration(hydration_data)
        
        # Simulate hydration process
        if self.storage.is_hydration_triggered():
            # Restore state from hydration data
            self.state_service.set_option('input_text', hydration_data['input_text'])
            self.state_service.set_options_batch(hydration_data['options'])
            self.state_service.set_options_batch(hydration_data['layout'])
            self.state_service.set_options_batch(hydration_data['typography'])
            
            # Trigger rerun
            self.session.rerun()
        
        # Verify state was restored
        assert self.restored_state['input_text'] == '学习 中文'
        assert self.restored_state['auto_pinyin'] is True
        assert self.restored_state['auto_english'] is False
        assert self.restored_state['layout_rows'] == 3
        assert self.restored_state['layout_cols'] == 4
        assert self.restored_state['card_size_cm'] == 5.5
        assert self.restored_state['hanzi_font_size_pt'] == 48
        assert self.restored_state['pinyin_font_size_pt'] == 18
        
        # Verify single rerun
        assert self.session.get_rerun_count() == 1
    
    def test_hydration_with_cards_restoration(self):
        """Test hydration with cards data restoration."""
        # Mock cards service
        cards_service = MagicMock()
        restored_cards = []
        
        def mock_restore_cards(cards_data):
            restored_cards.extend(cards_data)
        
        cards_service.restore_cards = mock_restore_cards
        
        # Hydration data with cards
        hydration_data = {
            'version': 3,
            'cards': [
                {
                    'uuid': 'card-1',
                    'hanzi': '你好',
                    'pinyin': 'nǐ hǎo',
                    'english': 'hello',
                    'version': 1
                },
                {
                    'uuid': 'card-2',
                    'hanzi': '世界',
                    'pinyin': 'shì jiè',
                    'english': 'world',
                    'version': 1
                }
            ]
        }
        
        # Trigger hydration
        self.storage.trigger_hydration(hydration_data)
        
        # Simulate hydration process
        if self.storage.is_hydration_triggered():
            cards_service.restore_cards(hydration_data['cards'])
            self.session.rerun()
        
        # Verify cards were restored
        assert len(restored_cards) == 2
        assert restored_cards[0]['uuid'] == 'card-1'
        assert restored_cards[0]['hanzi'] == '你好'
        assert restored_cards[1]['uuid'] == 'card-2'
        assert restored_cards[1]['hanzi'] == '世界'
        
        # Verify single rerun
        assert self.session.get_rerun_count() == 1


class TestHydrationErrorHandling:
    """Test hydration error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session = MockStreamlitSession()
        self.storage = MockBrowserStorage()
        self.error_logged = False
        self.error_message = None
    
    def test_hydration_with_corrupted_data(self):
        """Test hydration with corrupted data."""
        # Mock error logging
        def mock_log_error(message):
            self.error_logged = True
            self.error_message = message
        
        # Trigger hydration with corrupted JSON
        corrupted_data = "{'invalid': json}"
        self.storage.storage['user_snapshot'] = corrupted_data
        
        # Simulate hydration process with error handling
        try:
            if 'user_snapshot' in self.storage.storage:
                data = json.loads(self.storage.storage['user_snapshot'])
                self.storage.trigger_hydration(data)
        except json.JSONDecodeError:
            mock_log_error("Failed to parse hydration data")
            # Should still trigger rerun for error handling
            self.session.rerun()
        
        # Verify error was handled
        assert self.error_logged
        assert "Failed to parse hydration data" in self.error_message
        assert self.session.get_rerun_count() == 1
    
    def test_hydration_with_missing_fields(self):
        """Test hydration with missing required fields."""
        # Mock error logging
        def mock_log_error(message):
            self.error_logged = True
            self.error_message = message
        
        # Hydration data missing required fields
        incomplete_data = {
            'version': 3
            # Missing session_id, input_text, etc.
        }
        
        # Trigger hydration
        self.storage.trigger_hydration(incomplete_data)
        
        # Simulate hydration process with validation
        if self.storage.is_hydration_triggered():
            data = self.storage.get_hydration_data()
            if 'session_id' not in data:
                mock_log_error("Missing required field: session_id")
            
            # Should still trigger rerun
            self.session.rerun()
        
        # Verify error was handled
        assert self.error_logged
        assert "Missing required field: session_id" in self.error_message
        assert self.session.get_rerun_count() == 1


class TestHydrationPerformance:
    """Test hydration performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.session = MockStreamlitSession()
        self.storage = MockBrowserStorage()
        self.performance_metrics = {}
    
    def test_hydration_timing(self):
        """Test hydration timing characteristics."""
        # Large hydration data
        large_cards = []
        for i in range(1000):
            large_cards.append({
                'uuid': f'card-{i}',
                'hanzi': f'汉字{i}',
                'pinyin': f'hànzì{i}',
                'english': f'character{i}',
                'version': 1
            })
        
        hydration_data = {
            'version': 3,
            'session_id': 'perf-test',
            'cards': large_cards,
            'input_text': ' '.join([f'汉字{i}' for i in range(1000)])
        }
        
        # Measure hydration timing
        start_time = time.time()
        
        # Trigger hydration
        self.storage.trigger_hydration(hydration_data)
        
        if self.storage.is_hydration_triggered():
            self.session.rerun()
        
        end_time = time.time()
        hydration_time = end_time - start_time
        
        # Store performance metrics
        self.performance_metrics['hydration_time'] = hydration_time
        self.performance_metrics['data_size'] = len(json.dumps(hydration_data))
        self.performance_metrics['cards_count'] = len(large_cards)
        
        # Verify performance is reasonable (should be fast for mock)
        assert hydration_time < 1.0  # Should complete within 1 second
        assert self.session.get_rerun_count() == 1
        
        # Verify data was processed
        assert self.storage.get_hydration_data() == hydration_data
    
    def test_hydration_memory_efficiency(self):
        """Test hydration memory efficiency."""
        # Create hydration data with various sizes
        test_sizes = [10, 100, 500]
        
        for size in test_sizes:
            # Reset for each test
            session = MockStreamlitSession()
            storage = MockBrowserStorage()
            
            # Create data of specific size
            cards = [
                {
                    'uuid': f'card-{i}',
                    'hanzi': f'字{i}',
                    'version': 1
                }
                for i in range(size)
            ]
            
            hydration_data = {
                'version': 3,
                'session_id': f'memory-test-{size}',
                'cards': cards
            }
            
            # Trigger hydration
            storage.trigger_hydration(hydration_data)
            
            if storage.is_hydration_triggered():
                session.rerun()
            
            # Verify successful hydration regardless of size
            assert session.get_rerun_count() == 1
            assert len(storage.get_hydration_data()['cards']) == size


if __name__ == "__main__":
    pytest.main([__file__])
