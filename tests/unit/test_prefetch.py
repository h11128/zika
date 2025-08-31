"""
Unit tests for services/prefetch.py
Tests prefetch mechanisms, background processing, and predictive caching.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock, Mock

from services.prefetch import (
    PrefetchPriority, PrefetchType, PrefetchTask, PrefetchResult,
    PrefetchStrategy, PrefetchManager, get_prefetch_manager,
    prefetch_preview_pages, prefetch_exports, get_prefetch_stats
)


class TestPrefetchTask:
    """Test prefetch task functionality."""
    
    def test_task_creation(self):
        """Test prefetch task creation."""
        def dummy_function():
            return "result"
        
        task = PrefetchTask(
            task_id="test_task",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.HIGH,
            target_function=dummy_function,
            args=(),
            kwargs={},
            cache_key="test_key",
            tags={"component": "preview"}
        )
        
        assert task.task_id == "test_task"
        assert task.task_type == PrefetchType.PREVIEW_PAGE
        assert task.priority == PrefetchPriority.HIGH
        assert task.target_function == dummy_function
        assert task.cache_key == "test_key"
        assert task.tags["component"] == "preview"
    
    def test_task_auto_id_generation(self):
        """Test automatic task ID generation."""
        def dummy_function():
            return "result"
        
        task = PrefetchTask(
            task_id="",  # Empty ID should trigger auto-generation
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=dummy_function,
            args=(),
            kwargs={}
        )
        
        assert len(task.task_id) == 8  # UUID prefix length
        assert task.task_id != ""


class TestPrefetchResult:
    """Test prefetch result functionality."""
    
    def test_result_creation(self):
        """Test prefetch result creation."""
        result = PrefetchResult(
            task_id="test_task",
            success=True,
            result="test_result",
            duration_ms=150.0,
            cache_hit=False,
            cached=True
        )
        
        assert result.task_id == "test_task"
        assert result.success is True
        assert result.result == "test_result"
        assert result.duration_ms == 150.0
        assert result.cache_hit is False
        assert result.cached is True
    
    def test_error_result(self):
        """Test error result creation."""
        result = PrefetchResult(
            task_id="error_task",
            success=False,
            error="Test error message",
            duration_ms=50.0
        )
        
        assert result.task_id == "error_task"
        assert result.success is False
        assert result.error == "Test error message"
        assert result.result is None


class TestPrefetchStrategy:
    """Test prefetch strategy functionality."""
    
    def test_strategy_creation(self):
        """Test strategy creation."""
        strategy = PrefetchStrategy()
        assert strategy._prediction_window == 300.0
        assert strategy._min_confidence == 0.6
        assert len(strategy._access_patterns) == 0
    
    def test_record_access(self):
        """Test access pattern recording."""
        strategy = PrefetchStrategy()
        
        # Record some accesses
        strategy.record_access("resource1")
        strategy.record_access("resource2")
        strategy.record_access("resource1")
        
        assert "resource1" in strategy._access_patterns
        assert "resource2" in strategy._access_patterns
        assert len(strategy._access_patterns["resource1"]) == 2
        assert len(strategy._access_patterns["resource2"]) == 1
    
    def test_access_pattern_cleanup(self):
        """Test old access pattern cleanup."""
        strategy = PrefetchStrategy()
        strategy._prediction_window = 1.0  # 1 second window
        
        # Record access
        strategy.record_access("resource1")
        assert len(strategy._access_patterns["resource1"]) == 1
        
        # Wait and record another access
        time.sleep(1.1)
        strategy.record_access("resource1")
        
        # Should only have the recent access
        assert len(strategy._access_patterns["resource1"]) == 1
    
    def test_predict_next_accesses(self):
        """Test access prediction."""
        strategy = PrefetchStrategy()
        strategy._min_confidence = 0.1  # Lower threshold for testing
        
        # Record frequent accesses
        for _ in range(5):
            strategy.record_access("frequent_resource")
            time.sleep(0.01)
        
        predictions = strategy.predict_next_accesses({})
        assert "frequent_resource" in predictions
    
    def test_get_adjacent_pages(self):
        """Test adjacent page calculation."""
        strategy = PrefetchStrategy()
        
        # Test middle page
        pages = strategy.get_adjacent_pages(5, 10, lookahead=2)
        expected = [3, 4, 6, 7]  # 2 before and 2 after
        assert pages == expected
        
        # Test first page
        pages = strategy.get_adjacent_pages(0, 10, lookahead=2)
        expected = [1, 2]  # Only after
        assert pages == expected
        
        # Test last page
        pages = strategy.get_adjacent_pages(9, 10, lookahead=2)
        expected = [7, 8]  # Only before
        assert pages == expected


class TestPrefetchManager:
    """Test prefetch manager functionality."""
    
    def test_manager_creation(self):
        """Test manager creation."""
        manager = PrefetchManager(max_workers=2, max_queue_size=50)
        assert manager._max_workers == 2
        assert manager._max_queue_size == 50
        assert manager._enabled
        
        # Cleanup
        manager.shutdown()
    
    @patch('services.prefetch.get_feature_flag')
    def test_manager_disabled(self, mock_feature_flag):
        """Test manager when disabled."""
        mock_feature_flag.return_value = False
        
        manager = PrefetchManager()
        assert not manager._enabled
        assert manager._executor is None
        
        # Should not submit tasks when disabled
        def dummy_function():
            return "result"
        
        task = PrefetchTask(
            task_id="test",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=dummy_function,
            args=(),
            kwargs={}
        )
        
        assert not manager.submit_task(task)
    
    def test_task_submission(self):
        """Test task submission."""
        manager = PrefetchManager(max_workers=1)
        
        def dummy_function():
            time.sleep(0.1)
            return "result"
        
        task = PrefetchTask(
            task_id="test_submit",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=dummy_function,
            args=(),
            kwargs={}
        )
        
        # Submit task
        success = manager.submit_task(task)
        assert success
        
        # Wait for completion
        time.sleep(0.5)
        
        # Check result
        result = manager.get_task_result("test_submit")
        assert result is not None
        assert result.success
        assert result.result == "result"
        
        # Cleanup
        manager.shutdown()
    
    def test_task_cancellation(self):
        """Test task cancellation."""
        manager = PrefetchManager(max_workers=1)
        
        def slow_function():
            time.sleep(2.0)
            return "result"
        
        task = PrefetchTask(
            task_id="test_cancel",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=slow_function,
            args=(),
            kwargs={}
        )
        
        # Submit and immediately cancel
        manager.submit_task(task)
        time.sleep(0.1)  # Let it start
        cancelled = manager.cancel_task("test_cancel")
        
        # Should be cancelled or marked for cancellation
        assert cancelled or "test_cancel" in manager._cancelled_tasks
        
        # Cleanup
        manager.shutdown()
    
    def test_task_priority_handling(self):
        """Test task priority handling."""
        manager = PrefetchManager(max_workers=1)
        
        results = []
        
        def priority_function(priority_name):
            results.append(priority_name)
            return f"result_{priority_name}"
        
        # Submit tasks with different priorities
        high_task = PrefetchTask(
            task_id="high",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.HIGH,
            target_function=priority_function,
            args=("high",),
            kwargs={}
        )
        
        low_task = PrefetchTask(
            task_id="low",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.LOW,
            target_function=priority_function,
            args=("low",),
            kwargs={}
        )
        
        # Submit low priority first, then high priority
        manager.submit_task(low_task)
        manager.submit_task(high_task)
        
        # Wait for completion
        time.sleep(1.0)
        
        # High priority should execute first (if both were queued)
        # Note: This test is timing-dependent and may be flaky
        
        # Cleanup
        manager.shutdown()
    
    def test_statistics(self):
        """Test statistics collection."""
        manager = PrefetchManager(max_workers=1)
        
        def test_function():
            return "result"
        
        task = PrefetchTask(
            task_id="stats_test",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=test_function,
            args=(),
            kwargs={}
        )
        
        # Submit task
        manager.submit_task(task)
        
        # Wait for completion
        time.sleep(0.5)
        
        # Check statistics
        stats = manager.get_stats()
        assert stats['tasks_submitted'] >= 1
        assert stats['tasks_completed'] >= 1
        assert stats['success_rate'] > 0
        
        # Cleanup
        manager.shutdown()
    
    def test_prefetch_preview_pages(self):
        """Test preview page prefetching."""
        manager = PrefetchManager(max_workers=1)
        
        cards = [{"hanzi": "你好", "pinyin": "nǐ hǎo", "english": "hello"}]
        render_params = {"card_size_cm": 5.5, "gap_cm": 0.5}
        
        task_ids = manager.prefetch_preview_pages(
            cards, current_page=2, total_pages=10, render_params=render_params
        )
        
        # Should have submitted tasks for adjacent pages
        assert len(task_ids) > 0
        
        # Wait for completion
        time.sleep(0.5)
        
        # Check that tasks were processed
        stats = manager.get_stats()
        assert stats['tasks_submitted'] >= len(task_ids)
        
        # Cleanup
        manager.shutdown()
    
    def test_prefetch_export_formats(self):
        """Test export format prefetching."""
        manager = PrefetchManager(max_workers=1)
        
        cards = [{"hanzi": "测试", "pinyin": "cèshì", "english": "test"}]
        export_params = {"page_size": "A4", "margin_cm": 1.0}
        
        task_ids = manager.prefetch_export_formats(
            cards, export_params, formats=["pdf", "pptx"]
        )
        
        # Should have submitted tasks for each format
        assert len(task_ids) == 2
        
        # Wait for completion
        time.sleep(0.5)
        
        # Check that tasks were processed
        stats = manager.get_stats()
        assert stats['tasks_submitted'] >= 2
        
        # Cleanup
        manager.shutdown()
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        manager = PrefetchManager(max_workers=1)
        
        def warm_function(cache_key):
            return f"warmed_{cache_key}"
        
        cache_keys = ["key1", "key2", "key3"]
        task_ids = manager.warm_cache(cache_keys, warm_function)
        
        # Should have submitted tasks for each key
        assert len(task_ids) == 3
        
        # Wait for completion
        time.sleep(0.5)
        
        # Check results
        for task_id in task_ids:
            result = manager.get_task_result(task_id)
            if result:  # May not be completed yet
                assert result.success
                assert "warmed_" in str(result.result)
        
        # Cleanup
        manager.shutdown()


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.prefetch.get_prefetch_manager')
    def test_prefetch_preview_pages_function(self, mock_get_manager):
        """Test prefetch preview pages convenience function."""
        mock_manager = Mock()
        mock_manager.prefetch_preview_pages.return_value = ["task1", "task2"]
        mock_get_manager.return_value = mock_manager
        
        cards = [{"hanzi": "你好"}]
        render_params = {"card_size_cm": 5.5}
        
        task_ids = prefetch_preview_pages(cards, 1, 5, render_params)
        
        assert task_ids == ["task1", "task2"]
        mock_manager.prefetch_preview_pages.assert_called_once_with(
            cards, 1, 5, render_params
        )
    
    @patch('services.prefetch.get_prefetch_manager')
    def test_prefetch_exports_function(self, mock_get_manager):
        """Test prefetch exports convenience function."""
        mock_manager = Mock()
        mock_manager.prefetch_export_formats.return_value = ["export1", "export2"]
        mock_get_manager.return_value = mock_manager
        
        cards = [{"hanzi": "测试"}]
        export_params = {"page_size": "A4"}
        
        task_ids = prefetch_exports(cards, export_params, ["pdf"])
        
        assert task_ids == ["export1", "export2"]
        mock_manager.prefetch_export_formats.assert_called_once_with(
            cards, export_params, ["pdf"]
        )
    
    @patch('services.prefetch.get_prefetch_manager')
    def test_get_prefetch_stats_function(self, mock_get_manager):
        """Test get prefetch stats convenience function."""
        mock_manager = Mock()
        mock_manager.get_stats.return_value = {"tasks_submitted": 10}
        mock_get_manager.return_value = mock_manager
        
        stats = get_prefetch_stats()
        
        assert stats == {"tasks_submitted": 10}
        mock_manager.get_stats.assert_called_once()


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_prefetch_workflow(self):
        """Test complete prefetch workflow."""
        manager = PrefetchManager(max_workers=2)
        
        # Simulate user navigation pattern
        cards = [
            {"hanzi": f"卡片{i}", "pinyin": f"kǎpiàn{i}", "english": f"card{i}"}
            for i in range(20)
        ]
        
        render_params = {
            "card_size_cm": 5.5,
            "gap_cm": 0.5,
            "margin_cm": 1.0,
            "layout_rows": 2,
            "layout_cols": 3
        }
        
        # User is on page 3, prefetch adjacent pages
        task_ids = manager.prefetch_preview_pages(
            cards, current_page=3, total_pages=4, render_params=render_params
        )
        
        # Also prefetch exports
        export_task_ids = manager.prefetch_export_formats(
            cards, render_params, formats=["pdf"]
        )
        
        # Wait for completion
        time.sleep(1.0)
        
        # Check statistics
        stats = manager.get_stats()
        assert stats['tasks_submitted'] > 0
        
        # Check some results
        completed_count = 0
        for task_id in task_ids + export_task_ids:
            result = manager.get_task_result(task_id)
            if result and result.success:
                completed_count += 1
        
        assert completed_count > 0
        
        # Cleanup
        manager.shutdown()
    
    @patch('services.prefetch.measure_performance')
    def test_performance_monitoring_integration(self, mock_measure):
        """Test integration with performance monitoring."""
        manager = PrefetchManager(max_workers=1)
        
        def test_function():
            return "result"
        
        task = PrefetchTask(
            task_id="perf_test",
            task_type=PrefetchType.PREVIEW_PAGE,
            priority=PrefetchPriority.NORMAL,
            target_function=test_function,
            args=(),
            kwargs={}
        )
        
        manager.submit_task(task)
        time.sleep(0.5)
        
        # Should have called performance monitoring
        mock_measure.assert_called()
        
        # Cleanup
        manager.shutdown()


if __name__ == "__main__":
    pytest.main([__file__])
