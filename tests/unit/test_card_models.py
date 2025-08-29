"""
Unit tests for services/card_models.py
Tests Card dataclass, CardCollection, and migration functions.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from services.card_models import (
    Card, CardCollection, migrate_legacy_cards, use_stable_card_ids
)


class TestCard:
    """Test Card dataclass."""
    
    def test_card_creation(self):
        """Test basic card creation."""
        now = datetime.now(timezone.utc)
        card = Card(
            id="test-id",
            hanzi="爱",
            pinyin="ài",
            english="love",
            version=1,
            created_at=now
        )
        
        assert card.id == "test-id"
        assert card.hanzi == "爱"
        assert card.pinyin == "ài"
        assert card.english == "love"
        assert card.version == 1
        assert card.created_at == now
    
    def test_card_validation(self):
        """Test card validation."""
        now = datetime.now(timezone.utc)
        
        # Empty ID should fail
        with pytest.raises(ValueError, match="Card ID cannot be empty"):
            Card("", "爱", "ài", "love", 1, now)
        
        # Empty hanzi should fail
        with pytest.raises(ValueError, match="Card hanzi cannot be empty"):
            Card("test-id", "", "ài", "love", 1, now)
        
        # Invalid version should fail
        with pytest.raises(ValueError, match="Card version must be >= 1"):
            Card("test-id", "爱", "ài", "love", 0, now)
    
    def test_create_new(self):
        """Test creating new card with generated UUID."""
        card = Card.create_new("爱", "ài", "love")
        
        assert card.hanzi == "爱"
        assert card.pinyin == "ài"
        assert card.english == "love"
        assert card.version == 1
        assert card.created_at.tzinfo == timezone.utc
        assert len(card.id) == 36  # UUID format
    
    def test_from_dict(self):
        """Test creating card from dictionary."""
        data = {
            'id': 'test-id',
            'hanzi': '爱',
            'pinyin': 'ài',
            'english': 'love',
            'version': 2,
            'created_at': '2023-01-01T00:00:00+00:00'
        }
        
        card = Card.from_dict(data)
        
        assert card.id == 'test-id'
        assert card.hanzi == '爱'
        assert card.version == 2
        assert card.created_at.year == 2023
    
    def test_from_dict_legacy(self):
        """Test creating card from legacy dictionary without ID."""
        data = {
            'hanzi': '爱',
            'pinyin': 'ài',
            'english': 'love'
        }
        
        card = Card.from_dict(data)
        
        assert len(card.id) == 36  # Generated UUID
        assert card.version == 1  # Default version
        assert card.created_at.tzinfo == timezone.utc
    
    def test_to_dict(self):
        """Test converting card to dictionary."""
        card = Card.create_new("爱", "ài", "love")
        data = card.to_dict()
        
        assert data['id'] == card.id
        assert data['hanzi'] == "爱"
        assert data['pinyin'] == "ài"
        assert data['english'] == "love"
        assert data['version'] == 1
        assert 'created_at' in data
    
    def test_to_legacy_dict(self):
        """Test converting card to legacy format."""
        card = Card.create_new("爱", "ài", "love")
        legacy = card.to_legacy_dict()
        
        expected = {
            'hanzi': "爱",
            'pinyin': "ài",
            'english': "love"
        }
        assert legacy == expected
    
    def test_edit(self):
        """Test editing card content."""
        original = Card.create_new("爱", "ài", "love")
        edited = original.edit(english="affection")
        
        assert edited.id == original.id  # Same ID
        assert edited.hanzi == original.hanzi  # Unchanged
        assert edited.pinyin == original.pinyin  # Unchanged
        assert edited.english == "affection"  # Changed
        assert edited.version == original.version + 1  # Incremented
        assert edited.created_at == original.created_at  # Same creation time
    
    def test_content_hash(self):
        """Test content hash computation."""
        card1 = Card.create_new("爱", "ài", "love")
        card2 = Card.create_new("爱", "ài", "love")  # Same content, different ID
        card3 = Card.create_new("家", "jiā", "home")  # Different content
        
        # Same content should have same hash
        assert card1.content_hash() == card2.content_hash()
        
        # Different content should have different hash
        assert card1.content_hash() != card3.content_hash()
        
        # Hash should be deterministic
        assert card1.content_hash() == card1.content_hash()
    
    def test_is_empty(self):
        """Test empty card detection."""
        empty_card = Card.create_new("", "", "")
        non_empty_card = Card.create_new("爱", "", "")
        
        assert empty_card.is_empty()
        assert not non_empty_card.is_empty()
    
    def test_has_content_changed(self):
        """Test content change detection."""
        original = Card.create_new("爱", "ài", "love")
        same_content = Card.create_new("爱", "ài", "love")
        different_content = original.edit(english="affection")
        
        assert not original.has_content_changed(same_content)
        assert original.has_content_changed(different_content)


class TestCardCollection:
    """Test CardCollection class."""
    
    def test_empty_collection(self):
        """Test empty collection."""
        collection = CardCollection()
        
        assert len(collection) == 0
        assert list(collection) == []
    
    def test_add_card(self):
        """Test adding cards to collection."""
        collection = CardCollection()
        card = Card.create_new("爱", "ài", "love")
        
        result = collection.add_card(card)
        
        assert result is True
        assert len(collection) == 1
        assert collection[0] == card
    
    def test_add_duplicate_card(self):
        """Test adding duplicate card."""
        collection = CardCollection()
        card1 = Card.create_new("爱", "ài", "love")
        card2 = Card.create_new("爱", "ài", "love")  # Same content
        
        collection.add_card(card1)
        result = collection.add_card(card2)
        
        assert result is False  # Duplicate rejected
        assert len(collection) == 1
    
    def test_update_card(self):
        """Test updating card in collection."""
        collection = CardCollection()
        card = Card.create_new("爱", "ài", "love")
        collection.add_card(card)
        
        result = collection.update_card(card.id, english="affection")
        
        assert result is True
        updated_card = collection.get_card(card.id)
        assert updated_card.english == "affection"
        assert updated_card.version == card.version + 1
    
    def test_update_nonexistent_card(self):
        """Test updating non-existent card."""
        collection = CardCollection()
        
        result = collection.update_card("nonexistent", english="test")
        
        assert result is False
    
    def test_remove_card(self):
        """Test removing card from collection."""
        collection = CardCollection()
        card = Card.create_new("爱", "ài", "love")
        collection.add_card(card)
        
        result = collection.remove_card(card.id)
        
        assert result is True
        assert len(collection) == 0
        assert collection.get_card(card.id) is None
    
    def test_get_card(self):
        """Test getting card by ID."""
        collection = CardCollection()
        card = Card.create_new("爱", "ài", "love")
        collection.add_card(card)
        
        retrieved = collection.get_card(card.id)
        
        assert retrieved == card
        assert collection.get_card("nonexistent") is None
    
    def test_has_duplicate_content(self):
        """Test duplicate content detection."""
        collection = CardCollection()
        card1 = Card.create_new("爱", "ài", "love")
        card2 = Card.create_new("爱", "ài", "love")  # Same content
        card3 = Card.create_new("家", "jiā", "home")  # Different content
        
        collection.add_card(card1)
        
        assert collection.has_duplicate_content(card2)
        assert not collection.has_duplicate_content(card3)
    
    def test_find_duplicates(self):
        """Test finding duplicate groups."""
        collection = CardCollection()
        
        # Add cards with some duplicates
        card1 = Card.create_new("爱", "ài", "love")
        card2 = Card.create_new("爱", "ài", "love")  # Duplicate of card1
        card3 = Card.create_new("家", "jiā", "home")
        
        # Force add duplicates by bypassing duplicate check
        collection.cards = [card1, card2, card3]
        collection._rebuild_indices()
        
        duplicates = collection.find_duplicates()
        
        assert len(duplicates) == 1
        assert len(duplicates[0]) == 2
        assert card1 in duplicates[0]
        assert card2 in duplicates[0]
    
    def test_merge_cards(self):
        """Test merging card updates."""
        collection = CardCollection()
        card1 = Card.create_new("爱", "ài", "love")
        card2 = Card.create_new("家", "jiā", "home")
        collection.add_card(card1)
        collection.add_card(card2)
        
        updates = [
            {'id': card1.id, 'english': 'affection'},
            {'id': str(uuid.uuid4()), 'hanzi': '水', 'pinyin': 'shuǐ', 'english': 'water'}
        ]
        
        new_collection = collection.merge_cards(updates)
        
        assert len(new_collection) == 3  # 2 existing + 1 new
        updated_card1 = new_collection.get_card(card1.id)
        assert updated_card1.english == 'affection'
        assert updated_card1.version == card1.version + 1
    
    def test_to_legacy_format(self):
        """Test converting to legacy format."""
        collection = CardCollection()
        card = Card.create_new("爱", "ài", "love")
        collection.add_card(card)
        
        legacy = collection.to_legacy_format()
        
        expected = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        assert legacy == expected
    
    def test_from_legacy_format(self):
        """Test creating collection from legacy format."""
        legacy_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
        
        collection = CardCollection.from_legacy_format(legacy_cards)
        
        assert len(collection) == 2
        assert collection[0].hanzi == '爱'
        assert collection[1].hanzi == '家'
        assert all(len(card.id) == 36 for card in collection)  # All have UUIDs


class TestMigrationFunctions:
    """Test migration and utility functions."""
    
    def test_migrate_legacy_cards_disabled(self):
        """Test migration when feature flag is disabled."""
        legacy_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
        
        with patch('services.card_models.get_feature_flag', return_value=False):
            collection = migrate_legacy_cards(legacy_cards)
        
        assert len(collection) == 2
        # Should still create UUIDs even when disabled
        assert all(len(card.id) == 36 for card in collection)
    
    def test_migrate_legacy_cards_enabled(self):
        """Test migration when feature flag is enabled."""
        legacy_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}  # Duplicate
        ]
        
        with patch('services.card_models.get_feature_flag', return_value=True):
            collection = migrate_legacy_cards(legacy_cards)
        
        assert len(collection) == 2  # Duplicate removed
        assert collection[0].hanzi == '爱'
        assert collection[1].hanzi == '家'
    
    def test_use_stable_card_ids(self):
        """Test feature flag check."""
        with patch('services.card_models.get_feature_flag', return_value=True):
            assert use_stable_card_ids() is True
        
        with patch('services.card_models.get_feature_flag', return_value=False):
            assert use_stable_card_ids() is False
