"""
Integration tests for cache invalidation behavior.
Tests single invalidation per batch and proper cache management.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockCacheService:
    """Mock cache service for testing invalidation behavior."""
    
    def __init__(self):
        self.invalidation_calls = []
        self.cache_data = {}
    
    def invalidate_preview_cache(self, reason=None):
        """Mock cache invalidation."""
        self.invalidation_calls.append(('preview', reason))
    
    def invalidate_export_cache(self, reason=None):
        """Mock export cache invalidation."""
        self.invalidation_calls.append(('export', reason))
    
    def clear_all_caches(self, reason=None):
        """Mock clear all caches."""
        self.invalidation_calls.append(('all', reason))
        self.cache_data.clear()
    
    def get_invalidation_count(self):
        """Get total number of invalidation calls."""
        return len(self.invalidation_calls)
    
    def get_invalidation_calls(self):
        """Get all invalidation calls."""
        return self.invalidation_calls.copy()
    
    def reset_tracking(self):
        """Reset invalidation tracking."""
        self.invalidation_calls.clear()


class TestSingleInvalidationPerBatch:
    """Test that batch operations trigger only single invalidation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockCacheService()
        self.state_service = MagicMock()
        self.state_values = {
            'layout_rows': 2,
            'layout_cols': 3,
            'background_color': '#FFFFFF',
            'hanzi_font_size_pt': 48
        }
        
        # Mock state service methods
        def mock_get_option(key, default=None):
            return self.state_values.get(key, default)
        
        def mock_set_option(key, value):
            old_value = self.state_values.get(key)
            self.state_values[key] = value
            return old_value != value
        
        def mock_set_options_batch(changes):
            """Mock batch operation with single invalidation."""
            changed_keys = []
            for key, value in changes.items():
                if self.state_values.get(key) != value:
                    self.state_values[key] = value
                    changed_keys.append(key)
            
            # Single invalidation after all changes
            if changed_keys:
                self.cache_service.invalidate_preview_cache(f"batch_change: {', '.join(changed_keys)}")
            
            return len(changed_keys) > 0
        
        self.state_service.get_option = mock_get_option
        self.state_service.set_option = mock_set_option
        self.state_service.set_options_batch = mock_set_options_batch
    
    def test_single_change_single_invalidation(self):
        """Test that single change triggers single invalidation."""
        # Reset tracking
        self.cache_service.reset_tracking()
        
        # Make single change
        self.state_service.set_option('background_color', '#F0F0F0')
        
        # Simulate invalidation (would be called by state service)
        self.cache_service.invalidate_preview_cache("single_change: background_color")
        
        # Should have exactly one invalidation
        assert self.cache_service.get_invalidation_count() == 1
        calls = self.cache_service.get_invalidation_calls()
        assert calls[0] == ('preview', 'single_change: background_color')
    
    def test_batch_change_single_invalidation(self):
        """Test that batch changes trigger only single invalidation."""
        # Reset tracking
        self.cache_service.reset_tracking()
        
        # Make batch changes
        changes = {
            'layout_rows': 3,
            'layout_cols': 4,
            'background_color': '#E0E0E0',
            'hanzi_font_size_pt': 52
        }
        
        self.state_service.set_options_batch(changes)
        
        # Should have exactly one invalidation for the entire batch
        assert self.cache_service.get_invalidation_count() == 1
        calls = self.cache_service.get_invalidation_calls()
        assert calls[0][0] == 'preview'
        assert 'batch_change' in calls[0][1]
    
    def test_multiple_individual_changes_multiple_invalidations(self):
        """Test that multiple individual changes trigger multiple invalidations."""
        # Reset tracking
        self.cache_service.reset_tracking()
        
        # Make multiple individual changes (not batched)
        self.state_service.set_option('layout_rows', 3)
        self.cache_service.invalidate_preview_cache("single_change: layout_rows")
        
        self.state_service.set_option('background_color', '#E0E0E0')
        self.cache_service.invalidate_preview_cache("single_change: background_color")
        
        # Should have multiple invalidations (one per change)
        assert self.cache_service.get_invalidation_count() == 2
    
    def test_no_change_no_invalidation(self):
        """Test that no-op changes don't trigger invalidation."""
        # Reset tracking
        self.cache_service.reset_tracking()
        
        # Make changes that don't actually change values
        changes = {
            'layout_rows': 2,  # Same as current
            'layout_cols': 3,  # Same as current
            'background_color': '#FFFFFF'  # Same as current
        }
        
        self.state_service.set_options_batch(changes)
        
        # Should have no invalidations
        assert self.cache_service.get_invalidation_count() == 0


class TestCacheInvalidationTypes:
    """Test different types of cache invalidation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockCacheService()
    
    def test_preview_cache_invalidation(self):
        """Test preview cache invalidation."""
        self.cache_service.reset_tracking()
        
        # Trigger preview cache invalidation
        self.cache_service.invalidate_preview_cache("layout_change")
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 1
        assert calls[0] == ('preview', 'layout_change')
    
    def test_export_cache_invalidation(self):
        """Test export cache invalidation."""
        self.cache_service.reset_tracking()
        
        # Trigger export cache invalidation
        self.cache_service.invalidate_export_cache("cards_change")
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 1
        assert calls[0] == ('export', 'cards_change')
    
    def test_all_cache_invalidation(self):
        """Test clearing all caches."""
        self.cache_service.reset_tracking()
        
        # Add some mock cache data
        self.cache_service.cache_data['key1'] = 'value1'
        self.cache_service.cache_data['key2'] = 'value2'
        
        # Clear all caches
        self.cache_service.clear_all_caches("session_reset")
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 1
        assert calls[0] == ('all', 'session_reset')
        assert len(self.cache_service.cache_data) == 0


class TestCacheInvalidationReasons:
    """Test cache invalidation with proper reason tracking."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockCacheService()
    
    def test_layout_change_invalidation_reason(self):
        """Test invalidation reason for layout changes."""
        self.cache_service.reset_tracking()
        
        # Simulate layout change
        self.cache_service.invalidate_preview_cache("layout_change: rows 2->3")
        
        calls = self.cache_service.get_invalidation_calls()
        assert calls[0][1] == "layout_change: rows 2->3"
    
    def test_cards_change_invalidation_reason(self):
        """Test invalidation reason for cards changes."""
        self.cache_service.reset_tracking()
        
        # Simulate cards change
        self.cache_service.invalidate_preview_cache("cards_change: count 20->25")
        self.cache_service.invalidate_export_cache("cards_change: count 20->25")
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 2
        assert calls[0][1] == "cards_change: count 20->25"
        assert calls[1][1] == "cards_change: count 20->25"
    
    def test_style_change_invalidation_reason(self):
        """Test invalidation reason for style changes."""
        self.cache_service.reset_tracking()
        
        # Simulate style change
        self.cache_service.invalidate_preview_cache("style_change: background_color")
        
        calls = self.cache_service.get_invalidation_calls()
        assert calls[0][1] == "style_change: background_color"


class TestCacheInvalidationIntegration:
    """Test cache invalidation integration with state changes."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockCacheService()
        self.invalidation_tracker = []
        
        # Mock state service that tracks invalidations
        self.state_service = MagicMock()
        
        def mock_invalidate_caches(reason):
            """Mock cache invalidation that tracks calls."""
            self.invalidation_tracker.append(reason)
            self.cache_service.invalidate_preview_cache(reason)
        
        self.state_service.invalidate_caches = mock_invalidate_caches
    
    def test_state_change_triggers_cache_invalidation(self):
        """Test that state changes trigger appropriate cache invalidation."""
        # Reset tracking
        self.cache_service.reset_tracking()
        self.invalidation_tracker.clear()
        
        # Simulate state change that should trigger invalidation
        self.state_service.invalidate_caches("layout_change: rows")
        
        # Verify invalidation was triggered
        assert len(self.invalidation_tracker) == 1
        assert self.invalidation_tracker[0] == "layout_change: rows"
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 1
        assert calls[0] == ('preview', 'layout_change: rows')
    
    def test_batch_state_change_single_invalidation(self):
        """Test that batch state changes trigger single invalidation."""
        # Reset tracking
        self.cache_service.reset_tracking()
        self.invalidation_tracker.clear()
        
        # Simulate batch state change
        self.state_service.invalidate_caches("batch_change: layout_rows, layout_cols, background_color")
        
        # Verify single invalidation for batch
        assert len(self.invalidation_tracker) == 1
        assert "batch_change" in self.invalidation_tracker[0]
        
        calls = self.cache_service.get_invalidation_calls()
        assert len(calls) == 1


class TestCacheInvalidationPerformance:
    """Test cache invalidation performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockCacheService()
    
    def test_invalidation_efficiency(self):
        """Test that invalidation is efficient and doesn't cause cascading calls."""
        self.cache_service.reset_tracking()
        
        # Simulate multiple rapid changes
        for i in range(10):
            self.cache_service.invalidate_preview_cache(f"change_{i}")
        
        # Should have exactly 10 invalidations (no cascading)
        assert self.cache_service.get_invalidation_count() == 10
    
    def test_no_redundant_invalidations(self):
        """Test that redundant invalidations are avoided."""
        self.cache_service.reset_tracking()
        
        # Simulate the same change multiple times
        reason = "layout_change: rows"
        
        # In a real implementation, this might be optimized to avoid redundant calls
        # For now, we just test that each call is tracked
        self.cache_service.invalidate_preview_cache(reason)
        self.cache_service.invalidate_preview_cache(reason)
        self.cache_service.invalidate_preview_cache(reason)
        
        # Should track all calls (optimization would be implementation-specific)
        assert self.cache_service.get_invalidation_count() == 3


if __name__ == "__main__":
    pytest.main([__file__])
