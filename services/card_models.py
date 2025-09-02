"""
Card data models with stable UUID system and versioning.
Provides Card dataclass with stable IDs, version tracking, and content hashing.
"""

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field

from core.feature_flags import get_feature_flag


@dataclass(frozen=True)
class Card:
    """
    Immutable card with stable UUID and version tracking.
    
    The ID is stable across content edits. Content hash is used only
    for duplicate detection, not as the primary identifier.
    """
    id: str
    hanzi: str
    pinyin: str
    english: str
    version: int
    created_at: datetime
    
    def __post_init__(self):
        """Validate card data."""
        if not self.id:
            raise ValueError("Card ID cannot be empty")
        if not self.hanzi:
            raise ValueError("Card hanzi cannot be empty")
        if self.version < 1:
            raise ValueError("Card version must be >= 1")
        
        # Ensure timezone-aware datetime
        if self.created_at.tzinfo is None:
            object.__setattr__(self, 'created_at', 
                             self.created_at.replace(tzinfo=timezone.utc))
    
    @classmethod
    def create_new(cls, hanzi: str, pinyin: str = "", english: str = "") -> 'Card':
        """Create a new card with generated UUID.
        Allows creating an 'empty' placeholder card by using a single-space hanzi,
        which passes validation but is treated as empty by is_empty().
        """
        sanitized_hanzi = hanzi.strip()
        if not sanitized_hanzi:
            sanitized_hanzi = " "  # placeholder to satisfy validation
        return cls(
            id=str(uuid.uuid4()),
            hanzi=sanitized_hanzi,
            pinyin=pinyin.strip(),
            english=english.strip(),
            version=1,
            created_at=datetime.now(timezone.utc)
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Card':
        """Create card from dictionary (for migration/loading)."""
        # Handle legacy data without ID
        card_id = data.get('id')
        if not card_id:
            card_id = str(uuid.uuid4())
        
        # Handle legacy data without version
        version = data.get('version', 1)
        
        # Handle legacy data without created_at
        created_at = data.get('created_at')
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif isinstance(created_at, datetime) and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)
        
        return cls(
            id=card_id,
            hanzi=data.get('hanzi', ''),
            pinyin=data.get('pinyin', ''),
            english=data.get('english', ''),
            version=version,
            created_at=created_at
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary for serialization."""
        return {
            'id': self.id,
            'hanzi': self.hanzi,
            'pinyin': self.pinyin,
            'english': self.english,
            'version': self.version,
            'created_at': self.created_at.isoformat()
        }
    
    def to_legacy_dict(self) -> Dict[str, str]:
        """Convert to legacy format for backward compatibility."""
        return {
            'hanzi': self.hanzi,
            'pinyin': self.pinyin,
            'english': self.english
        }
    
    def edit(self, hanzi: str = None, pinyin: str = None, english: str = None) -> 'Card':
        """Create new card with edited content and incremented version."""
        return Card(
            id=self.id,  # Keep same ID
            hanzi=hanzi.strip() if hanzi is not None else self.hanzi,
            pinyin=pinyin.strip() if pinyin is not None else self.pinyin,
            english=english.strip() if english is not None else self.english,
            version=self.version + 1,  # Increment version
            created_at=self.created_at  # Keep original creation time
        )
    
    def content_hash(self) -> str:
        """
        Compute content hash for duplicate detection.
        
        This is NOT used as the primary ID, only for finding duplicates.
        """
        normalized_content = {
            'hanzi': self.hanzi.strip().lower(),
            'pinyin': self.pinyin.strip().lower(),
            'english': self.english.strip().lower()
        }
        content_str = json.dumps(normalized_content, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()[:16]
    
    def is_empty(self) -> bool:
        """Check if card has no meaningful content."""
        return not (self.hanzi.strip() or self.pinyin.strip() or self.english.strip())
    
    def has_content_changed(self, other: 'Card') -> bool:
        """Check if content has changed compared to another card."""
        return (self.hanzi != other.hanzi or 
                self.pinyin != other.pinyin or 
                self.english != other.english)


class CardCollection:
    """Manages a collection of cards with stable IDs and duplicate detection."""
    
    def __init__(self, cards: List[Card] = None):
        self.cards: List[Card] = cards or []
        self._id_index: Dict[str, int] = {}
        self._content_hash_index: Dict[str, List[int]] = {}
        self._rebuild_indices()
    
    def _rebuild_indices(self) -> None:
        """Rebuild internal indices for fast lookups."""
        self._id_index.clear()
        self._content_hash_index.clear()
        
        for i, card in enumerate(self.cards):
            # ID index
            self._id_index[card.id] = i
            
            # Content hash index (for duplicate detection)
            content_hash = card.content_hash()
            if content_hash not in self._content_hash_index:
                self._content_hash_index[content_hash] = []
            self._content_hash_index[content_hash].append(i)
    
    def add_card(self, card: Card) -> bool:
        """
        Add card to collection.
        
        Returns:
            True if added, False if duplicate content detected
        """
        # Check for duplicate content
        if self.has_duplicate_content(card):
            return False
        
        self.cards.append(card)
        self._rebuild_indices()
        return True
    
    def update_card(self, card_id: str, hanzi: str = None, 
                   pinyin: str = None, english: str = None) -> bool:
        """
        Update card by ID with new content.
        
        Returns:
            True if updated, False if card not found
        """
        if card_id not in self._id_index:
            return False
        
        index = self._id_index[card_id]
        old_card = self.cards[index]
        new_card = old_card.edit(hanzi=hanzi, pinyin=pinyin, english=english)
        
        # Check for duplicate content (excluding self)
        temp_cards = self.cards[:index] + self.cards[index+1:]
        temp_collection = CardCollection(temp_cards)
        if temp_collection.has_duplicate_content(new_card):
            return False
        
        self.cards[index] = new_card
        self._rebuild_indices()
        return True
    
    def remove_card(self, card_id: str) -> bool:
        """
        Remove card by ID.
        
        Returns:
            True if removed, False if card not found
        """
        if card_id not in self._id_index:
            return False
        
        index = self._id_index[card_id]
        del self.cards[index]
        self._rebuild_indices()
        return True
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """Get card by ID."""
        if card_id not in self._id_index:
            return None
        return self.cards[self._id_index[card_id]]
    
    def has_duplicate_content(self, card: Card) -> bool:
        """Check if card has duplicate content in collection."""
        content_hash = card.content_hash()
        if content_hash not in self._content_hash_index:
            return False
        
        # Check if any existing card with same hash has different ID
        for index in self._content_hash_index[content_hash]:
            existing_card = self.cards[index]
            if existing_card.id != card.id:
                return True
        
        return False
    
    def find_duplicates(self) -> List[List[Card]]:
        """Find all groups of duplicate cards."""
        duplicate_groups = []
        
        for content_hash, indices in self._content_hash_index.items():
            if len(indices) > 1:
                group = [self.cards[i] for i in indices]
                duplicate_groups.append(group)
        
        return duplicate_groups
    
    def merge_cards(self, card_updates: List[Dict[str, Any]]) -> 'CardCollection':
        """
        Merge card updates by ID, preserving order.
        
        Args:
            card_updates: List of dicts with 'id' and content fields
            
        Returns:
            New CardCollection with merged changes
        """
        new_cards = []
        update_map = {update['id']: update for update in card_updates}
        
        # Process existing cards
        for card in self.cards:
            if card.id in update_map:
                update = update_map[card.id]
                new_card = card.edit(
                    hanzi=update.get('hanzi'),
                    pinyin=update.get('pinyin'),
                    english=update.get('english')
                )
                new_cards.append(new_card)
                del update_map[card.id]  # Mark as processed
            else:
                new_cards.append(card)
        
        # Add new cards (those not in existing collection)
        for update in update_map.values():
            new_card = Card.from_dict(update)
            new_cards.append(new_card)
        
        return CardCollection(new_cards)
    
    def to_legacy_format(self) -> List[Dict[str, str]]:
        """Convert to legacy format for backward compatibility."""
        return [card.to_legacy_dict() for card in self.cards]
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries for serialization."""
        return [card.to_dict() for card in self.cards]
    
    @classmethod
    def from_legacy_format(cls, legacy_cards: List[Dict[str, str]]) -> 'CardCollection':
        """Create collection from legacy format."""
        cards = []
        for legacy_card in legacy_cards:
            card = Card.create_new(
                hanzi=legacy_card.get('hanzi', ''),
                pinyin=legacy_card.get('pinyin', ''),
                english=legacy_card.get('english', '')
            )
            cards.append(card)
        return cls(cards)
    
    @classmethod
    def from_dict_list(cls, card_dicts: List[Dict[str, Any]]) -> 'CardCollection':
        """Create collection from list of dictionaries."""
        cards = [Card.from_dict(card_dict) for card_dict in card_dicts]
        return cls(cards)
    
    def __len__(self) -> int:
        """Get number of cards."""
        return len(self.cards)
    
    def __iter__(self):
        """Iterate over cards."""
        return iter(self.cards)
    
    def __getitem__(self, index: int) -> Card:
        """Get card by index."""
        return self.cards[index]


def migrate_legacy_cards(legacy_cards: List[Dict[str, str]]) -> CardCollection:
    """
    Migrate legacy card format to new Card system.
    
    Args:
        legacy_cards: List of dicts with hanzi, pinyin, english
        
    Returns:
        CardCollection with stable IDs
    """
    if not get_feature_flag('stable_card_ids', False):
        # Return legacy format wrapped in collection
        return CardCollection.from_legacy_format(legacy_cards)
    
    cards = []
    seen_hashes: Set[str] = set()
    
    for legacy_card in legacy_cards:
        # Create card with new ID
        card = Card.create_new(
            hanzi=legacy_card.get('hanzi', ''),
            pinyin=legacy_card.get('pinyin', ''),
            english=legacy_card.get('english', '')
        )
        
        # Skip duplicates
        content_hash = card.content_hash()
        if content_hash in seen_hashes:
            continue
        
        seen_hashes.add(content_hash)
        cards.append(card)
    
    return CardCollection(cards)


def use_stable_card_ids() -> bool:
    """Check if stable card IDs should be used."""
    return get_feature_flag('stable_card_ids', False)
