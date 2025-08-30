"""
User data persistence with versioned snapshots and migration system.
Provides UserSnapshot dataclass, migration functions, and storage management.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict
import logging

from core.feature_flags import get_feature_flag
from core.field_migration import migrate_snapshot_data, get_field_with_alias
from services.card_models import Card, CardCollection


# Current snapshot version
CURRENT_SNAPSHOT_VERSION = 3

# Storage limits and quotas
MAX_INPUT_TEXT_LENGTH = 10000  # 10K characters
MAX_SNAPSHOT_SIZE_BYTES = 1024 * 1024  # 1MB
MAX_EXPORT_HISTORY_RECORDS = 50
EXPORT_HISTORY_RETENTION_DAYS = 30
MAX_CARDS_PER_SNAPSHOT = 1000  # Prevent memory issues
MAX_MIGRATION_RETRIES = 3  # Retry failed migrations

# Migration safety settings
ENABLE_MIGRATION_BACKUP = True
MIGRATION_BACKUP_RETENTION_HOURS = 24


@dataclass
class ExportRecord:
    """Single export history record."""
    timestamp: str  # ISO-8601 UTC
    format_type: str  # 'pdf', 'pptx', 'csv'
    card_count: int
    filename: str
    
    @classmethod
    def create_now(cls, format_type: str, card_count: int, filename: str) -> 'ExportRecord':
        """Create export record with current timestamp."""
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            format_type=format_type,
            card_count=card_count,
            filename=filename
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportRecord':
        """Create from dictionary with validation."""
        return cls(
            timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            format_type=data.get('format_type', 'unknown'),
            card_count=int(data.get('card_count', 0)),
            filename=data.get('filename', 'unknown')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def is_expired(self) -> bool:
        """Check if record is older than retention period."""
        try:
            record_time = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=EXPORT_HISTORY_RETENTION_DAYS)
            return record_time < cutoff_time
        except (ValueError, TypeError):
            return True  # Invalid timestamp, consider expired


@dataclass
class UserSnapshot:
    """Complete user data snapshot with versioning."""
    version: int
    created_at: str  # ISO-8601 UTC
    last_modified: str  # ISO-8601 UTC
    
    # Core data
    input_text: str
    cards: List[Dict[str, Any]]  # Card.to_dict() format
    
    # Configuration
    options: Dict[str, Any]  # Processing options
    layout: Dict[str, Any]   # Layout configuration
    typography: Dict[str, Any]  # Typography settings
    visual: Dict[str, Any]   # Visual preferences
    preview: Dict[str, Any]  # Preview settings
    
    # History
    export_history: List[Dict[str, Any]]  # ExportRecord.to_dict() format
    total_cards_generated: int = 0

    # Metadata
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    state_metadata: Dict[str, Any] = field(default_factory=dict)  # State management metadata
    
    def __post_init__(self):
        """Validate and normalize snapshot data."""
        # Ensure version is valid
        if self.version < 1:
            raise ValueError("Snapshot version must be >= 1")
        
        # Truncate input text if too long
        if len(self.input_text) > MAX_INPUT_TEXT_LENGTH:
            self.input_text = self.input_text[:MAX_INPUT_TEXT_LENGTH]
            logging.warning(f"Input text truncated to {MAX_INPUT_TEXT_LENGTH} characters")
        
        # Clean up export history
        self._cleanup_export_history()
    
    def _cleanup_export_history(self) -> None:
        """Clean up export history based on retention policy."""
        # Convert to ExportRecord objects for validation
        valid_records = []
        for record_data in self.export_history:
            try:
                record = ExportRecord.from_dict(record_data)
                if not record.is_expired():
                    valid_records.append(record.to_dict())
            except Exception:
                continue  # Skip invalid records
        
        # Limit to max records (keep most recent)
        if len(valid_records) > MAX_EXPORT_HISTORY_RECORDS:
            # Sort by timestamp (most recent first)
            valid_records.sort(key=lambda r: r.get('timestamp', ''), reverse=True)
            valid_records = valid_records[:MAX_EXPORT_HISTORY_RECORDS]
        
        self.export_history = valid_records
    
    @classmethod
    def create_empty(cls) -> 'UserSnapshot':
        """Create empty snapshot with current version."""
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            version=CURRENT_SNAPSHOT_VERSION,
            created_at=now,
            last_modified=now,
            input_text="",
            cards=[],
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=[],
            total_cards_generated=0
        )
    
    @classmethod
    def from_session_state(cls, session_state) -> 'UserSnapshot':
        """Create snapshot from current session state."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Extract cards
        cards_data = []
        processed_cards = getattr(session_state, 'processed_cards', [])
        if processed_cards:
            # Convert legacy format to Card objects then to dict
            try:
                from services.card_models import CardCollection
                collection = CardCollection.from_legacy_format(processed_cards)
                cards_data = collection.to_dict_list()
            except Exception:
                # Fallback to legacy format
                cards_data = processed_cards
        
        # Extract export history
        export_history = []
        history = getattr(session_state, 'export_history', [])
        for record in history:
            if isinstance(record, dict):
                export_history.append(record)
        
        return cls(
            version=CURRENT_SNAPSHOT_VERSION,
            created_at=now,
            last_modified=now,
            input_text=getattr(session_state, 'input_text', ''),
            cards=cards_data,
            options={
                'auto_pinyin': getattr(session_state, 'auto_pinyin', True),
                'auto_translate': getattr(session_state, 'auto_translate', True),
                'use_segmented': getattr(session_state, 'use_segmented', False),
            },
            layout={
                'rows': getattr(session_state, 'rows', 2),
                'cols': getattr(session_state, 'cols', 3),
                'auto_fill': getattr(session_state, 'auto_fill', True),
                'card_size': getattr(session_state, 'card_size', 5.5),
                # Use canonical field names for new snapshots
                'gap_cm': get_field_with_alias({
                    'gap': getattr(session_state, 'gap', None),
                    'gap_cm': getattr(session_state, 'gap_cm', None)
                }, 'gap_cm', 0.5),
                'margin_cm': get_field_with_alias({
                    'margin': getattr(session_state, 'margin', None),
                    'margin_cm': getattr(session_state, 'margin_cm', None)
                }, 'margin_cm', 1.0),
                'page_size': getattr(session_state, 'page_size', 'A4'),
            },
            typography={
                'font_hanzi': getattr(session_state, 'font_hanzi', 48),
                'font_pinyin': getattr(session_state, 'font_pinyin', 18),
                'font_english': getattr(session_state, 'font_english', 14),
                'hanzi_font': getattr(session_state, 'hanzi_font', 'SimHei'),
            },
            visual={
                'background_color': getattr(session_state, 'background_color', '#ffffff'),
                'preview_mode': getattr(session_state, 'preview_mode', '📄 完整页面'),
            },
            preview={
                'current_page': getattr(session_state, 'current_page', 0),
            },
            export_history=export_history,
            total_cards_generated=getattr(session_state, 'total_cards_generated', 0),
            state_metadata={
                'last_digest': getattr(session_state, 'last_digest', None),
                'cache_version': 1,
                'feature_flags_snapshot': {}
            }
        )
    
    def apply_to_session_state(self, session_state) -> None:
        """Apply snapshot data to session state."""
        # Apply core data
        session_state.input_text = self.input_text
        
        # Apply cards
        if self.cards:
            try:
                from services.card_models import CardCollection
                collection = CardCollection.from_dict_list(self.cards)
                session_state.processed_cards = collection.to_legacy_format()
            except Exception:
                # Fallback to direct assignment
                session_state.processed_cards = self.cards
        else:
            session_state.processed_cards = []
        
        # Apply configuration
        for key, value in self.options.items():
            setattr(session_state, key, value)
        
        for key, value in self.layout.items():
            setattr(session_state, key, value)
        
        for key, value in self.typography.items():
            setattr(session_state, key, value)
        
        for key, value in self.visual.items():
            setattr(session_state, key, value)
        
        for key, value in self.preview.items():
            setattr(session_state, key, value)
        
        # Apply history
        session_state.export_history = self.export_history
        session_state.total_cards_generated = self.total_cards_generated
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(',', ':'))
    
    def estimate_size_bytes(self) -> int:
        """Estimate snapshot size in bytes."""
        try:
            json_str = self.to_json()
            return len(json_str.encode('utf-8'))
        except Exception:
            return 0
    
    def is_too_large(self) -> bool:
        """Check if snapshot exceeds size limit."""
        return self.estimate_size_bytes() > MAX_SNAPSHOT_SIZE_BYTES

    def check_quota_violations(self) -> List[str]:
        """Check for various quota violations and return list of issues."""
        violations = []

        # Check size limit
        if self.is_too_large():
            violations.append(f"Snapshot size {self.estimate_size_bytes()} bytes exceeds limit {MAX_SNAPSHOT_SIZE_BYTES}")

        # Check input text length
        if len(self.input_text) > MAX_INPUT_TEXT_LENGTH:
            violations.append(f"Input text length {len(self.input_text)} exceeds limit {MAX_INPUT_TEXT_LENGTH}")

        # Check cards count
        if len(self.cards) > MAX_CARDS_PER_SNAPSHOT:
            violations.append(f"Cards count {len(self.cards)} exceeds limit {MAX_CARDS_PER_SNAPSHOT}")

        # Check export history count
        if len(self.export_history) > MAX_EXPORT_HISTORY_RECORDS:
            violations.append(f"Export history count {len(self.export_history)} exceeds limit {MAX_EXPORT_HISTORY_RECORDS}")

        return violations

    def is_quota_compliant(self) -> bool:
        """Check if snapshot complies with all quotas."""
        return len(self.check_quota_violations()) == 0
    
    def truncate_for_storage(self) -> 'UserSnapshot':
        """Create truncated version that fits storage limits with intelligent prioritization."""
        if self.is_quota_compliant():
            return self

        violations = self.check_quota_violations()
        logging.warning(f"Truncating snapshot due to quota violations: {violations}")

        # Start with current data
        truncated_data = {
            'version': self.version,
            'created_at': self.created_at,
            'last_modified': datetime.now(timezone.utc).isoformat(),
            'input_text': self.input_text,
            'cards': self.cards.copy(),
            'options': self.options,
            'layout': self.layout,
            'typography': self.typography,
            'visual': self.visual,
            'preview': self.preview,
            'export_history': self.export_history.copy(),
            'total_cards_generated': self.total_cards_generated,
            'session_id': self.session_id
        }

        # Apply intelligent truncation strategies

        # 1. Truncate input text if too long
        if len(truncated_data['input_text']) > MAX_INPUT_TEXT_LENGTH:
            truncated_data['input_text'] = truncated_data['input_text'][:MAX_INPUT_TEXT_LENGTH]
            logging.info("Truncated input text to fit limits")

        # 2. Limit cards count (keep most recent if they have timestamps)
        if len(truncated_data['cards']) > MAX_CARDS_PER_SNAPSHOT:
            # Try to sort by creation time if available
            try:
                sorted_cards = sorted(truncated_data['cards'],
                                    key=lambda c: c.get('created_at', ''), reverse=True)
                truncated_data['cards'] = sorted_cards[:MAX_CARDS_PER_SNAPSHOT]
            except Exception:
                # Fallback to simple truncation
                truncated_data['cards'] = truncated_data['cards'][:MAX_CARDS_PER_SNAPSHOT]
            logging.info(f"Truncated cards to {MAX_CARDS_PER_SNAPSHOT}")

        # 3. Limit export history (keep most recent)
        if len(truncated_data['export_history']) > MAX_EXPORT_HISTORY_RECORDS:
            try:
                sorted_history = sorted(truncated_data['export_history'],
                                      key=lambda r: r.get('timestamp', ''), reverse=True)
                truncated_data['export_history'] = sorted_history[:MAX_EXPORT_HISTORY_RECORDS]
            except Exception:
                truncated_data['export_history'] = truncated_data['export_history'][:MAX_EXPORT_HISTORY_RECORDS]
            logging.info(f"Truncated export history to {MAX_EXPORT_HISTORY_RECORDS}")

        # 4. If still too large, apply more aggressive truncation
        temp_snapshot = UserSnapshot(**truncated_data)
        if temp_snapshot.is_too_large():
            # More aggressive input text truncation
            truncated_data['input_text'] = truncated_data['input_text'][:MAX_INPUT_TEXT_LENGTH // 2]
            # Reduce cards further
            truncated_data['cards'] = truncated_data['cards'][:min(100, len(truncated_data['cards']))]
            # Reduce export history further
            truncated_data['export_history'] = truncated_data['export_history'][:10]
            logging.warning("Applied aggressive truncation to meet size limits")

        return UserSnapshot(**truncated_data)


def migrate_snapshot(data: Dict[str, Any]) -> UserSnapshot:
    """
    Migrate snapshot data to current version with comprehensive error handling.

    Args:
        data: Raw snapshot data dictionary

    Returns:
        UserSnapshot with current version

    Raises:
        ValueError: If migration fails after retries
    """
    original_data = data.copy() if ENABLE_MIGRATION_BACKUP else None
    version = data.get('version', 1)

    if version == CURRENT_SNAPSHOT_VERSION:
        # Already current version, but still apply field migration
        field_migration_result = migrate_snapshot_data(data)
        if field_migration_result.migration_applied:
            logging.info(f"Applied field migration to current version snapshot: {list(field_migration_result.migrated_fields.keys())}")
            for warning in field_migration_result.warnings:
                logging.warning(f"Field migration warning: {warning}")
            for error in field_migration_result.errors:
                logging.error(f"Field migration error: {error}")
        return UserSnapshot(**data)

    if version > CURRENT_SNAPSHOT_VERSION:
        logging.warning(f"Snapshot version {version} is newer than supported {CURRENT_SNAPSHOT_VERSION}")
        # Try to load anyway, might be forward compatible
        try:
            return UserSnapshot(**data)
        except Exception as e:
            logging.error(f"Failed to load newer snapshot version: {e}")
            raise ValueError(f"Unsupported snapshot version {version}")

    # Perform migration chain with retry logic
    for attempt in range(MAX_MIGRATION_RETRIES):
        try:
            migrated_data = _perform_migration_chain(data.copy(), version)
            return UserSnapshot(**migrated_data)
        except Exception as e:
            logging.warning(f"Migration attempt {attempt + 1} failed: {e}")
            if attempt == MAX_MIGRATION_RETRIES - 1:
                # Final attempt failed, try emergency fallback
                if original_data and ENABLE_MIGRATION_BACKUP:
                    logging.error("All migration attempts failed, attempting emergency recovery")
                    return _emergency_migration_fallback(original_data)
                else:
                    raise ValueError(f"Migration failed after {MAX_MIGRATION_RETRIES} attempts: {e}")

    # Should never reach here
    raise ValueError("Migration failed unexpectedly")


def _perform_migration_chain(data: Dict[str, Any], from_version: int) -> Dict[str, Any]:
    """
    Perform the complete migration chain from given version to current.

    Args:
        data: Snapshot data to migrate
        from_version: Starting version

    Returns:
        Migrated data at current version
    """
    current_data = data.copy()
    version = from_version

    # Migration chain - each step validates and transforms data
    if version == 1:
        current_data = _migrate_v1_to_v2(current_data)
        version = 2
        logging.info("Migrated snapshot from v1 to v2")

    if version == 2:
        current_data = _migrate_v2_to_v3(current_data)
        version = 3
        logging.info("Migrated snapshot from v2 to v3")

    # Add future migrations here
    # if version == 3:
    #     current_data = _migrate_v3_to_v4(current_data)
    #     version = 4

    # Apply field migration to ensure canonical field names
    field_migration_result = migrate_snapshot_data(current_data)
    if field_migration_result.migration_applied:
        logging.info(f"Applied field migration: {list(field_migration_result.migrated_fields.keys())}")
        for warning in field_migration_result.warnings:
            logging.warning(f"Field migration warning: {warning}")
        for error in field_migration_result.errors:
            logging.error(f"Field migration error: {error}")

    # Validate final version
    if version != CURRENT_SNAPSHOT_VERSION:
        raise ValueError(f"Migration chain incomplete: reached v{version}, expected v{CURRENT_SNAPSHOT_VERSION}")

    return current_data


def _emergency_migration_fallback(data: Dict[str, Any]) -> UserSnapshot:
    """
    Emergency fallback migration that creates a minimal valid snapshot.
    Used when normal migration fails to prevent data loss.
    """
    logging.warning("Using emergency migration fallback - some data may be lost")

    # Extract only the most critical data
    safe_data = {
        'version': CURRENT_SNAPSHOT_VERSION,
        'created_at': data.get('created_at', datetime.now(timezone.utc).isoformat()),
        'last_modified': datetime.now(timezone.utc).isoformat(),
        'input_text': str(data.get('input_text', ''))[:MAX_INPUT_TEXT_LENGTH],
        'cards': [],  # Start with empty cards to avoid corruption
        'options': {},
        'layout': {},
        'typography': {},
        'visual': {},
        'preview': {},
        'export_history': [],
        'total_cards_generated': 0,
        'session_id': str(uuid.uuid4())
    }

    # Try to preserve input text and basic options
    try:
        if 'cards' in data and isinstance(data['cards'], list):
            # Limit cards to prevent memory issues
            safe_cards = data['cards'][:MAX_CARDS_PER_SNAPSHOT]
            safe_data['cards'] = safe_cards
    except Exception:
        pass  # Keep empty cards

    try:
        if 'total_cards_generated' in data:
            safe_data['total_cards_generated'] = int(data['total_cards_generated'])
    except Exception:
        pass  # Keep default 0

    return UserSnapshot(**safe_data)


def _migrate_v1_to_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from version 1 to version 2."""
    # V1 -> V2 changes:
    # - Added session_id field
    # - Improved export_history structure
    # - Better card format
    
    migrated = data.copy()
    migrated['version'] = 2
    
    # Add session_id if missing
    if 'session_id' not in migrated:
        migrated['session_id'] = str(uuid.uuid4())
    
    # Ensure all required fields exist with defaults
    defaults = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'last_modified': datetime.now(timezone.utc).isoformat(),
        'input_text': '',
        'cards': [],
        'options': {},
        'layout': {},
        'typography': {},
        'visual': {},
        'preview': {},
        'export_history': [],
        'total_cards_generated': 0,
    }
    
    for key, default_value in defaults.items():
        if key not in migrated:
            migrated[key] = default_value
    
    # Migrate export history format if needed
    if 'export_history' in migrated:
        new_history = []
        for record in migrated['export_history']:
            if isinstance(record, dict):
                # Ensure required fields
                if 'timestamp' not in record:
                    record['timestamp'] = datetime.now(timezone.utc).isoformat()
                new_history.append(record)
        migrated['export_history'] = new_history
    
    return migrated


def _migrate_v2_to_v3(data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate from version 2 to version 3."""
    # V2 -> V3 changes:
    # - Enhanced card format with stable IDs
    # - Improved state management structure
    # - Better error handling and validation
    # - Enhanced export history with more metadata

    migrated = data.copy()
    migrated['version'] = 3

    # Update timestamp
    migrated['last_modified'] = datetime.now(timezone.utc).isoformat()

    # Enhance cards with stable IDs if using new card system
    if 'cards' in migrated and isinstance(migrated['cards'], list):
        enhanced_cards = []
        for i, card in enumerate(migrated['cards']):
            if isinstance(card, dict):
                # Ensure card has required fields
                enhanced_card = {
                    'id': card.get('id', str(uuid.uuid4())),
                    'hanzi': card.get('hanzi', ''),
                    'pinyin': card.get('pinyin', ''),
                    'english': card.get('english', ''),
                    'version': card.get('version', 1),
                    'created_at': card.get('created_at', datetime.now(timezone.utc).isoformat())
                }
                enhanced_cards.append(enhanced_card)
        migrated['cards'] = enhanced_cards

    # Enhance export history with additional metadata
    if 'export_history' in migrated and isinstance(migrated['export_history'], list):
        enhanced_history = []
        for record in migrated['export_history']:
            if isinstance(record, dict):
                enhanced_record = record.copy()
                # Add filename if missing
                if 'filename' not in enhanced_record:
                    format_type = enhanced_record.get('format_type', 'unknown')
                    card_count = enhanced_record.get('card_count', 0)
                    timestamp = enhanced_record.get('timestamp', '')
                    enhanced_record['filename'] = f"cards_{card_count}_{timestamp[:10]}.{format_type}"
                enhanced_history.append(enhanced_record)
        migrated['export_history'] = enhanced_history

    # Add new state management fields
    if 'state_metadata' not in migrated:
        migrated['state_metadata'] = {
            'last_digest': None,
            'cache_version': 1,
            'feature_flags_snapshot': {}
        }

    # Validate and clean up data
    migrated = _validate_and_clean_v3_data(migrated)

    return migrated


def _validate_and_clean_v3_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clean v3 snapshot data."""
    # Ensure input text is within limits
    if 'input_text' in data and len(data['input_text']) > MAX_INPUT_TEXT_LENGTH:
        data['input_text'] = data['input_text'][:MAX_INPUT_TEXT_LENGTH]
        logging.warning("Input text truncated during v3 migration")

    # Ensure cards count is within limits
    if 'cards' in data and isinstance(data['cards'], list):
        if len(data['cards']) > MAX_CARDS_PER_SNAPSHOT:
            data['cards'] = data['cards'][:MAX_CARDS_PER_SNAPSHOT]
            logging.warning(f"Cards truncated to {MAX_CARDS_PER_SNAPSHOT} during v3 migration")

    # Ensure export history is within limits
    if 'export_history' in data and isinstance(data['export_history'], list):
        if len(data['export_history']) > MAX_EXPORT_HISTORY_RECORDS:
            # Keep most recent records
            data['export_history'].sort(key=lambda r: r.get('timestamp', ''), reverse=True)
            data['export_history'] = data['export_history'][:MAX_EXPORT_HISTORY_RECORDS]
            logging.warning("Export history truncated during v3 migration")

    return data


def validate_snapshot_data(data: Any) -> bool:
    """
    Validate snapshot data structure.
    
    Args:
        data: Data to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(data, dict):
        return False
    
    # Check required fields
    required_fields = ['version', 'input_text', 'cards']
    for field in required_fields:
        if field not in data:
            return False
    
    # Check version is valid
    version = data.get('version')
    if not isinstance(version, int) or version < 1:
        return False
    
    # Check input_text is string
    if not isinstance(data.get('input_text'), str):
        return False
    
    # Check cards is list
    if not isinstance(data.get('cards'), list):
        return False
    
    return True


def coerce_snapshot_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce snapshot data to correct types.
    
    Args:
        data: Raw data dictionary
        
    Returns:
        Coerced data dictionary
    """
    coerced = data.copy()
    
    # Coerce version to int
    if 'version' in coerced:
        try:
            coerced['version'] = int(coerced['version'])
        except (ValueError, TypeError):
            coerced['version'] = 1
    
    # Coerce input_text to string
    if 'input_text' in coerced:
        coerced['input_text'] = str(coerced['input_text'])
    
    # Coerce cards to list
    if 'cards' in coerced:
        if not isinstance(coerced['cards'], list):
            coerced['cards'] = []
    
    # Coerce numeric fields
    numeric_fields = ['total_cards_generated']
    for field in numeric_fields:
        if field in coerced:
            try:
                coerced[field] = int(coerced[field])
            except (ValueError, TypeError):
                coerced[field] = 0
    
    return coerced


def is_persistence_enabled() -> bool:
    """Check if persistence is enabled."""
    # Check environment variable kill-switch
    import os
    if os.getenv('DISABLE_PERSISTENCE', '').lower() in ('true', '1', 'yes'):
        return False
    
    # Check feature flag
    return get_feature_flag('persistence', True)


def create_snapshot_from_session(session_state) -> Optional[UserSnapshot]:
    """
    Create snapshot from session state if persistence is enabled.
    
    Args:
        session_state: Streamlit session state
        
    Returns:
        UserSnapshot or None if persistence disabled
    """
    if not is_persistence_enabled():
        return None
    
    try:
        snapshot = UserSnapshot.from_session_state(session_state)
        
        # Check size limits
        if snapshot.is_too_large():
            logging.warning("Snapshot too large, truncating for storage")
            snapshot = snapshot.truncate_for_storage()
        
        return snapshot
    except Exception as e:
        logging.error(f"Failed to create snapshot: {e}")
        return None


def load_snapshot_from_data(data: Any) -> Optional[UserSnapshot]:
    """
    Load snapshot from raw data with validation and migration.
    
    Args:
        data: Raw snapshot data
        
    Returns:
        UserSnapshot or None if invalid
    """
    if not is_persistence_enabled():
        return None
    
    try:
        # Validate basic structure
        if not validate_snapshot_data(data):
            logging.warning("Invalid snapshot data structure")
            return None
        
        # Coerce types
        coerced_data = coerce_snapshot_data(data)
        
        # Migrate to current version
        snapshot = migrate_snapshot(coerced_data)
        
        return snapshot
    except Exception as e:
        logging.error(f"Failed to load snapshot: {e}")
        return None
