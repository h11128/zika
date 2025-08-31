"""
Unit tests for enhanced export cache key with content version signals.
Tests compute_export_key, content version signal generation, and cache invalidation.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import directly from the state.py file to avoid conflict with state/ directory
import importlib.util
spec = importlib.util.spec_from_file_location("ui_state", os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'state.py'))
ui_state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state)

# Import the functions we need
compute_export_key = ui_state.compute_export_key
compute_cards_content_version_signal = ui_state.compute_cards_content_version_signal
compute_snapshot_content_version_signal = ui_state.compute_snapshot_content_version_signal
get_content_version_signal = ui_state.get_content_version_signal


class TestComputeExportKey:
    """Test enhanced export cache key computation."""
    
    def test_basic_export_key_computation(self):
        """Test basic export key computation."""
        export_params = {'format': 'pdf', 'quality': 'high'}
        cards_count = 10
        
        key = compute_export_key(export_params, cards_count)
        
        assert isinstance(key, str)
        assert len(key) == 16  # Truncated SHA256
    
    def test_export_key_with_content_version_signal(self):
        """Test export key with content version signal."""
        export_params = {'format': 'pdf', 'quality': 'high'}
        cards_count = 10
        content_version_signal = "test_signal_123"
        
        key = compute_export_key(export_params, cards_count, content_version_signal)
        
        assert isinstance(key, str)
        assert len(key) == 16
        
        # Key should be different without content version signal
        key_without_signal = compute_export_key(export_params, cards_count)
        assert key != key_without_signal
    
    def test_export_key_with_all_parameters(self):
        """Test export key with all optional parameters."""
        export_params = {'format': 'pptx', 'layout': 'grid'}
        cards_count = 15
        content_version_signal = "content_v2"
        export_schema_version = "v2.0.0"
        preview_theme_version = "theme_v1"
        
        key = compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version=export_schema_version,
            preview_theme_version=preview_theme_version
        )
        
        assert isinstance(key, str)
        assert len(key) == 16
    
    def test_export_key_deterministic(self):
        """Test that export keys are deterministic."""
        export_params = {'format': 'pdf', 'margin_cm': 1.0}
        cards_count = 5
        content_version_signal = "stable_signal"
        
        key1 = compute_export_key(export_params, cards_count, content_version_signal)
        key2 = compute_export_key(export_params, cards_count, content_version_signal)
        
        assert key1 == key2
    
    def test_export_key_different_params_different_keys(self):
        """Test that different parameters produce different keys."""
        base_params = {'format': 'pdf', 'quality': 'high'}
        cards_count = 10
        content_version_signal = "signal_123"
        
        key1 = compute_export_key(base_params, cards_count, content_version_signal)
        
        # Different export params
        different_params = {'format': 'pptx', 'quality': 'high'}
        key2 = compute_export_key(different_params, cards_count, content_version_signal)
        
        # Different cards count
        key3 = compute_export_key(base_params, 15, content_version_signal)
        
        # Different content version signal
        key4 = compute_export_key(base_params, cards_count, "different_signal")
        
        # All keys should be different
        keys = [key1, key2, key3, key4]
        assert len(set(keys)) == 4


class TestCardsContentVersionSignal:
    """Test cards content version signal generation."""
    
    def test_empty_cards_signal(self):
        """Test content version signal for empty cards."""
        signal = compute_cards_content_version_signal([])
        assert signal == "empty"
    
    def test_cards_with_uuid_and_version(self):
        """Test content version signal for cards with UUID and version."""
        cards = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
            {'id': 'uuid-2', 'version': 2, 'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'},
            {'id': 'uuid-3', 'version': 1, 'hanzi': '谢谢', 'pinyin': 'xiè xiè', 'english': 'thank you'}
        ]
        
        signal = compute_cards_content_version_signal(cards)
        
        assert isinstance(signal, str)
        assert len(signal) == 16
        assert signal != "empty"
    
    def test_cards_signal_deterministic_ordering(self):
        """Test that card order doesn't affect signal (sorted by UUID)."""
        cards1 = [
            {'id': 'uuid-a', 'version': 1, 'hanzi': '你好'},
            {'id': 'uuid-b', 'version': 2, 'hanzi': '再见'}
        ]
        
        cards2 = [
            {'id': 'uuid-b', 'version': 2, 'hanzi': '再见'},
            {'id': 'uuid-a', 'version': 1, 'hanzi': '你好'}
        ]
        
        signal1 = compute_cards_content_version_signal(cards1)
        signal2 = compute_cards_content_version_signal(cards2)
        
        assert signal1 == signal2
    
    def test_cards_signal_version_sensitivity(self):
        """Test that version changes affect the signal."""
        cards_v1 = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好'}
        ]
        
        cards_v2 = [
            {'id': 'uuid-1', 'version': 2, 'hanzi': '你好'}
        ]
        
        signal1 = compute_cards_content_version_signal(cards_v1)
        signal2 = compute_cards_content_version_signal(cards_v2)
        
        assert signal1 != signal2
    
    def test_cards_signal_legacy_cards_without_id(self):
        """Test content version signal for legacy cards without ID."""
        cards = [
            {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
            {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'}
        ]
        
        signal = compute_cards_content_version_signal(cards)
        
        assert isinstance(signal, str)
        assert len(signal) == 16
        assert signal != "empty"
    
    def test_cards_signal_mixed_legacy_and_new(self):
        """Test content version signal for mixed legacy and new cards."""
        cards = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好'},
            {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'}  # Legacy without ID
        ]
        
        signal = compute_cards_content_version_signal(cards)
        
        assert isinstance(signal, str)
        assert len(signal) == 16


class TestSnapshotContentVersionSignal:
    """Test snapshot content version signal generation."""
    
    def test_snapshot_signal_with_timestamp(self):
        """Test content version signal from timestamp."""
        timestamp = "2024-01-15T10:30:00.000Z"
        signal = compute_snapshot_content_version_signal(timestamp)
        
        assert isinstance(signal, str)
        assert len(signal) == 16
    
    def test_snapshot_signal_empty_timestamp(self):
        """Test content version signal with empty timestamp."""
        signal = compute_snapshot_content_version_signal("")
        assert signal == "no_timestamp"
        
        signal_none = compute_snapshot_content_version_signal(None)
        assert signal_none == "no_timestamp"
    
    def test_snapshot_signal_deterministic(self):
        """Test that same timestamp produces same signal."""
        timestamp = "2024-01-15T10:30:00.000Z"
        
        signal1 = compute_snapshot_content_version_signal(timestamp)
        signal2 = compute_snapshot_content_version_signal(timestamp)
        
        assert signal1 == signal2
    
    def test_snapshot_signal_different_timestamps(self):
        """Test that different timestamps produce different signals."""
        timestamp1 = "2024-01-15T10:30:00.000Z"
        timestamp2 = "2024-01-15T10:31:00.000Z"
        
        signal1 = compute_snapshot_content_version_signal(timestamp1)
        signal2 = compute_snapshot_content_version_signal(timestamp2)
        
        assert signal1 != signal2


class TestGetContentVersionSignal:
    """Test automatic content version signal selection."""
    
    def test_get_signal_prefers_cards_with_proper_structure(self):
        """Test that cards with UUID/version are preferred."""
        cards = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好'}
        ]
        snapshot_timestamp = "2024-01-15T10:30:00.000Z"
        
        signal = get_content_version_signal(cards, snapshot_timestamp)
        
        # Should use cards-based signal, not timestamp
        cards_signal = compute_cards_content_version_signal(cards)
        timestamp_signal = compute_snapshot_content_version_signal(snapshot_timestamp)
        
        assert signal == cards_signal
        assert signal != timestamp_signal
    
    def test_get_signal_falls_back_to_timestamp(self):
        """Test fallback to timestamp when cards lack proper structure."""
        cards = [
            {'hanzi': '你好', 'pinyin': 'nǐ hǎo'}  # No ID or version
        ]
        snapshot_timestamp = "2024-01-15T10:30:00.000Z"
        
        signal = get_content_version_signal(cards, snapshot_timestamp)
        
        # Should use timestamp-based signal
        timestamp_signal = compute_snapshot_content_version_signal(snapshot_timestamp)
        assert signal == timestamp_signal
    
    def test_get_signal_final_fallback_to_current_time(self):
        """Test final fallback to current time."""
        # Test that fallback produces a valid signal (don't test exact value due to timing)
        signal = get_content_version_signal(None, None)

        # Should produce a valid signal string
        assert isinstance(signal, str)
        assert len(signal) == 16
        assert signal != "empty"
        assert signal != "no_timestamp"

        # Should be deterministic for same inputs
        signal2 = get_content_version_signal(None, None)
        # Note: These might be different due to timing, but both should be valid
    
    def test_get_signal_empty_cards_uses_timestamp(self):
        """Test that empty cards list uses timestamp."""
        snapshot_timestamp = "2024-01-15T10:30:00.000Z"
        
        signal = get_content_version_signal([], snapshot_timestamp)
        
        # Should use timestamp-based signal
        timestamp_signal = compute_snapshot_content_version_signal(snapshot_timestamp)
        assert signal == timestamp_signal


class TestContentVersionSignalIntegration:
    """Test integration scenarios for content version signals."""
    
    def test_cache_invalidation_on_content_change(self):
        """Test that cache keys change when content changes."""
        export_params = {'format': 'pdf'}
        
        # Original cards
        cards_v1 = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好'}
        ]
        
        # Same card, different version (content changed)
        cards_v2 = [
            {'id': 'uuid-1', 'version': 2, 'hanzi': '你好'}
        ]
        
        signal_v1 = get_content_version_signal(cards_v1)
        signal_v2 = get_content_version_signal(cards_v2)
        
        key_v1 = compute_export_key(export_params, len(cards_v1), signal_v1)
        key_v2 = compute_export_key(export_params, len(cards_v2), signal_v2)
        
        # Keys should be different even though card count is the same
        assert key_v1 != key_v2
    
    def test_cache_consistency_with_same_content(self):
        """Test that cache keys are consistent with same content."""
        export_params = {'format': 'pptx', 'quality': 'high'}
        
        cards = [
            {'id': 'uuid-1', 'version': 1, 'hanzi': '你好'},
            {'id': 'uuid-2', 'version': 1, 'hanzi': '再见'}
        ]
        
        signal = get_content_version_signal(cards)
        
        # Multiple calls should produce same key
        key1 = compute_export_key(export_params, len(cards), signal)
        key2 = compute_export_key(export_params, len(cards), signal)
        
        assert key1 == key2
    
    def test_mixed_card_formats_consistency(self):
        """Test consistency with mixed legacy and new card formats."""
        export_params = {'format': 'pdf'}
        
        # Mixed format cards
        cards = [
            {'id': 'uuid-1', 'version': 2, 'hanzi': '你好'},  # New format
            {'hanzi': '再见', 'pinyin': 'zài jiàn'}  # Legacy format
        ]
        
        signal = get_content_version_signal(cards)
        key = compute_export_key(export_params, len(cards), signal)
        
        assert isinstance(key, str)
        assert len(key) == 16
        
        # Should be deterministic
        signal2 = get_content_version_signal(cards)
        key2 = compute_export_key(export_params, len(cards), signal2)
        assert key == key2


if __name__ == "__main__":
    pytest.main([__file__])
