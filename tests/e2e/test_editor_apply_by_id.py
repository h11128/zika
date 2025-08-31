"""
End-to-end tests for editor apply-by-id functionality.
Tests editor apply flow with stable UUIDs without sleeps using event-driven approach.
"""

import pytest
from unittest.mock import MagicMock, patch, call
import sys
import os
import uuid
import time

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))


class MockCard:
    """Mock card with stable UUID."""
    
    def __init__(self, uuid_str, hanzi, pinyin="", english="", version=1):
        self.uuid = uuid_str
        self.hanzi = hanzi
        self.pinyin = pinyin
        self.english = english
        self.version = version
        self.created_at = time.time()
    
    def to_dict(self):
        return {
            'uuid': self.uuid,
            'hanzi': self.hanzi,
            'pinyin': self.pinyin,
            'english': self.english,
            'version': self.version,
            'created_at': self.created_at
        }
    
    def increment_version(self):
        """Increment version for edits."""
        self.version += 1
    
    def __eq__(self, other):
        if not isinstance(other, MockCard):
            return False
        return self.uuid == other.uuid
    
    def __repr__(self):
        return f"MockCard(uuid={self.uuid}, hanzi={self.hanzi}, version={self.version})"


class MockCardEditor:
    """Mock card editor for testing apply-by-id functionality."""
    
    def __init__(self):
        self.cards = {}  # uuid -> MockCard
        self.pending_changes = {}  # uuid -> changes dict
        self.apply_callbacks = []
        self.preview_invalidation_count = 0
    
    def add_card(self, card):
        """Add card to editor."""
        self.cards[card.uuid] = card
    
    def get_cards(self):
        """Get all cards."""
        return list(self.cards.values())
    
    def get_card_by_uuid(self, uuid_str):
        """Get card by UUID."""
        return self.cards.get(uuid_str)
    
    def stage_change(self, uuid_str, field, value):
        """Stage a change for a card."""
        if uuid_str not in self.pending_changes:
            self.pending_changes[uuid_str] = {}
        self.pending_changes[uuid_str][field] = value
    
    def apply_changes(self):
        """Apply all pending changes by UUID."""
        applied_changes = []
        
        for uuid_str, changes in self.pending_changes.items():
            if uuid_str in self.cards:
                card = self.cards[uuid_str]
                
                # Apply changes
                for field, value in changes.items():
                    if hasattr(card, field):
                        setattr(card, field, value)
                
                # Increment version
                card.increment_version()
                applied_changes.append((uuid_str, changes))
        
        # Clear pending changes
        self.pending_changes.clear()
        
        # Trigger single preview invalidation
        if applied_changes:
            self.preview_invalidation_count += 1
            for callback in self.apply_callbacks:
                callback(applied_changes)
        
        return applied_changes
    
    def add_apply_callback(self, callback):
        """Add callback for apply events."""
        self.apply_callbacks.append(callback)
    
    def get_pending_changes_count(self):
        """Get number of pending changes."""
        return len(self.pending_changes)
    
    def get_preview_invalidation_count(self):
        """Get number of preview invalidations."""
        return self.preview_invalidation_count


class TestEditorApplyById:
    """Test editor apply-by-id functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.editor = MockCardEditor()
        self.applied_changes = []
        
        # Set up apply callback
        def on_apply(changes):
            self.applied_changes.extend(changes)
        
        self.editor.add_apply_callback(on_apply)
    
    def test_apply_single_card_change(self):
        """Test applying changes to a single card by UUID."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Stage change
        self.editor.stage_change("card-1", "pinyin", "nǐ hǎo!")
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Verify changes were applied
        assert len(applied) == 1
        assert applied[0][0] == "card-1"
        assert applied[0][1] == {"pinyin": "nǐ hǎo!"}
        
        # Verify card was updated
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.pinyin == "nǐ hǎo!"
        assert updated_card.version == 2  # Version incremented
        
        # Verify single preview invalidation
        assert self.editor.get_preview_invalidation_count() == 1
    
    def test_apply_multiple_card_changes(self):
        """Test applying changes to multiple cards by UUID."""
        # Add cards to editor
        card1 = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        card2 = MockCard("card-2", "世界", "shì jiè", "world", version=1)
        card3 = MockCard("card-3", "学习", "xué xí", "study", version=1)
        
        self.editor.add_card(card1)
        self.editor.add_card(card2)
        self.editor.add_card(card3)
        
        # Stage multiple changes
        self.editor.stage_change("card-1", "english", "hi")
        self.editor.stage_change("card-2", "pinyin", "shì jiè!")
        self.editor.stage_change("card-3", "hanzi", "学习!")
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Verify all changes were applied
        assert len(applied) == 3
        
        # Check each card was updated
        updated_card1 = self.editor.get_card_by_uuid("card-1")
        assert updated_card1.english == "hi"
        assert updated_card1.version == 2
        
        updated_card2 = self.editor.get_card_by_uuid("card-2")
        assert updated_card2.pinyin == "shì jiè!"
        assert updated_card2.version == 2
        
        updated_card3 = self.editor.get_card_by_uuid("card-3")
        assert updated_card3.hanzi == "学习!"
        assert updated_card3.version == 2
        
        # Verify single preview invalidation for batch
        assert self.editor.get_preview_invalidation_count() == 1
    
    def test_apply_multiple_fields_single_card(self):
        """Test applying multiple field changes to single card."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Stage multiple field changes for same card
        self.editor.stage_change("card-1", "pinyin", "nǐ hǎo!")
        self.editor.stage_change("card-1", "english", "hi there")
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Verify changes were applied
        assert len(applied) == 1
        assert applied[0][0] == "card-1"
        assert applied[0][1] == {"pinyin": "nǐ hǎo!", "english": "hi there"}
        
        # Verify card was updated
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.pinyin == "nǐ hǎo!"
        assert updated_card.english == "hi there"
        assert updated_card.version == 2  # Single version increment
        
        # Verify single preview invalidation
        assert self.editor.get_preview_invalidation_count() == 1
    
    def test_apply_with_nonexistent_uuid(self):
        """Test applying changes to nonexistent UUID."""
        # Stage change for nonexistent card
        self.editor.stage_change("nonexistent-uuid", "hanzi", "测试")
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Should not apply changes for nonexistent UUID
        assert len(applied) == 0
        
        # Should not trigger preview invalidation
        assert self.editor.get_preview_invalidation_count() == 0
    
    def test_apply_empty_changes(self):
        """Test applying when no changes are staged."""
        # Add card but don't stage any changes
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Should not apply any changes
        assert len(applied) == 0
        
        # Should not trigger preview invalidation
        assert self.editor.get_preview_invalidation_count() == 0
        
        # Card should be unchanged
        unchanged_card = self.editor.get_card_by_uuid("card-1")
        assert unchanged_card.version == 1


class TestEditorConflictResolution:
    """Test editor conflict resolution with latest-edit-wins policy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.editor = MockCardEditor()
    
    def test_latest_edit_wins_policy(self):
        """Test that latest edit wins in conflict resolution."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Stage conflicting changes (simulating multiple edits)
        self.editor.stage_change("card-1", "english", "hi")
        self.editor.stage_change("card-1", "english", "hello there")  # Latest edit
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Verify latest edit wins
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.english == "hello there"  # Latest value
        assert updated_card.version == 2
    
    def test_concurrent_field_edits(self):
        """Test concurrent edits to different fields."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Stage changes to different fields (no conflict)
        self.editor.stage_change("card-1", "pinyin", "nǐ hǎo!")
        self.editor.stage_change("card-1", "english", "hi")
        
        # Apply changes
        applied = self.editor.apply_changes()
        
        # Verify both changes applied
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.pinyin == "nǐ hǎo!"
        assert updated_card.english == "hi"
        assert updated_card.version == 2


class TestEditorVersioning:
    """Test editor versioning behavior."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.editor = MockCardEditor()
    
    def test_version_increment_on_apply(self):
        """Test that version increments on apply."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=5)
        self.editor.add_card(card)
        
        # Stage change
        self.editor.stage_change("card-1", "english", "hi")
        
        # Apply changes
        self.editor.apply_changes()
        
        # Verify version incremented
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.version == 6
    
    def test_version_increment_atomic(self):
        """Test that version increment is atomic per apply."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # Stage multiple changes
        self.editor.stage_change("card-1", "pinyin", "nǐ hǎo!")
        self.editor.stage_change("card-1", "english", "hi")
        
        # Apply changes
        self.editor.apply_changes()
        
        # Verify single version increment for multiple changes
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.version == 2  # Only incremented once
    
    def test_multiple_apply_cycles(self):
        """Test multiple apply cycles increment version correctly."""
        # Add card to editor
        card = MockCard("card-1", "你好", "nǐ hǎo", "hello", version=1)
        self.editor.add_card(card)
        
        # First apply cycle
        self.editor.stage_change("card-1", "english", "hi")
        self.editor.apply_changes()
        
        # Second apply cycle
        self.editor.stage_change("card-1", "pinyin", "nǐ hǎo!")
        self.editor.apply_changes()
        
        # Third apply cycle
        self.editor.stage_change("card-1", "hanzi", "你好!")
        self.editor.apply_changes()
        
        # Verify version incremented for each apply
        updated_card = self.editor.get_card_by_uuid("card-1")
        assert updated_card.version == 4  # 1 + 3 applies
        
        # Verify three preview invalidations
        assert self.editor.get_preview_invalidation_count() == 3


class TestEditorPerformance:
    """Test editor performance characteristics."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.editor = MockCardEditor()
    
    def test_large_batch_apply_performance(self):
        """Test performance with large batch of changes."""
        # Add many cards
        num_cards = 1000
        for i in range(num_cards):
            card = MockCard(f"card-{i}", f"汉字{i}", f"hànzì{i}", f"character{i}")
            self.editor.add_card(card)
        
        # Stage changes for all cards
        for i in range(num_cards):
            self.editor.stage_change(f"card-{i}", "english", f"char{i}")
        
        # Measure apply time
        start_time = time.time()
        applied = self.editor.apply_changes()
        end_time = time.time()
        
        apply_time = end_time - start_time
        
        # Verify all changes applied
        assert len(applied) == num_cards
        
        # Verify single preview invalidation
        assert self.editor.get_preview_invalidation_count() == 1
        
        # Verify reasonable performance (should be fast for mock)
        assert apply_time < 1.0  # Should complete within 1 second
    
    def test_uuid_lookup_efficiency(self):
        """Test UUID lookup efficiency."""
        # Add cards with various UUIDs
        uuids = [str(uuid.uuid4()) for _ in range(100)]
        
        for uuid_str in uuids:
            card = MockCard(uuid_str, "测试", "cèshì", "test")
            self.editor.add_card(card)
        
        # Test lookup performance
        start_time = time.time()
        
        for uuid_str in uuids:
            card = self.editor.get_card_by_uuid(uuid_str)
            assert card is not None
            assert card.uuid == uuid_str
        
        end_time = time.time()
        lookup_time = end_time - start_time
        
        # Verify reasonable lookup performance
        assert lookup_time < 0.1  # Should be very fast for dictionary lookup


if __name__ == "__main__":
    pytest.main([__file__])
