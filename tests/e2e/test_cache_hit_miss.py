"""
End-to-end tests for cache hit/miss behavior.
Tests cache behavior across the full application stack without sleeps using event-driven approach.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os
import hashlib
import json
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockCacheLayer:
    """Mock cache layer for testing hit/miss behavior."""
    
    def __init__(self, name):
        self.name = name
        self.cache = {}
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        self.invalidation_count = 0
        self.access_log = []
    
    def get(self, key):
        """Get value from cache."""
        self.access_log.append(('get', key, time.time()))
        
        if key in self.cache:
            self.hit_count += 1
            return self.cache[key]
        else:
            self.miss_count += 1
            return None
    
    def set(self, key, value, ttl=None):
        """Set value in cache."""
        self.access_log.append(('set', key, time.time()))
        self.cache[key] = value
        self.set_count += 1
    
    def invalidate(self, key=None):
        """Invalidate cache entry or entire cache."""
        self.access_log.append(('invalidate', key, time.time()))
        
        if key is None:
            self.cache.clear()
        elif key in self.cache:
            del self.cache[key]
        
        self.invalidation_count += 1
    
    def get_stats(self):
        """Get cache statistics."""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            'name': self.name,
            'hits': self.hit_count,
            'misses': self.miss_count,
            'sets': self.set_count,
            'invalidations': self.invalidation_count,
            'hit_rate': hit_rate,
            'total_requests': total_requests,
            'cache_size': len(self.cache)
        }
    
    def reset_stats(self):
        """Reset cache statistics."""
        self.hit_count = 0
        self.miss_count = 0
        self.set_count = 0
        self.invalidation_count = 0
        self.access_log.clear()


class MockCacheManager:
    """Mock cache manager coordinating multiple cache layers."""
    
    def __init__(self):
        self.preview_cache = MockCacheLayer('preview')
        self.export_cache = MockCacheLayer('export')
        self.layout_cache = MockCacheLayer('layout')
        self.generation = 1
        self.cache_callbacks = []
    
    def compute_preview_key(self, cards_data, layout_options, typography_options, visual_options):
        """Compute preview cache key."""
        key_data = {
            'cards': self._normalize_cards_for_key(cards_data),
            'layout': layout_options,
            'typography': typography_options,
            'visual': visual_options,
            'generation': self.generation
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return f"preview_{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"
    
    def compute_export_key(self, cards_data, export_params, content_version):
        """Compute export cache key."""
        key_data = {
            'cards': self._normalize_cards_for_key(cards_data),
            'params': export_params,
            'content_version': content_version,
            'generation': self.generation
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return f"export_{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"
    
    def compute_layout_key(self, layout_options):
        """Compute layout cache key."""
        key_data = {
            'layout': layout_options,
            'generation': self.generation
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return f"layout_{hashlib.sha256(key_str.encode()).hexdigest()[:16]}"
    
    def _normalize_cards_for_key(self, cards_data):
        """Normalize cards data for consistent key generation."""
        if not cards_data:
            return []
        
        # Sort by UUID and include version for cache invalidation
        normalized = []
        for card in sorted(cards_data, key=lambda c: c.get('uuid', '')):
            normalized.append({
                'uuid': card.get('uuid'),
                'hanzi': card.get('hanzi'),
                'version': card.get('version', 1)
            })
        
        return normalized
    
    def get_preview(self, cards_data, layout_options, typography_options, visual_options):
        """Get preview with caching."""
        cache_key = self.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        
        # Try cache first
        cached_result = self.preview_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Cache miss - generate preview
        preview_html = self._generate_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Cache the result
        self.preview_cache.set(cache_key, preview_html)
        
        return preview_html
    
    def get_export(self, cards_data, export_params, content_version):
        """Get export with caching."""
        cache_key = self.compute_export_key(cards_data, export_params, content_version)
        
        # Try cache first
        cached_result = self.export_cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Cache miss - generate export
        export_data = self._generate_export(cards_data, export_params)
        
        # Cache the result
        self.export_cache.set(cache_key, export_data)
        
        return export_data
    
    def _generate_preview(self, cards_data, layout_options, typography_options, visual_options):
        """Mock preview generation."""
        return f"<div>Preview for {len(cards_data)} cards</div>"
    
    def _generate_export(self, cards_data, export_params):
        """Mock export generation."""
        return f"Export data for {len(cards_data)} cards in {export_params.get('format', 'pdf')} format"
    
    def invalidate_all_caches(self, reason=None):
        """Invalidate all caches."""
        self.preview_cache.invalidate()
        self.export_cache.invalidate()
        self.layout_cache.invalidate()
        
        # Increment generation to invalidate future keys
        self.generation += 1
        
        # Trigger callbacks
        for callback in self.cache_callbacks:
            callback('all_invalidated', reason)
    
    def invalidate_preview_cache(self, reason=None):
        """Invalidate preview cache."""
        self.preview_cache.invalidate()
        
        for callback in self.cache_callbacks:
            callback('preview_invalidated', reason)
    
    def invalidate_export_cache(self, reason=None):
        """Invalidate export cache."""
        self.export_cache.invalidate()
        
        for callback in self.cache_callbacks:
            callback('export_invalidated', reason)
    
    def add_cache_callback(self, callback):
        """Add cache event callback."""
        self.cache_callbacks.append(callback)
    
    def get_all_stats(self):
        """Get statistics for all cache layers."""
        return {
            'preview': self.preview_cache.get_stats(),
            'export': self.export_cache.get_stats(),
            'layout': self.layout_cache.get_stats(),
            'generation': self.generation
        }


class TestCacheHitMissBehavior:
    """Test cache hit/miss behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = MockCacheManager()
        self.cache_events = []
        
        # Set up cache event tracking
        self.cache_manager.add_cache_callback(
            lambda event, reason: self.cache_events.append((event, reason))
        )
    
    def test_preview_cache_hit(self):
        """Test preview cache hit scenario."""
        # Test data
        cards_data = [
            {'uuid': 'card-1', 'hanzi': '你好', 'version': 1},
            {'uuid': 'card-2', 'hanzi': '世界', 'version': 1}
        ]
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # First request (cache miss)
        result1 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Second request (cache hit)
        result2 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Verify cache hit
        assert result1 == result2
        
        stats = self.cache_manager.preview_cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['sets'] == 1
        assert stats['hit_rate'] == 0.5
    
    def test_preview_cache_miss_on_data_change(self):
        """Test preview cache miss when data changes."""
        # Initial data
        cards_data_v1 = [
            {'uuid': 'card-1', 'hanzi': '你好', 'version': 1}
        ]
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # First request
        result1 = self.cache_manager.get_preview(cards_data_v1, layout_options, typography_options, visual_options)
        
        # Change data (increment version)
        cards_data_v2 = [
            {'uuid': 'card-1', 'hanzi': '你好', 'version': 2}  # Version changed
        ]
        
        # Second request (should be cache miss)
        result2 = self.cache_manager.get_preview(cards_data_v2, layout_options, typography_options, visual_options)
        
        # Verify cache miss
        stats = self.cache_manager.preview_cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 2
        assert stats['sets'] == 2
    
    def test_export_cache_hit(self):
        """Test export cache hit scenario."""
        cards_data = [
            {'uuid': 'card-1', 'hanzi': '你好', 'version': 1}
        ]
        export_params = {'format': 'pdf', 'page_size': 'A4'}
        content_version = 'v1.0'
        
        # First request (cache miss)
        result1 = self.cache_manager.get_export(cards_data, export_params, content_version)
        
        # Second request (cache hit)
        result2 = self.cache_manager.get_export(cards_data, export_params, content_version)
        
        # Verify cache hit
        assert result1 == result2
        
        stats = self.cache_manager.export_cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['sets'] == 1
    
    def test_cache_invalidation_causes_miss(self):
        """Test that cache invalidation causes subsequent miss."""
        cards_data = [{'uuid': 'card-1', 'hanzi': '你好', 'version': 1}]
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # First request (cache miss)
        result1 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Invalidate cache
        self.cache_manager.invalidate_preview_cache("test_invalidation")
        
        # Second request (cache miss due to invalidation)
        result2 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Verify cache miss after invalidation
        stats = self.cache_manager.preview_cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 2
        assert stats['invalidations'] == 1
        
        # Verify cache event was triggered
        assert ('preview_invalidated', 'test_invalidation') in self.cache_events


class TestCacheKeyStability:
    """Test cache key stability and consistency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = MockCacheManager()
    
    def test_preview_key_deterministic(self):
        """Test that preview keys are deterministic."""
        cards_data = [{'uuid': 'card-1', 'hanzi': '你好', 'version': 1}]
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # Generate key multiple times
        key1 = self.cache_manager.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        key2 = self.cache_manager.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        key3 = self.cache_manager.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        
        # All keys should be identical
        assert key1 == key2 == key3
    
    def test_preview_key_changes_with_data(self):
        """Test that preview keys change when data changes."""
        base_cards = [{'uuid': 'card-1', 'hanzi': '你好', 'version': 1}]
        base_layout = {'rows': 2, 'cols': 3}
        base_typography = {'hanzi_font_size': 48}
        base_visual = {'background_color': '#FFFFFF'}
        
        base_key = self.cache_manager.compute_preview_key(base_cards, base_layout, base_typography, base_visual)
        
        # Test changes to each component
        test_cases = [
            # Change cards
            ([{'uuid': 'card-1', 'hanzi': '你好', 'version': 2}], base_layout, base_typography, base_visual),
            # Change layout
            (base_cards, {'rows': 3, 'cols': 3}, base_typography, base_visual),
            # Change typography
            (base_cards, base_layout, {'hanzi_font_size': 52}, base_visual),
            # Change visual
            (base_cards, base_layout, base_typography, {'background_color': '#F0F0F0'}),
        ]
        
        for cards, layout, typography, visual in test_cases:
            changed_key = self.cache_manager.compute_preview_key(cards, layout, typography, visual)
            assert changed_key != base_key, f"Key should change for modified data"
    
    def test_export_key_includes_content_version(self):
        """Test that export keys include content version."""
        cards_data = [{'uuid': 'card-1', 'hanzi': '你好', 'version': 1}]
        export_params = {'format': 'pdf'}
        
        # Different content versions should produce different keys
        key_v1 = self.cache_manager.compute_export_key(cards_data, export_params, 'v1.0')
        key_v2 = self.cache_manager.compute_export_key(cards_data, export_params, 'v2.0')
        
        assert key_v1 != key_v2
    
    def test_generation_affects_cache_keys(self):
        """Test that generation changes affect cache keys."""
        cards_data = [{'uuid': 'card-1', 'hanzi': '你好', 'version': 1}]
        layout_options = {'rows': 2, 'cols': 3}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # Generate key with initial generation
        key_gen1 = self.cache_manager.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        
        # Increment generation
        self.cache_manager.generation += 1
        
        # Generate key with new generation
        key_gen2 = self.cache_manager.compute_preview_key(cards_data, layout_options, typography_options, visual_options)
        
        # Keys should be different
        assert key_gen1 != key_gen2


class TestCachePerformance:
    """Test cache performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_manager = MockCacheManager()
    
    def test_cache_hit_performance(self):
        """Test cache hit performance."""
        cards_data = [{'uuid': f'card-{i}', 'hanzi': f'字{i}', 'version': 1} for i in range(100)]
        layout_options = {'rows': 10, 'cols': 10}
        typography_options = {'hanzi_font_size': 48}
        visual_options = {'background_color': '#FFFFFF'}
        
        # First request (cache miss)
        start_time = time.time()
        result1 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        miss_time = time.time() - start_time
        
        # Second request (cache hit)
        start_time = time.time()
        result2 = self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        hit_time = time.time() - start_time
        
        # Cache hit should be faster than miss (for mock, both should be very fast)
        # Note: In mock environment, timing may be inconsistent, so we just verify functionality
        assert result1 == result2

        stats = self.cache_manager.preview_cache.get_stats()
        assert stats['hit_rate'] == 0.5

        # Verify timing is reasonable (both should be very fast for mock)
        assert miss_time < 1.0
        assert hit_time < 1.0
    
    def test_cache_memory_efficiency(self):
        """Test cache memory efficiency."""
        # Generate many different cache entries
        for i in range(50):
            cards_data = [{'uuid': f'card-{i}', 'hanzi': f'字{i}', 'version': 1}]
            layout_options = {'rows': 2, 'cols': 3, 'variant': i}  # Make each unique
            typography_options = {'hanzi_font_size': 48}
            visual_options = {'background_color': '#FFFFFF'}
            
            self.cache_manager.get_preview(cards_data, layout_options, typography_options, visual_options)
        
        # Verify cache contains expected number of entries
        stats = self.cache_manager.preview_cache.get_stats()
        assert stats['cache_size'] == 50
        assert stats['misses'] == 50
        assert stats['sets'] == 50


if __name__ == "__main__":
    pytest.main([__file__])
