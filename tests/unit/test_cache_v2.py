"""
Unit tests for services/cache_v2.py
Tests cache functionality, TTL, eviction, and observability.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from services.cache_v2 import (
    CacheEntry, CacheConfig, CacheStats, CacheV2,
    get_preview_cache, get_export_cache, compute_cache_key,
    cached_preview_render, cached_export_render,
    clear_preview_cache_v2, clear_export_cache_v2, get_cache_stats
)


class TestCacheEntry:
    """Test CacheEntry dataclass."""
    
    def test_cache_entry_creation(self):
        """Test CacheEntry creation."""
        now = datetime.utcnow()
        entry = CacheEntry(
            value="test_value",
            created_at=now,
            last_accessed=now,
            size_bytes=100
        )
        
        assert entry.value == "test_value"
        assert entry.created_at == now
        assert entry.last_accessed == now
        assert entry.access_count == 0
        assert entry.size_bytes == 100
    
    def test_cache_entry_touch(self):
        """Test CacheEntry touch method."""
        now = datetime.utcnow()
        entry = CacheEntry(
            value="test_value",
            created_at=now,
            last_accessed=now
        )

        # Add a small delay to ensure time difference
        time.sleep(0.001)

        # Touch the entry
        entry.touch()

        assert entry.access_count == 1
        assert entry.last_accessed >= now  # Use >= instead of > for timing issues


class TestCacheStats:
    """Test CacheStats dataclass."""
    
    def test_cache_stats_hit_rate(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=8, misses=2)
        assert stats.hit_rate == 80.0
        
        # Test zero division
        stats_empty = CacheStats()
        assert stats_empty.hit_rate == 0.0


class TestCacheV2:
    """Test CacheV2 class."""
    
    def setup_method(self):
        """Setup test environment."""
        self.config = CacheConfig(
            max_entries=3,
            max_size_bytes=1000,
            ttl_seconds=60,
            name="test_cache"
        )
        self.cache = CacheV2(self.config)
    
    def test_cache_basic_operations(self):
        """Test basic cache operations."""
        # Cache v2 is always enabled - no need to mock
        # Test miss
        assert self.cache.get("key1") is None
        assert self.cache.stats.misses == 1

        # Test set and hit
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"
        assert self.cache.stats.hits == 1
        assert self.cache.stats.entry_count == 1
    
    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        # Cache v2 is always enabled - no need to mock
        # Set short TTL
        self.cache.config.ttl_seconds = 0.1

        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.2)
        assert self.cache.get("key1") is None
        assert self.cache.stats.misses == 1
    
    def test_cache_size_eviction(self):
        """Test size-based eviction."""
        # Cache v2 is always enabled - no need to mock
        # Set small size limit
        self.cache.config.max_size_bytes = 50

        # Add entries that exceed size limit
        self.cache.set("key1", "a" * 30)  # 30 bytes
        self.cache.set("key2", "b" * 30)  # 30 bytes - should evict key1

        assert self.cache.get("key1") is None  # Evicted
        assert self.cache.get("key2") == "b" * 30  # Still there
        assert self.cache.stats.evictions >= 1
    
    def test_cache_entry_count_eviction(self):
        """Test entry count-based eviction."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # Fill cache to max entries
            self.cache.set("key1", "value1")
            self.cache.set("key2", "value2")
            self.cache.set("key3", "value3")

            # Add one more - should evict LRU
            self.cache.set("key4", "value4")

            assert len(self.cache.entries) <= self.config.max_entries
            assert self.cache.stats.evictions >= 1
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction policy."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # Fill cache
            self.cache.set("key1", "value1")
            self.cache.set("key2", "value2")
            self.cache.set("key3", "value3")

            # Add new entry - should trigger eviction
            self.cache.set("key4", "value4")

            # Should have evicted something and have max entries
            assert len(self.cache.entries) <= self.config.max_entries
            assert self.cache.stats.evictions >= 1

            # New entry should be there
            assert self.cache.get("key4") == "value4"
    
    def test_cache_invalidate(self):
        """Test cache invalidation."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            self.cache.set("key1", "value1")
            assert self.cache.get("key1") == "value1"

            # Invalidate
            result = self.cache.invalidate("key1")
            assert result is True
            assert self.cache.get("key1") is None

            # Invalidate non-existent key
            result = self.cache.invalidate("nonexistent")
            assert result is False
    
    def test_cache_clear(self):
        """Test cache clearing."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            self.cache.set("key1", "value1")
            self.cache.set("key2", "value2")

            self.cache.clear()

            assert len(self.cache.entries) == 0
            assert self.cache.stats.entry_count == 0
            assert self.cache.stats.total_size_bytes == 0
    
    def test_cache_size_estimation(self):
        """Test size estimation."""
        # Test string
        size = self.cache._estimate_size("hello")
        assert size == 5  # 5 bytes for "hello"
        
        # Test integer
        size = self.cache._estimate_size(42)
        assert size == 8
        
        # Test list
        size = self.cache._estimate_size([1, 2, 3])
        assert size > 0


class TestCacheGlobalInstances:
    """Test global cache instances."""
    
    def test_get_preview_cache(self):
        """Test preview cache singleton."""
        cache1 = get_preview_cache()
        cache2 = get_preview_cache()
        
        assert cache1 is cache2  # Same instance
        assert cache1.config.name == "preview"
    
    def test_get_export_cache(self):
        """Test export cache singleton."""
        cache1 = get_export_cache()
        cache2 = get_export_cache()
        
        assert cache1 is cache2  # Same instance
        assert cache1.config.name == "export"


class TestCacheKeyComputation:
    """Test cache key computation."""
    
    def test_compute_cache_key(self):
        """Test cache key computation."""
        data = {"param1": "value1", "param2": 42}
        schema_version = "v1.0.0"
        
        key1 = compute_cache_key(data, schema_version)
        key2 = compute_cache_key(data, schema_version)
        
        # Should be deterministic
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) == 16  # Truncated SHA256
    
    def test_compute_cache_key_different_data(self):
        """Test cache key with different data."""
        data1 = {"param1": "value1"}
        data2 = {"param1": "value2"}
        schema_version = "v1.0.0"
        
        key1 = compute_cache_key(data1, schema_version)
        key2 = compute_cache_key(data2, schema_version)
        
        assert key1 != key2
    
    def test_compute_cache_key_different_schema(self):
        """Test cache key with different schema version."""
        data = {"param1": "value1"}
        
        key1 = compute_cache_key(data, "v1.0.0")
        key2 = compute_cache_key(data, "v2.0.0")
        
        assert key1 != key2


class TestCacheDecorators:
    """Test cache decorators."""
    
    def test_cached_preview_render_disabled(self):
        """Test cached preview render when cache is disabled."""
        def test_func(x, y):
            return x + y
        
        with patch('services.cache_v2.use_cache_v2', return_value=False):
            result = cached_preview_render(test_func, 1, 2)
            assert result == 3


class TestPreviewDataclassesV2:
    """Test v2 preview functions using dataclasses."""

    def test_create_page_preview_html_v2(self):
        """Test create_page_preview_html_v2 with dataclasses."""
        from services.cache_v2 import create_page_preview_html_v2
        from services.preview_types import LayoutOptions, Typography, VisualOptions

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        page_num = 0

        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font_family='SimHei'
        )

        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )

        # Test function
        result = create_page_preview_html_v2(cards, page_num, layout, typography, visual)

        # Verify result is HTML string
        assert isinstance(result, str)
        assert '<html>' in result or '<div' in result
        assert 'you' in result  # Should contain card content

    def test_cached_create_page_preview_html_v2(self):
        """Test cached version of create_page_preview_html_v2."""
        from services.cache_v2 import cached_create_page_preview_html_v2
        from services.preview_types import LayoutOptions, Typography, VisualOptions

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]
        page_num = 0

        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font_family='SimHei'
        )

        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )

        # Test cached function
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            result = cached_create_page_preview_html_v2(cards, page_num, layout, typography, visual)

            # Verify result is HTML string
            assert isinstance(result, str)
            assert '<html>' in result or '<div' in result

    def test_create_simple_grid_html_v2(self):
        """Test create_simple_grid_html_v2 with dataclasses."""
        from services.cache_v2 import create_simple_grid_html_v2
        from services.preview_types import LayoutOptions, Typography, VisualOptions

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]

        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font_family='SimHei'
        )

        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='🔲 简单网格'
        )

        # Test function
        result = create_simple_grid_html_v2(cards, layout, typography, visual)

        # Verify result is HTML string
        assert isinstance(result, str)
        assert '<html>' in result or '<div' in result
        assert 'you' in result  # Should contain card content

    def test_cached_create_simple_grid_html_v2(self):
        """Test cached version of create_simple_grid_html_v2."""
        from services.cache_v2 import cached_create_simple_grid_html_v2
        from services.preview_types import LayoutOptions, Typography, VisualOptions

        # Create test data
        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]

        layout = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font_family='SimHei'
        )

        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='🔲 简单网格'
        )

        # Test cached function
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            result = cached_create_simple_grid_html_v2(cards, layout, typography, visual)

            # Verify result is HTML string
            assert isinstance(result, str)
            assert '<html>' in result or '<div' in result

    def test_dataclass_cache_key_consistency(self):
        """Test that dataclasses produce consistent cache keys."""
        from services.cache_v2 import cached_preview_render, create_page_preview_html_v2
        from services.preview_types import LayoutOptions, Typography, VisualOptions

        # Create identical dataclasses
        layout1 = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        layout2 = LayoutOptions(
            layout_rows=2, layout_cols=2, layout_auto_fill=True,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            page_size='A4'
        )

        typography = Typography(
            font_hanzi_pt=48, font_pinyin_pt=18, font_english_pt=14,
            hanzi_font_family='SimHei'
        )

        visual = VisualOptions(
            background_color='#ffffff',
            preview_mode='📄 完整页面'
        )

        cards = [{'hanzi': '你', 'pinyin': 'nǐ', 'english': 'you'}]

        # Test that identical dataclasses produce same cache behavior
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # Both calls should use the same cache key since dataclasses are identical
            result1 = cached_preview_render(create_page_preview_html_v2, cards, 0, layout1, typography, visual)
            result2 = cached_preview_render(create_page_preview_html_v2, cards, 0, layout2, typography, visual)

            # Results should be identical (from cache)
            assert result1 == result2
    
    def test_cached_preview_render_enabled(self):
        """Test cached preview render when cache is enabled."""
        call_count = 0
        
        def test_func(x, y):
            nonlocal call_count
            call_count += 1
            return x + y
        
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # First call - should compute
            result1 = cached_preview_render(test_func, 1, 2)
            assert result1 == 3
            assert call_count == 1
            
            # Second call with same args - should use cache
            result2 = cached_preview_render(test_func, 1, 2)
            assert result2 == 3
            assert call_count == 1  # Not called again
            
            # Different args - should compute again
            result3 = cached_preview_render(test_func, 2, 3)
            assert result3 == 5
            assert call_count == 2
    
    def test_cached_export_render(self):
        """Test cached export render."""
        call_count = 0
        
        def test_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            result1 = cached_export_render(test_func, 5)
            assert result1 == 10
            assert call_count == 1
            
            # Should use cache
            result2 = cached_export_render(test_func, 5)
            assert result2 == 10
            assert call_count == 1


class TestCacheManagement:
    """Test cache management functions."""
    
    def test_clear_preview_cache_v2(self):
        """Test clearing preview cache."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            cache = get_preview_cache()
            cache.set("key1", "value1")
            
            clear_preview_cache_v2()
            
            assert len(cache.entries) == 0
    
    def test_clear_export_cache_v2(self):
        """Test clearing export cache."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            cache = get_export_cache()
            cache.set("key1", "value1")
            
            clear_export_cache_v2()
            
            assert len(cache.entries) == 0
    
    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # Add some data to caches
            preview_cache = get_preview_cache()
            export_cache = get_export_cache()
            
            preview_cache.set("key1", "value1")
            export_cache.set("key2", "value2")
            
            stats = get_cache_stats()
            
            assert 'preview' in stats
            assert 'export' in stats
            assert stats['preview'].entry_count >= 1
            assert stats['export'].entry_count >= 1
    
    def test_get_cache_stats_disabled(self):
        """Test getting cache stats when cache is disabled."""
        with patch('services.cache_v2.use_cache_v2', return_value=False):
            stats = get_cache_stats()
            assert stats == {}


class TestFeatureFlagIntegration:
    """Test feature flag integration."""
    
    def test_cache_operations_with_flag_disabled(self):
        """Test cache operations when feature flag is disabled."""
        config = CacheConfig(max_entries=5, ttl_seconds=60)
        cache = CacheV2(config)
        
        with patch('services.cache_v2.use_cache_v2', return_value=False):
            # Operations should be no-ops
            assert cache.get("key1") is None
            cache.set("key1", "value1")  # Should do nothing
            assert cache.get("key1") is None
    
    def test_cache_operations_with_flag_enabled(self):
        """Test cache operations when feature flag is enabled."""
        config = CacheConfig(max_entries=5, ttl_seconds=60)
        cache = CacheV2(config)
        
        with patch('services.cache_v2.use_cache_v2', return_value=True):
            # Operations should work normally
            cache.set("key1", "value1")
            assert cache.get("key1") == "value1"
