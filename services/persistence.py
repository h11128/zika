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
from services.card_models import Card, CardCollection


# Current snapshot version
CURRENT_SNAPSHOT_VERSION = 2

# Storage limits
MAX_INPUT_TEXT_LENGTH = 10000  # 10K characters
MAX_SNAPSHOT_SIZE_BYTES = 1024 * 1024  # 1MB
MAX_EXPORT_HISTORY_RECORDS = 50
EXPORT_HISTORY_RETENTION_DAYS = 30


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
                'gap': getattr(session_state, 'gap', 0.5),
                'margin': getattr(session_state, 'margin', 1.0),
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
            total_cards_generated=getattr(session_state, 'total_cards_generated', 0)
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
    
    def truncate_for_storage(self) -> 'UserSnapshot':
        """Create truncated version that fits storage limits."""
        if not self.is_too_large():
            return self
        
        # Create copy with truncated data
        truncated = UserSnapshot(
            version=self.version,
            created_at=self.created_at,
            last_modified=datetime.now(timezone.utc).isoformat(),
            input_text=self.input_text[:MAX_INPUT_TEXT_LENGTH // 2],  # Aggressive truncation
            cards=self.cards[:100],  # Limit cards
            options=self.options,
            layout=self.layout,
            typography=self.typography,
            visual=self.visual,
            preview=self.preview,
            export_history=self.export_history[:10],  # Limit history
            total_cards_generated=self.total_cards_generated,
            session_id=self.session_id
        )
        
        return truncated


def migrate_snapshot(data: Dict[str, Any]) -> UserSnapshot:
    """
    Migrate snapshot data to current version.
    
    Args:
        data: Raw snapshot data dictionary
        
    Returns:
        UserSnapshot with current version
    """
    version = data.get('version', 1)
    
    if version == CURRENT_SNAPSHOT_VERSION:
        # Already current version
        return UserSnapshot(**data)
    
    # Migration chain
    if version == 1:
        data = _migrate_v1_to_v2(data)
        version = 2
    
    # Add future migrations here
    # if version == 2:
    #     data = _migrate_v2_to_v3(data)
    #     version = 3
    
    return UserSnapshot(**data)


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
