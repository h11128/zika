"""
Apply flow and conflict resolution service.
Implements merge strategies for card collections with stable UUID-based merging,
row order preservation, and latest-edit-wins conflict resolution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import logging

from services.card_models import Card, CardCollection


class ConflictResolutionPolicy(Enum):
    """Conflict resolution policies for merging changes."""
    LATEST_EDIT_WINS = "latest_edit_wins"
    FIRST_EDIT_WINS = "first_edit_wins"
    MANUAL_RESOLUTION = "manual_resolution"


class ChangeType(Enum):
    """Types of changes that can be applied."""
    FIELD_EDIT = "field_edit"
    CARD_ADDITION = "card_addition"
    CARD_DELETION = "card_deletion"
    CARD_REORDER = "card_reorder"


@dataclass
class ChangeRecord:
    """Records a single change operation."""
    change_type: ChangeType
    card_id: str
    field: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: Optional[datetime] = None
    user_id: Optional[str] = None

    def __post_init__(self):
        """Ensure timezone-aware timestamp."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
        elif self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class ConflictInfo:
    """Information about a detected conflict."""
    card_id: str
    field: str
    base_value: str
    local_value: str
    remote_value: str
    local_timestamp: datetime
    remote_timestamp: datetime
    
    @property
    def latest_value(self) -> str:
        """Get the value from the latest edit."""
        return self.remote_value if self.remote_timestamp > self.local_timestamp else self.local_value
    
    @property
    def is_conflict(self) -> bool:
        """Check if this represents an actual conflict."""
        return self.local_value != self.remote_value


@dataclass
class MergeResult:
    """Result of a merge operation."""
    merged_collection: CardCollection
    conflicts_detected: List[ConflictInfo]
    conflicts_resolved: List[ConflictInfo]
    changes_applied: List[ChangeRecord]
    success: bool
    error_message: Optional[str] = None
    
    @property
    def has_conflicts(self) -> bool:
        """Check if there were any conflicts."""
        return len(self.conflicts_detected) > 0
    
    @property
    def all_conflicts_resolved(self) -> bool:
        """Check if all conflicts were resolved."""
        return len(self.conflicts_resolved) == len(self.conflicts_detected)


class MergeService:
    """Service for merging card collection changes with conflict resolution."""
    
    def __init__(self, conflict_policy: ConflictResolutionPolicy = ConflictResolutionPolicy.LATEST_EDIT_WINS):
        self.conflict_policy = conflict_policy
        self.logger = logging.getLogger(__name__)
    
    def merge_changes(
        self, 
        base_collection: CardCollection,
        changes: List[ChangeRecord],
        preserve_order: bool = True
    ) -> MergeResult:
        """
        Merge changes into base collection with conflict resolution.
        
        Args:
            base_collection: Original card collection
            changes: List of changes to apply
            preserve_order: Whether to preserve original card order
            
        Returns:
            MergeResult with merged collection and conflict information
        """
        try:
            # Group changes by type and card ID
            field_edits = self._group_field_edits(changes)
            deletions = self._get_deletions(changes)
            additions = self._get_additions(changes)
            
            # Start with a copy of the base collection
            working_collection = CardCollection(base_collection.cards.copy())
            
            # Track conflicts
            conflicts_detected = []
            conflicts_resolved = []
            applied_changes = []
            
            # Apply field edits with conflict detection
            for card_id, field_changes in field_edits.items():
                card = working_collection.get_card(card_id)
                if not card:
                    self.logger.warning(f"Card {card_id} not found for field edits")
                    continue
                
                # Detect conflicts between concurrent edits
                card_conflicts = self._detect_field_conflicts(card, field_changes)
                conflicts_detected.extend(card_conflicts)
                
                # Resolve conflicts according to policy
                resolved_changes = self._resolve_field_conflicts(card_conflicts, field_changes)
                conflicts_resolved.extend(card_conflicts)
                
                # Apply resolved changes
                if resolved_changes:
                    success = self._apply_field_changes(working_collection, card_id, resolved_changes)
                    if success:
                        applied_changes.extend(resolved_changes)
            
            # Apply deletions
            for card_id in deletions:
                if working_collection.remove_card(card_id):
                    applied_changes.append(ChangeRecord(
                        change_type=ChangeType.CARD_DELETION,
                        card_id=card_id
                    ))
            
            # Apply additions
            for new_card in additions:
                if working_collection.add_card(new_card):
                    applied_changes.append(ChangeRecord(
                        change_type=ChangeType.CARD_ADDITION,
                        card_id=new_card.id
                    ))
            
            # Preserve order if requested
            if preserve_order:
                working_collection = self._preserve_card_order(base_collection, working_collection)
            
            return MergeResult(
                merged_collection=working_collection,
                conflicts_detected=conflicts_detected,
                conflicts_resolved=conflicts_resolved,
                changes_applied=applied_changes,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Merge operation failed: {e}")
            return MergeResult(
                merged_collection=base_collection,
                conflicts_detected=[],
                conflicts_resolved=[],
                changes_applied=[],
                success=False,
                error_message=str(e)
            )
    
    def _group_field_edits(self, changes: List[ChangeRecord]) -> Dict[str, List[ChangeRecord]]:
        """Group field edit changes by card ID."""
        field_edits = {}
        for change in changes:
            if change.change_type == ChangeType.FIELD_EDIT:
                if change.card_id not in field_edits:
                    field_edits[change.card_id] = []
                field_edits[change.card_id].append(change)
        return field_edits
    
    def _get_deletions(self, changes: List[ChangeRecord]) -> Set[str]:
        """Get card IDs marked for deletion."""
        return {
            change.card_id for change in changes 
            if change.change_type == ChangeType.CARD_DELETION
        }
    
    def _get_additions(self, changes: List[ChangeRecord]) -> List[Card]:
        """Get new cards to be added."""
        additions = []
        for change in changes:
            if change.change_type == ChangeType.CARD_ADDITION and change.new_value:
                # Assume new_value contains card data as JSON or Card object
                if isinstance(change.new_value, Card):
                    additions.append(change.new_value)
        return additions
    
    def _detect_field_conflicts(self, card: Card, field_changes: List[ChangeRecord]) -> List[ConflictInfo]:
        """Detect conflicts in field changes for a single card."""
        conflicts = []
        
        # Group changes by field
        field_groups = {}
        for change in field_changes:
            if change.field not in field_groups:
                field_groups[change.field] = []
            field_groups[change.field].append(change)
        
        # Check for conflicts within each field
        for field, changes in field_groups.items():
            if len(changes) > 1:
                # Sort by timestamp to find latest
                changes.sort(key=lambda c: c.timestamp)
                
                # Get current field value
                current_value = getattr(card, field, "")
                
                # Check if there are conflicting values
                values = [change.new_value for change in changes]
                if len(set(values)) > 1:
                    # Create conflict info
                    conflict = ConflictInfo(
                        card_id=card.id,
                        field=field,
                        base_value=current_value,
                        local_value=changes[0].new_value,
                        remote_value=changes[-1].new_value,
                        local_timestamp=changes[0].timestamp,
                        remote_timestamp=changes[-1].timestamp
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _resolve_field_conflicts(
        self, 
        conflicts: List[ConflictInfo], 
        field_changes: List[ChangeRecord]
    ) -> List[ChangeRecord]:
        """Resolve field conflicts according to policy."""
        if self.conflict_policy == ConflictResolutionPolicy.LATEST_EDIT_WINS:
            # Keep only the latest change for each field
            field_latest = {}
            for change in field_changes:
                if change.field not in field_latest or change.timestamp > field_latest[change.field].timestamp:
                    field_latest[change.field] = change
            return list(field_latest.values())
        
        elif self.conflict_policy == ConflictResolutionPolicy.FIRST_EDIT_WINS:
            # Keep only the first change for each field
            field_first = {}
            for change in field_changes:
                if change.field not in field_first:
                    field_first[change.field] = change
            return list(field_first.values())
        
        else:
            # Manual resolution - return all changes for external handling
            return field_changes
    
    def _apply_field_changes(
        self, 
        collection: CardCollection, 
        card_id: str, 
        changes: List[ChangeRecord]
    ) -> bool:
        """Apply field changes to a card in the collection."""
        # Build update parameters
        update_params = {}
        for change in changes:
            if change.field and change.new_value is not None:
                update_params[change.field] = change.new_value
        
        if update_params:
            return collection.update_card(card_id, **update_params)
        return True
    
    def _preserve_card_order(
        self, 
        original_collection: CardCollection, 
        updated_collection: CardCollection
    ) -> CardCollection:
        """Preserve the original card order in the updated collection."""
        # Create mapping of card ID to card
        updated_cards_map = {card.id: card for card in updated_collection.cards}
        
        # Rebuild in original order, adding new cards at the end
        ordered_cards = []
        seen_ids = set()
        
        # First, add existing cards in original order
        for original_card in original_collection.cards:
            if original_card.id in updated_cards_map:
                ordered_cards.append(updated_cards_map[original_card.id])
                seen_ids.add(original_card.id)
        
        # Then add any new cards
        for card in updated_collection.cards:
            if card.id not in seen_ids:
                ordered_cards.append(card)
        
        return CardCollection(ordered_cards)


def create_change_record(
    change_type: ChangeType,
    card_id: str,
    field: str = None,
    old_value: str = None,
    new_value: str = None,
    user_id: str = None
) -> ChangeRecord:
    """Convenience function to create a change record."""
    return ChangeRecord(
        change_type=change_type,
        card_id=card_id,
        field=field,
        old_value=old_value,
        new_value=new_value,
        user_id=user_id
    )


# Global merge service instance
_merge_service = None


def get_merge_service() -> MergeService:
    """Get global merge service instance."""
    global _merge_service
    if _merge_service is None:
        _merge_service = MergeService()
    return _merge_service
