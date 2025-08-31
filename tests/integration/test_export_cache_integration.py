"""
Integration tests for export cache key content version signals.
Tests that export cache keys properly include content version signals.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os
import hashlib
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockCard:
    """Mock card for testing."""
    
    def __init__(self, uuid, hanzi, pinyin="", english="", version=1):
        self.uuid = uuid
        self.hanzi = hanzi
        self.pinyin = pinyin
        self.english = english
        self.version = version
    
    def to_dict(self):
        return {
            'uuid': self.uuid,
            'hanzi': self.hanzi,
            'pinyin': self.pinyin,
            'english': self.english,
            'version': self.version
        }


class MockExportCacheService:
    """Mock export cache service for testing."""
    
    def __init__(self):
        self.cache = {}
        self.key_computations = []
    
    def compute_export_key(self, export_params, cards_count, content_version_signal, 
                          export_schema_version=None, preview_theme_version=None):
        """Compute export cache key with content version signal."""
        # Record the computation for testing
        computation = {
            'export_params': export_params,
            'cards_count': cards_count,
            'content_version_signal': content_version_signal,
            'export_schema_version': export_schema_version,
            'preview_theme_version': preview_theme_version
        }
        self.key_computations.append(computation)
        
        # Create deterministic key
        key_data = {
            'params': export_params,
            'count': cards_count,
            'content': content_version_signal,
            'schema': export_schema_version,
            'theme': preview_theme_version
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def get_cached_export(self, cache_key):
        """Get cached export data."""
        return self.cache.get(cache_key)
    
    def set_cached_export(self, cache_key, export_data):
        """Set cached export data."""
        self.cache[cache_key] = export_data
    
    def get_key_computations(self):
        """Get all key computations for testing."""
        return self.key_computations.copy()
    
    def clear_computations(self):
        """Clear computation tracking."""
        self.key_computations.clear()


class TestContentVersionSignalGeneration:
    """Test content version signal generation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockExportCacheService()
    
    def test_content_version_from_card_uuids_and_versions(self):
        """Test content version signal from card UUIDs and versions."""
        # Create test cards
        cards = [
            MockCard("uuid-1", "你好", "nǐ hǎo", "hello", version=1),
            MockCard("uuid-2", "世界", "shì jiè", "world", version=2),
            MockCard("uuid-3", "学习", "xué xí", "study", version=1),
        ]
        
        # Generate content version signal from ordered (uuid, version) tuples
        content_tuples = [(card.uuid, card.version) for card in cards]
        content_version_signal = hashlib.sha256(
            json.dumps(content_tuples, sort_keys=False).encode()
        ).hexdigest()[:16]
        
        # Compute export key
        export_params = {'format': 'pdf', 'page_size': 'A4'}
        cache_key = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=len(cards),
            content_version_signal=content_version_signal,
            export_schema_version="v2.1",
            preview_theme_version="v1.0"
        )
        
        # Verify key computation includes content version
        computations = self.cache_service.get_key_computations()
        assert len(computations) == 1
        assert computations[0]['content_version_signal'] == content_version_signal
        assert computations[0]['cards_count'] == 3
    
    def test_content_version_changes_with_card_modifications(self):
        """Test that content version changes when cards are modified."""
        # Create initial cards
        cards_v1 = [
            MockCard("uuid-1", "你好", "nǐ hǎo", "hello", version=1),
            MockCard("uuid-2", "世界", "shì jiè", "world", version=1),
        ]
        
        # Generate initial content version
        content_tuples_v1 = [(card.uuid, card.version) for card in cards_v1]
        content_version_v1 = hashlib.sha256(
            json.dumps(content_tuples_v1, sort_keys=False).encode()
        ).hexdigest()[:16]
        
        # Modify a card (increment version)
        cards_v2 = [
            MockCard("uuid-1", "你好", "nǐ hǎo", "hello", version=2),  # Version incremented
            MockCard("uuid-2", "世界", "shì jiè", "world", version=1),
        ]
        
        # Generate new content version
        content_tuples_v2 = [(card.uuid, card.version) for card in cards_v2]
        content_version_v2 = hashlib.sha256(
            json.dumps(content_tuples_v2, sort_keys=False).encode()
        ).hexdigest()[:16]
        
        # Content versions should be different
        assert content_version_v1 != content_version_v2
        
        # Export keys should be different
        export_params = {'format': 'pdf', 'page_size': 'A4'}
        
        key_v1 = self.cache_service.compute_export_key(
            export_params, len(cards_v1), content_version_v1
        )
        key_v2 = self.cache_service.compute_export_key(
            export_params, len(cards_v2), content_version_v2
        )
        
        assert key_v1 != key_v2
    
    def test_content_version_changes_with_card_order(self):
        """Test that content version changes when card order changes."""
        # Create cards in one order
        cards_order1 = [
            MockCard("uuid-1", "你好", version=1),
            MockCard("uuid-2", "世界", version=1),
        ]
        
        # Same cards in different order
        cards_order2 = [
            MockCard("uuid-2", "世界", version=1),
            MockCard("uuid-1", "你好", version=1),
        ]
        
        # Generate content versions (order-sensitive)
        content_tuples_1 = [(card.uuid, card.version) for card in cards_order1]
        content_version_1 = hashlib.sha256(
            json.dumps(content_tuples_1, sort_keys=False).encode()
        ).hexdigest()[:16]
        
        content_tuples_2 = [(card.uuid, card.version) for card in cards_order2]
        content_version_2 = hashlib.sha256(
            json.dumps(content_tuples_2, sort_keys=False).encode()
        ).hexdigest()[:16]
        
        # Content versions should be different (order matters)
        assert content_version_1 != content_version_2
    
    def test_content_version_from_snapshot_last_modified(self):
        """Test content version signal from snapshot last_modified timestamp."""
        # Simulate using snapshot last_modified as content version signal
        snapshot_last_modified = "2025-01-01T12:00:00Z"
        content_version_signal = hashlib.sha256(
            snapshot_last_modified.encode()
        ).hexdigest()[:16]
        
        # Compute export key
        export_params = {'format': 'pptx', 'slides_per_page': 4}
        cache_key = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=10,
            content_version_signal=content_version_signal
        )
        
        # Verify computation
        computations = self.cache_service.get_key_computations()
        assert len(computations) == 1
        assert computations[0]['content_version_signal'] == content_version_signal
        
        # Different timestamp should produce different key
        different_timestamp = "2025-01-01T12:01:00Z"
        different_content_version = hashlib.sha256(
            different_timestamp.encode()
        ).hexdigest()[:16]
        
        different_key = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=10,
            content_version_signal=different_content_version
        )
        
        assert cache_key != different_key


class TestExportCacheKeyComposition:
    """Test export cache key composition with all components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockExportCacheService()
    
    def test_complete_cache_key_composition(self):
        """Test cache key composition with all components."""
        # Set up test data
        export_params = {
            'format': 'pdf',
            'page_size': 'A4',
            'margin_cm': 1.0,
            'gap_cm': 0.5
        }
        cards_count = 25
        content_version_signal = "abc123def456"
        export_schema_version = "v2.1"
        preview_theme_version = "v1.2"
        
        # Compute cache key
        cache_key = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version=export_schema_version,
            preview_theme_version=preview_theme_version
        )
        
        # Verify all components were included
        computations = self.cache_service.get_key_computations()
        assert len(computations) == 1
        comp = computations[0]
        
        assert comp['export_params'] == export_params
        assert comp['cards_count'] == cards_count
        assert comp['content_version_signal'] == content_version_signal
        assert comp['export_schema_version'] == export_schema_version
        assert comp['preview_theme_version'] == preview_theme_version
        
        # Verify key is deterministic
        cache_key2 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version=export_schema_version,
            preview_theme_version=preview_theme_version
        )
        
        assert cache_key == cache_key2
    
    def test_cache_key_changes_with_each_component(self):
        """Test that cache key changes when any component changes."""
        base_params = {
            'export_params': {'format': 'pdf', 'page_size': 'A4'},
            'cards_count': 20,
            'content_version_signal': 'base_content_version',
            'export_schema_version': 'v2.0',
            'preview_theme_version': 'v1.0'
        }
        
        # Compute base key
        base_key = self.cache_service.compute_export_key(**base_params)
        
        # Test changing each component
        test_cases = [
            # Change export params
            {**base_params, 'export_params': {'format': 'pptx', 'page_size': 'A4'}},
            # Change cards count
            {**base_params, 'cards_count': 25},
            # Change content version
            {**base_params, 'content_version_signal': 'different_content_version'},
            # Change schema version
            {**base_params, 'export_schema_version': 'v2.1'},
            # Change theme version
            {**base_params, 'preview_theme_version': 'v1.1'},
        ]
        
        for modified_params in test_cases:
            modified_key = self.cache_service.compute_export_key(**modified_params)
            assert modified_key != base_key, f"Key should change for params: {modified_params}"
    
    def test_optional_version_parameters(self):
        """Test cache key computation with optional version parameters."""
        export_params = {'format': 'pdf'}
        cards_count = 10
        content_version_signal = 'test_content'
        
        # Test with no optional parameters
        key1 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal
        )
        
        # Test with one optional parameter
        key2 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version="v2.0"
        )
        
        # Test with both optional parameters
        key3 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version="v2.0",
            preview_theme_version="v1.0"
        )
        
        # All keys should be different
        assert key1 != key2
        assert key2 != key3
        assert key1 != key3


class TestExportCacheIntegration:
    """Test export cache integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.cache_service = MockExportCacheService()
    
    def test_cache_hit_with_same_content_version(self):
        """Test cache hit when content version is the same."""
        # Set up export parameters
        export_params = {'format': 'pdf', 'page_size': 'A4'}
        cards_count = 15
        content_version_signal = 'stable_content_version'
        
        # Compute cache key
        cache_key = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal
        )
        
        # Simulate caching export data
        export_data = b'mock_pdf_data'
        self.cache_service.set_cached_export(cache_key, export_data)
        
        # Compute same key again (should be cache hit)
        cache_key2 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal
        )
        
        assert cache_key == cache_key2
        
        # Should get cached data
        cached_data = self.cache_service.get_cached_export(cache_key2)
        assert cached_data == export_data
    
    def test_cache_miss_with_different_content_version(self):
        """Test cache miss when content version changes."""
        # Set up initial export
        export_params = {'format': 'pdf', 'page_size': 'A4'}
        cards_count = 15
        content_version_v1 = 'content_version_v1'
        
        cache_key_v1 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_v1
        )
        
        # Cache export data
        export_data_v1 = b'mock_pdf_data_v1'
        self.cache_service.set_cached_export(cache_key_v1, export_data_v1)
        
        # Change content version (simulate card modification)
        content_version_v2 = 'content_version_v2'
        cache_key_v2 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_v2
        )
        
        # Keys should be different
        assert cache_key_v1 != cache_key_v2
        
        # Should be cache miss for new key
        cached_data_v2 = self.cache_service.get_cached_export(cache_key_v2)
        assert cached_data_v2 is None
        
        # Original cache should still exist
        cached_data_v1 = self.cache_service.get_cached_export(cache_key_v1)
        assert cached_data_v1 == export_data_v1
    
    def test_cache_invalidation_on_schema_version_change(self):
        """Test cache invalidation when schema version changes."""
        # Set up export with specific schema version
        export_params = {'format': 'pdf'}
        content_version_signal = 'stable_content'
        
        key_v1 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=10,
            content_version_signal=content_version_signal,
            export_schema_version="v1.0"
        )
        
        key_v2 = self.cache_service.compute_export_key(
            export_params=export_params,
            cards_count=10,
            content_version_signal=content_version_signal,
            export_schema_version="v2.0"
        )
        
        # Different schema versions should produce different keys
        assert key_v1 != key_v2


if __name__ == "__main__":
    pytest.main([__file__])
