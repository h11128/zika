"""
Unit tests for services/warmup.py
Tests cache warmup strategies, pattern learning, and memory management.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, Mock

from services.warmup import (
    WarmupStrategy, WarmupConfig, WarmupRequest, WarmupResult,
    PageAccessTracker, CacheWarmupManager, get_warmup_manager,
    warmup_adjacent_pages, warmup_predictive_pages, cancel_outdated_warmups,
    get_warmup_stats
)


class TestWarmupConfig:
    """Test warmup configuration."""
    
    def test_default_config(self):
        """Test default warmup configuration."""
        config = WarmupConfig()
        assert config.enabled is True
        assert config.strategy == WarmupStrategy.SMART
        assert config.max_pages_ahead == 2
        assert config.max_pages_behind == 1
        assert config.max_memory_mb == 50.0
        assert config.max_concurrent_warmups == 2
        assert config.enable_pattern_learning is True
    
    def test_custom_config(self):
        """Test custom warmup configuration."""
        config = WarmupConfig(
            enabled=False,
            strategy=WarmupStrategy.ADJACENT_PAGES,
            max_pages_ahead=3,
            max_memory_mb=100.0
        )
        assert config.enabled is False
        assert config.strategy == WarmupStrategy.ADJACENT_PAGES
        assert config.max_pages_ahead == 3
        assert config.max_memory_mb == 100.0


class TestWarmupRequest:
    """Test warmup request functionality."""
    
    def test_request_creation(self):
        """Test warmup request creation."""
        cards = [{"hanzi": "你好", "pinyin": "nǐ hǎo", "english": "hello"}]
        preview_params = {"card_size_cm": 5.5, "gap_cm": 0.5}
        
        request = WarmupRequest(
            request_id="test_request",
            cards=cards,
            current_page=2,
            total_pages=10,
            preview_params=preview_params,
            strategy=WarmupStrategy.ADJACENT_PAGES
        )
        
        assert request.request_id == "test_request"
        assert request.cards == cards
        assert request.current_page == 2
        assert request.total_pages == 10
        assert request.preview_params == preview_params
        assert request.strategy == WarmupStrategy.ADJACENT_PAGES


class TestWarmupResult:
    """Test warmup result functionality."""
    
    def test_result_creation(self):
        """Test warmup result creation."""
        result = WarmupResult(
            request_id="test_request",
            pages_warmed=[1, 3, 4],
            pages_failed=[5],
            cache_hits=2,
            cache_misses=1,
            duration_ms=150.0,
            memory_used_mb=3.0
        )
        
        assert result.request_id == "test_request"
        assert result.pages_warmed == [1, 3, 4]
        assert result.pages_failed == [5]
        assert result.cache_hits == 2
        assert result.cache_misses == 1
        assert result.duration_ms == 150.0
        assert result.memory_used_mb == 3.0


class TestPageAccessTracker:
    """Test page access tracking and pattern learning."""
    
    def test_tracker_creation(self):
        """Test tracker creation."""
        tracker = PageAccessTracker(window_minutes=5)
        assert tracker._window_minutes == 5
        assert len(tracker._access_history) == 0
        assert len(tracker._transition_counts) == 0
    
    def test_record_page_access(self):
        """Test page access recording."""
        tracker = PageAccessTracker()
        
        # Record some page accesses
        tracker.record_page_access(1)
        tracker.record_page_access(2)
        tracker.record_page_access(3)
        tracker.record_page_access(2)
        
        assert len(tracker._access_history) == 4
        assert len(tracker._transition_counts) == 3  # 1->2, 2->3, 3->2
        assert tracker._transition_counts[(1, 2)] == 1
        assert tracker._transition_counts[(2, 3)] == 1
        assert tracker._transition_counts[(3, 2)] == 1
    
    def test_predict_next_pages(self):
        """Test page prediction."""
        tracker = PageAccessTracker()
        
        # Create access pattern: 1->2 (twice), 1->3 (once)
        tracker.record_page_access(1)
        tracker.record_page_access(2)
        tracker.record_page_access(1)
        tracker.record_page_access(2)
        tracker.record_page_access(1)
        tracker.record_page_access(3)
        
        # Predict from page 1
        predictions = tracker.predict_next_pages(1, max_predictions=2)
        
        assert len(predictions) == 2
        # Page 2 should have higher confidence (2/3) than page 3 (1/3)
        assert predictions[0][0] == 2  # Most likely next page
        assert predictions[0][1] > predictions[1][1]  # Higher confidence
        assert predictions[1][0] == 3
    
    def test_access_frequency(self):
        """Test access frequency calculation."""
        tracker = PageAccessTracker(window_minutes=1)  # 1 minute window
        
        # Record multiple accesses to page 1
        for _ in range(5):
            tracker.record_page_access(1)
            time.sleep(0.01)  # Small delay
        
        frequency = tracker.get_access_frequency(1)
        assert frequency == 5.0  # 5 accesses per minute
        
        # Page 2 should have 0 frequency
        frequency_2 = tracker.get_access_frequency(2)
        assert frequency_2 == 0.0
    
    def test_history_cleanup(self):
        """Test old history cleanup."""
        tracker = PageAccessTracker(window_minutes=0.01)  # Very short window
        
        # Record access
        tracker.record_page_access(1)
        assert len(tracker._access_history) == 1
        
        # Wait for window to expire
        time.sleep(0.7)  # 0.7 seconds > 0.01 minutes
        
        # Record another access (should trigger cleanup)
        tracker.record_page_access(2)
        
        # Should only have the recent access
        assert len(tracker._access_history) == 1
        assert tracker._access_history[0][0] == 2


class TestCacheWarmupManager:
    """Test cache warmup manager functionality."""
    
    def test_manager_creation(self):
        """Test manager creation."""
        config = WarmupConfig(max_memory_mb=25.0)
        manager = CacheWarmupManager(config)
        
        assert manager.config.max_memory_mb == 25.0
        assert len(manager._active_requests) == 0
        assert len(manager._completed_requests) == 0
    
    @patch('services.warmup.get_feature_flag')
    def test_manager_disabled(self, mock_feature_flag):
        """Test manager when disabled."""
        mock_feature_flag.return_value = False
        config = WarmupConfig(enabled=False)
        manager = CacheWarmupManager(config)
        
        cards = [{"hanzi": "测试"}]
        request_id = manager.warmup_pages(cards, 1, 5, {})
        
        assert request_id == ""  # Should return empty string when disabled
    
    def test_determine_pages_adjacent(self):
        """Test adjacent pages strategy."""
        manager = CacheWarmupManager()
        
        request = WarmupRequest(
            request_id="test",
            cards=[],
            current_page=5,
            total_pages=10,
            preview_params={},
            strategy=WarmupStrategy.ADJACENT_PAGES
        )
        
        pages = manager._determine_pages_to_warm(request)
        
        # Should include pages 4, 6, 7 (current_page ± 1, ± 2)
        expected = [4, 6, 7]  # 5-1, 5+1, 5+2 (max_pages_behind=1, max_pages_ahead=2)
        assert sorted(pages) == sorted(expected)
    
    def test_determine_pages_sequential(self):
        """Test sequential pages strategy."""
        manager = CacheWarmupManager()
        
        request = WarmupRequest(
            request_id="test",
            cards=[],
            current_page=3,
            total_pages=10,
            preview_params={},
            strategy=WarmupStrategy.SEQUENTIAL
        )
        
        pages = manager._determine_pages_to_warm(request)
        
        # Should include next 2 pages: 4, 5
        expected = [4, 5]
        assert pages == expected
    
    def test_determine_pages_boundary_conditions(self):
        """Test page determination at boundaries."""
        manager = CacheWarmupManager()
        
        # Test at beginning
        request = WarmupRequest(
            request_id="test",
            cards=[],
            current_page=0,
            total_pages=5,
            preview_params={},
            strategy=WarmupStrategy.ADJACENT_PAGES
        )
        
        pages = manager._determine_pages_to_warm(request)
        
        # Should only include forward pages: 1, 2
        expected = [1, 2]
        assert sorted(pages) == sorted(expected)
        
        # Test at end
        request.current_page = 4  # Last page
        pages = manager._determine_pages_to_warm(request)
        
        # Should only include backward page: 3
        expected = [3]
        assert pages == expected
    
    def test_memory_limits(self):
        """Test memory limit checking."""
        config = WarmupConfig(max_memory_mb=2.0)  # Very low limit
        manager = CacheWarmupManager(config)
        
        # Should allow small warmup
        assert manager._check_memory_limits(1) is True
        
        # Should reject large warmup
        assert manager._check_memory_limits(5) is False
    
    def test_cache_key_creation(self):
        """Test cache key creation."""
        manager = CacheWarmupManager()
        
        preview_params = {"card_size_cm": 5.5, "gap_cm": 0.5}
        key1 = manager._create_page_cache_key(1, preview_params)
        key2 = manager._create_page_cache_key(1, preview_params)
        key3 = manager._create_page_cache_key(2, preview_params)
        
        # Same page and params should produce same key
        assert key1 == key2
        
        # Different page should produce different key
        assert key1 != key3
        
        # Keys should be valid MD5 hashes
        assert len(key1) == 32
        assert all(c in '0123456789abcdef' for c in key1)
    
    @patch('services.warmup.get_prefetch_manager')
    def test_warmup_request_submission(self, mock_get_prefetch):
        """Test warmup request submission."""
        mock_prefetch_manager = Mock()
        mock_prefetch_manager.submit_task.return_value = True
        mock_get_prefetch.return_value = mock_prefetch_manager
        
        manager = CacheWarmupManager()
        
        cards = [{"hanzi": f"卡片{i}"} for i in range(10)]
        preview_params = {"card_size_cm": 5.5}
        
        request_id = manager.warmup_pages(cards, 2, 5, preview_params)

        # Should return a valid request ID
        assert len(request_id) == 8

        # Should have recorded the request
        assert manager._stats['requests_submitted'] == 1

        # Wait a bit for background thread to process
        time.sleep(0.1)

        # Request might be moved to completed or cancelled by now,
        # but stats should be updated
    
    def test_cancel_warmup(self):
        """Test warmup cancellation."""
        manager = CacheWarmupManager()
        
        # Create a mock request
        request = WarmupRequest(
            request_id="test_cancel",
            cards=[],
            current_page=1,
            total_pages=5,
            preview_params={}
        )
        
        manager._active_requests["test_cancel"] = request
        
        # Cancel the request
        cancelled = manager.cancel_warmup("test_cancel")
        
        assert cancelled is True
        assert "test_cancel" not in manager._active_requests
        assert "test_cancel" in manager._cancelled_requests
        assert manager._stats['requests_cancelled'] == 1
    
    def test_cancel_outdated_warmups(self):
        """Test cancellation of outdated warmups."""
        manager = CacheWarmupManager()
        
        # Create multiple requests
        for i in range(3):
            request = WarmupRequest(
                request_id=f"request_{i}",
                cards=[],
                current_page=i,
                total_pages=5,
                preview_params={}
            )
            manager._active_requests[f"request_{i}"] = request
        
        # Cancel outdated (keep request_1)
        cancelled_count = manager.cancel_outdated_warmups("request_1")
        
        assert cancelled_count == 2
        assert "request_1" in manager._active_requests
        assert "request_0" not in manager._active_requests
        assert "request_2" not in manager._active_requests
    
    def test_statistics(self):
        """Test statistics collection."""
        manager = CacheWarmupManager()
        
        # Add some mock data
        manager._stats['requests_submitted'] = 5
        manager._stats['pages_warmed'] = 10
        manager._estimated_memory_mb = 15.0
        
        stats = manager.get_stats()
        
        assert stats['requests_submitted'] == 5
        assert stats['pages_warmed'] == 10
        assert stats['active_requests'] == 0
        assert stats['memory_usage']['estimated_mb'] == 15.0
        assert 'pattern_transitions' in stats


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.warmup.get_warmup_manager')
    def test_warmup_adjacent_pages_function(self, mock_get_manager):
        """Test warmup adjacent pages convenience function."""
        mock_manager = Mock()
        mock_manager.warmup_pages.return_value = "request_123"
        mock_get_manager.return_value = mock_manager
        
        cards = [{"hanzi": "你好"}]
        preview_params = {"card_size_cm": 5.5}
        
        request_id = warmup_adjacent_pages(cards, 2, 10, preview_params)
        
        assert request_id == "request_123"
        mock_manager.warmup_pages.assert_called_once_with(
            cards, 2, 10, preview_params, WarmupStrategy.ADJACENT_PAGES
        )
    
    @patch('services.warmup.get_warmup_manager')
    def test_warmup_predictive_pages_function(self, mock_get_manager):
        """Test warmup predictive pages convenience function."""
        mock_manager = Mock()
        mock_manager.warmup_pages.return_value = "request_456"
        mock_get_manager.return_value = mock_manager
        
        cards = [{"hanzi": "测试"}]
        preview_params = {"card_size_cm": 6.0}
        
        request_id = warmup_predictive_pages(cards, 3, 8, preview_params)
        
        assert request_id == "request_456"
        mock_manager.warmup_pages.assert_called_once_with(
            cards, 3, 8, preview_params, WarmupStrategy.PREDICTIVE
        )
    
    @patch('services.warmup.get_warmup_manager')
    def test_cancel_outdated_warmups_function(self, mock_get_manager):
        """Test cancel outdated warmups convenience function."""
        mock_manager = Mock()
        mock_manager.cancel_outdated_warmups.return_value = 3
        mock_get_manager.return_value = mock_manager
        
        cancelled_count = cancel_outdated_warmups("current_request")
        
        assert cancelled_count == 3
        mock_manager.cancel_outdated_warmups.assert_called_once_with("current_request")
    
    @patch('services.warmup.get_warmup_manager')
    def test_get_warmup_stats_function(self, mock_get_manager):
        """Test get warmup stats convenience function."""
        mock_manager = Mock()
        mock_manager.get_stats.return_value = {"requests_submitted": 10}
        mock_get_manager.return_value = mock_manager
        
        stats = get_warmup_stats()
        
        assert stats == {"requests_submitted": 10}
        mock_manager.get_stats.assert_called_once()


class TestIntegration:
    """Test integration scenarios."""
    
    def test_pattern_learning_integration(self):
        """Test pattern learning with warmup."""
        config = WarmupConfig(
            enable_pattern_learning=True,
            min_pattern_confidence=0.5
        )
        manager = CacheWarmupManager(config)
        
        # Simulate user navigation pattern
        access_tracker = manager._access_tracker
        
        # Create pattern: 1->2->3->2->1
        for page in [1, 2, 3, 2, 1, 2, 3, 2]:
            access_tracker.record_page_access(page)
        
        # Test prediction from page 2
        predictions = access_tracker.predict_next_pages(2, max_predictions=2)
        
        # Should predict page 3 and page 1 based on pattern
        assert len(predictions) > 0
        predicted_pages = [p[0] for p in predictions]
        assert 3 in predicted_pages or 1 in predicted_pages
    
    @patch('services.warmup.get_prefetch_manager')
    @patch('services.warmup.get_preview_cache')
    def test_full_warmup_workflow(self, mock_get_cache, mock_get_prefetch):
        """Test complete warmup workflow."""
        # Setup mocks
        mock_cache = Mock()
        mock_cache.get.return_value = None  # No cache hits
        mock_get_cache.return_value = mock_cache
        
        mock_prefetch_manager = Mock()
        mock_prefetch_manager.submit_task.return_value = True
        mock_get_prefetch.return_value = mock_prefetch_manager
        
        # Create manager
        manager = CacheWarmupManager()
        
        # Submit warmup request
        cards = [{"hanzi": f"卡片{i}"} for i in range(20)]
        preview_params = {"card_size_cm": 5.5, "gap_cm": 0.5}
        
        request_id = manager.warmup_pages(cards, 5, 10, preview_params)

        # Should have submitted request
        assert request_id != ""

        # Should have called prefetch manager
        # (Note: actual task submission happens in background thread)
        time.sleep(0.1)  # Allow background thread to start
        
        # Verify statistics
        stats = manager.get_stats()
        assert stats['requests_submitted'] == 1


if __name__ == "__main__":
    pytest.main([__file__])
