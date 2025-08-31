"""
Unit tests for merge service and conflict resolution.
Tests apply flow, conflict detection, and latest-edit-wins policy.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import uuid

from services.merge_service import (
    MergeService, ChangeRecord, ChangeType, ConflictResolutionPolicy,
    ConflictInfo, MergeResult, create_change_record, get_merge_service
)
from services.card_models import Card, CardCollection


class TestChangeRecord:
    """Test change record functionality."""
    
    def test_change_record_creation(self):
        """Test creating change records."""
        record = create_change_record(
            change_type=ChangeType.FIELD_EDIT,
            card_id="card1",
            field="hanzi",
            old_value="老",
            new_value="新"
        )
        
        assert record.change_type == ChangeType.FIELD_EDIT
        assert record.card_id == "card1"
        assert record.field == "hanzi"
        assert record.old_value == "老"
        assert record.new_value == "新"
        assert record.timestamp.tzinfo is not None
    
    def test_change_record_timezone_handling(self):
        """Test timezone handling in change records."""
        # Test with naive datetime
        naive_time = datetime.now()
        record = ChangeRecord(
            change_type=ChangeType.FIELD_EDIT,
            card_id="card1",
            timestamp=naive_time
        )
        
        # Should be converted to UTC
        assert record.timestamp.tzinfo == timezone.utc


class TestConflictInfo:
    """Test conflict information handling."""
    
    def test_conflict_detection(self):
        """Test conflict detection logic."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(minutes=5)
        
        conflict = ConflictInfo(
            card_id="card1",
            field="hanzi",
            base_value="原",
            local_value="本",
            remote_value="地",
            local_timestamp=now,
            remote_timestamp=later
        )
        
        assert conflict.is_conflict is True
        assert conflict.latest_value == "地"  # Remote is later
    
    def test_no_conflict_same_values(self):
        """Test no conflict when values are the same."""
        now = datetime.now(timezone.utc)
        
        conflict = ConflictInfo(
            card_id="card1",
            field="hanzi",
            base_value="原",
            local_value="同",
            remote_value="同",
            local_timestamp=now,
            remote_timestamp=now
        )
        
        assert conflict.is_conflict is False


class TestMergeService:
    """Test merge service functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.merge_service = MergeService(ConflictResolutionPolicy.LATEST_EDIT_WINS)
        
        # Create test cards
        self.card1 = Card.create_new("一", "yi", "one")
        self.card2 = Card.create_new("二", "er", "two")
        self.card3 = Card.create_new("三", "san", "three")
        
        self.collection = CardCollection([self.card1, self.card2, self.card3])
    
    def test_merge_service_initialization(self):
        """Test merge service initialization."""
        service = MergeService()
        assert service.conflict_policy == ConflictResolutionPolicy.LATEST_EDIT_WINS
        
        service_custom = MergeService(ConflictResolutionPolicy.FIRST_EDIT_WINS)
        assert service_custom.conflict_policy == ConflictResolutionPolicy.FIRST_EDIT_WINS
    
    def test_merge_simple_field_edits(self):
        """Test merging simple field edits without conflicts."""
        changes = [
            create_change_record(
                ChangeType.FIELD_EDIT, self.card1.id, "english", "one", "ONE"
            ),
            create_change_record(
                ChangeType.FIELD_EDIT, self.card2.id, "pinyin", "er", "èr"
            )
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes)
        
        assert result.success is True
        assert len(result.conflicts_detected) == 0
        assert len(result.changes_applied) == 2
        
        # Check changes were applied
        updated_card1 = result.merged_collection.get_card(self.card1.id)
        updated_card2 = result.merged_collection.get_card(self.card2.id)
        
        assert updated_card1.english == "ONE"
        assert updated_card2.pinyin == "èr"
    
    def test_merge_with_conflicts_latest_wins(self):
        """Test merging with conflicts using latest-edit-wins policy."""
        now = datetime.now(timezone.utc)
        later = now + timedelta(minutes=5)
        
        changes = [
            ChangeRecord(
                change_type=ChangeType.FIELD_EDIT,
                card_id=self.card1.id,
                field="english",
                old_value="one",
                new_value="first",
                timestamp=now
            ),
            ChangeRecord(
                change_type=ChangeType.FIELD_EDIT,
                card_id=self.card1.id,
                field="english",
                old_value="one",
                new_value="latest",
                timestamp=later
            )
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes)
        
        assert result.success is True
        assert len(result.conflicts_detected) > 0
        assert len(result.conflicts_resolved) > 0
        
        # Latest edit should win
        updated_card = result.merged_collection.get_card(self.card1.id)
        assert updated_card.english == "latest"
    
    def test_merge_with_conflicts_first_wins(self):
        """Test merging with conflicts using first-edit-wins policy."""
        service = MergeService(ConflictResolutionPolicy.FIRST_EDIT_WINS)
        
        now = datetime.now(timezone.utc)
        later = now + timedelta(minutes=5)
        
        changes = [
            ChangeRecord(
                change_type=ChangeType.FIELD_EDIT,
                card_id=self.card1.id,
                field="english",
                old_value="one",
                new_value="first",
                timestamp=now
            ),
            ChangeRecord(
                change_type=ChangeType.FIELD_EDIT,
                card_id=self.card1.id,
                field="english",
                old_value="one",
                new_value="second",
                timestamp=later
            )
        ]
        
        result = service.merge_changes(self.collection, changes)
        
        assert result.success is True
        
        # First edit should win
        updated_card = result.merged_collection.get_card(self.card1.id)
        assert updated_card.english == "first"
    
    def test_merge_card_deletions(self):
        """Test merging card deletions."""
        changes = [
            create_change_record(ChangeType.CARD_DELETION, self.card2.id)
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes)
        
        assert result.success is True
        assert len(result.merged_collection) == 2
        assert result.merged_collection.get_card(self.card2.id) is None
    
    def test_merge_card_additions(self):
        """Test merging card additions."""
        new_card = Card.create_new("四", "si", "four")
        
        changes = [
            ChangeRecord(
                change_type=ChangeType.CARD_ADDITION,
                card_id=new_card.id,
                new_value=new_card
            )
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes)
        
        assert result.success is True
        assert len(result.merged_collection) == 4
        assert result.merged_collection.get_card(new_card.id) is not None
    
    def test_preserve_card_order(self):
        """Test that card order is preserved during merge."""
        # Add a new card at the beginning conceptually
        new_card = Card.create_new("零", "ling", "zero")
        
        changes = [
            ChangeRecord(
                change_type=ChangeType.CARD_ADDITION,
                card_id=new_card.id,
                new_value=new_card
            ),
            create_change_record(
                ChangeType.FIELD_EDIT, self.card2.id, "english", "two", "TWO"
            )
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes, preserve_order=True)
        
        assert result.success is True
        
        # Original cards should maintain their relative order
        cards = result.merged_collection.cards
        original_indices = []
        for original_card in [self.card1, self.card2, self.card3]:
            for i, card in enumerate(cards):
                if card.id == original_card.id:
                    original_indices.append(i)
                    break
        
        # Should be in ascending order (preserving original order)
        assert original_indices == sorted(original_indices)
        
        # New card should be at the end
        assert cards[-1].id == new_card.id
    
    def test_merge_error_handling(self):
        """Test merge error handling."""
        # Create invalid changes that might cause errors
        changes = [
            create_change_record(
                ChangeType.FIELD_EDIT, "nonexistent_card", "hanzi", "old", "new"
            )
        ]
        
        # Should handle gracefully
        result = self.merge_service.merge_changes(self.collection, changes)
        
        # Should still succeed even with invalid card ID
        assert result.success is True
    
    def test_complex_merge_scenario(self):
        """Test complex merge scenario with multiple change types."""
        new_card = Card.create_new("四", "si", "four")
        
        changes = [
            # Edit existing cards
            create_change_record(
                ChangeType.FIELD_EDIT, self.card1.id, "english", "one", "ONE"
            ),
            create_change_record(
                ChangeType.FIELD_EDIT, self.card1.id, "pinyin", "yi", "yī"
            ),
            # Delete a card
            create_change_record(ChangeType.CARD_DELETION, self.card3.id),
            # Add a new card
            ChangeRecord(
                change_type=ChangeType.CARD_ADDITION,
                card_id=new_card.id,
                new_value=new_card
            )
        ]
        
        result = self.merge_service.merge_changes(self.collection, changes)
        
        assert result.success is True
        assert len(result.merged_collection) == 3  # 3 original - 1 deleted + 1 added
        
        # Check edits were applied
        updated_card1 = result.merged_collection.get_card(self.card1.id)
        assert updated_card1.english == "ONE"
        assert updated_card1.pinyin == "yī"
        
        # Check deletion
        assert result.merged_collection.get_card(self.card3.id) is None
        
        # Check addition
        assert result.merged_collection.get_card(new_card.id) is not None


class TestMergeServiceIntegration:
    """Test merge service integration functions."""
    
    def test_get_merge_service_singleton(self):
        """Test that get_merge_service returns singleton."""
        service1 = get_merge_service()
        service2 = get_merge_service()
        
        assert service1 is service2
        assert isinstance(service1, MergeService)


class TestMergeResult:
    """Test merge result functionality."""
    
    def test_merge_result_properties(self):
        """Test merge result property calculations."""
        collection = CardCollection([])
        conflicts = [
            ConflictInfo("card1", "field1", "base", "local", "remote", 
                        datetime.now(timezone.utc), datetime.now(timezone.utc))
        ]
        
        result = MergeResult(
            merged_collection=collection,
            conflicts_detected=conflicts,
            conflicts_resolved=conflicts,
            changes_applied=[],
            success=True
        )
        
        assert result.has_conflicts is True
        assert result.all_conflicts_resolved is True
        
        # Test with unresolved conflicts
        result_unresolved = MergeResult(
            merged_collection=collection,
            conflicts_detected=conflicts,
            conflicts_resolved=[],
            changes_applied=[],
            success=True
        )
        
        assert result_unresolved.has_conflicts is True
        assert result_unresolved.all_conflicts_resolved is False


if __name__ == "__main__":
    pytest.main([__file__])
