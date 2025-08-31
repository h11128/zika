"""
Data Migration Strategy and Implementation.
Handles version detection, automatic migration of old formats, validation, rollback capability, and user notification.
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
import copy

from core.feature_flags import get_feature_flag
from services.telemetry import record_error_event, record_performance_event


class MigrationStatus(Enum):
    """Migration operation status."""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"
    ROLLBACK = "rollback"


class DataFormat(Enum):
    """Supported data formats for migration."""
    LEGACY_V1 = "legacy_v1"        # Original format without versioning
    SNAPSHOT_V1 = "snapshot_v1"    # First versioned snapshot format
    SNAPSHOT_V2 = "snapshot_v2"    # Enhanced snapshot with metadata
    SNAPSHOT_V3 = "snapshot_v3"    # Current format with full features
    UNKNOWN = "unknown"            # Unrecognized format


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    status: MigrationStatus
    source_version: str
    target_version: str
    migrated_data: Optional[Dict[str, Any]] = None
    backup_data: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    data_size_before: int = 0
    data_size_after: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


@dataclass
class MigrationRule:
    """Migration rule definition."""
    from_version: str
    to_version: str
    migration_function: Callable[[Dict[str, Any]], Dict[str, Any]]
    validation_function: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""
    is_destructive: bool = False
    requires_backup: bool = True


class DataVersionDetector:
    """Detects data format versions from raw data."""
    
    def __init__(self):
        self._detection_rules = [
            self._detect_snapshot_v3,
            self._detect_snapshot_v2,
            self._detect_snapshot_v1,
            self._detect_legacy_v1,
        ]
    
    def detect_version(self, data: Dict[str, Any]) -> Tuple[DataFormat, str]:
        """
        Detect data format version.
        
        Args:
            data: Raw data dictionary
        
        Returns:
            Tuple of (DataFormat, version_string)
        """
        if not isinstance(data, dict):
            return DataFormat.UNKNOWN, "unknown"
        
        # Try each detection rule in order
        for detection_rule in self._detection_rules:
            try:
                result = detection_rule(data)
                if result:
                    return result
            except Exception as e:
                logging.warning(f"Error in version detection: {e}")
                continue
        
        return DataFormat.UNKNOWN, "unknown"
    
    def _detect_snapshot_v3(self, data: Dict[str, Any]) -> Optional[Tuple[DataFormat, str]]:
        """Detect snapshot v3 format (current)."""
        if (data.get('format_version') == '3.0.0' and
            'metadata' in data and
            'cards' in data and
            'export_history' in data and
            'created_at' in data.get('metadata', {})):
            return DataFormat.SNAPSHOT_V3, data.get('format_version', '3.0.0')
        return None
    
    def _detect_snapshot_v2(self, data: Dict[str, Any]) -> Optional[Tuple[DataFormat, str]]:
        """Detect snapshot v2 format."""
        if (data.get('format_version') == '2.0.0' and
            'metadata' in data and
            'cards' in data and
            'last_modified' in data.get('metadata', {})):
            return DataFormat.SNAPSHOT_V2, data.get('format_version', '2.0.0')
        return None
    
    def _detect_snapshot_v1(self, data: Dict[str, Any]) -> Optional[Tuple[DataFormat, str]]:
        """Detect snapshot v1 format."""
        if (data.get('format_version') == '1.0.0' and
            'cards' in data and
            isinstance(data['cards'], list)):
            return DataFormat.SNAPSHOT_V1, data.get('format_version', '1.0.0')
        return None
    
    def _detect_legacy_v1(self, data: Dict[str, Any]) -> Optional[Tuple[DataFormat, str]]:
        """Detect legacy v1 format (no versioning)."""
        if ('cards' in data and
            isinstance(data['cards'], list) and
            'format_version' not in data):
            # Empty cards list is still valid legacy format
            if not data['cards']:
                return DataFormat.LEGACY_V1, "legacy"
            # Check if cards have legacy structure
            if data['cards'] and isinstance(data['cards'][0], dict):
                card = data['cards'][0]
                if ('hanzi' in card and 'pinyin' in card and 'english' in card and
                    'id' not in card):  # Legacy cards don't have IDs
                    return DataFormat.LEGACY_V1, "legacy"
        return None


class DataMigrator:
    """Handles data migration between versions."""
    
    def __init__(self):
        self.detector = DataVersionDetector()
        self._migration_rules: List[MigrationRule] = []
        self._setup_migration_rules()
        
        # Migration statistics
        self._stats = {
            'migrations_attempted': 0,
            'migrations_successful': 0,
            'migrations_failed': 0,
            'rollbacks_performed': 0,
            'data_loss_incidents': 0
        }
    
    def _setup_migration_rules(self):
        """Setup migration rules for all supported version transitions."""
        
        # Legacy V1 -> Snapshot V1
        self._migration_rules.append(MigrationRule(
            from_version="legacy",
            to_version="1.0.0",
            migration_function=self._migrate_legacy_to_v1,
            validation_function=self._validate_snapshot_v1,
            description="Migrate legacy format to versioned snapshot v1",
            is_destructive=False,
            requires_backup=True
        ))
        
        # Snapshot V1 -> Snapshot V2
        self._migration_rules.append(MigrationRule(
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=self._migrate_v1_to_v2,
            validation_function=self._validate_snapshot_v2,
            description="Add metadata and enhanced structure",
            is_destructive=False,
            requires_backup=True
        ))
        
        # Snapshot V2 -> Snapshot V3
        self._migration_rules.append(MigrationRule(
            from_version="2.0.0",
            to_version="3.0.0",
            migration_function=self._migrate_v2_to_v3,
            validation_function=self._validate_snapshot_v3,
            description="Add export history and full feature support",
            is_destructive=False,
            requires_backup=True
        ))
    
    def migrate_data(self, data: Dict[str, Any], target_version: str = "3.0.0") -> MigrationResult:
        """
        Migrate data to target version.
        
        Args:
            data: Source data to migrate
            target_version: Target version to migrate to
        
        Returns:
            MigrationResult with migration details
        """
        start_time = time.time()
        self._stats['migrations_attempted'] += 1
        
        # Detect current version
        data_format, current_version = self.detector.detect_version(data)
        
        if data_format == DataFormat.UNKNOWN:
            self._stats['migrations_failed'] += 1
            return MigrationResult(
                status=MigrationStatus.FAILED,
                source_version="unknown",
                target_version=target_version,
                errors=["Unable to detect data format version"],
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Check if migration is needed
        if current_version == target_version:
            return MigrationResult(
                status=MigrationStatus.SKIPPED,
                source_version=current_version,
                target_version=target_version,
                migrated_data=copy.deepcopy(data),
                duration_ms=(time.time() - start_time) * 1000
            )
        
        # Create backup
        backup_data = copy.deepcopy(data)
        migrated_data = copy.deepcopy(data)
        warnings = []
        errors = []
        
        try:
            # Find migration path
            migration_path = self._find_migration_path(current_version, target_version)
            
            if not migration_path:
                self._stats['migrations_failed'] += 1
                return MigrationResult(
                    status=MigrationStatus.FAILED,
                    source_version=current_version,
                    target_version=target_version,
                    backup_data=backup_data,
                    errors=[f"No migration path found from {current_version} to {target_version}"],
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            # Execute migration steps
            for rule in migration_path:
                try:
                    migrated_data = rule.migration_function(migrated_data)
                    
                    # Validate if validation function exists
                    if rule.validation_function and not rule.validation_function(migrated_data):
                        raise ValueError(f"Validation failed after migration step: {rule.description}")
                    
                except Exception as e:
                    error_msg = f"Migration step failed ({rule.from_version} -> {rule.to_version}): {e}"
                    errors.append(error_msg)
                    
                    # Record error event
                    record_error_event(
                        error_type="MigrationError",
                        error_message=error_msg,
                        metadata={
                            'migration_rule': rule.description,
                            'from_version': rule.from_version,
                            'to_version': rule.to_version
                        }
                    )
                    
                    self._stats['migrations_failed'] += 1
                    return MigrationResult(
                        status=MigrationStatus.FAILED,
                        source_version=current_version,
                        target_version=target_version,
                        backup_data=backup_data,
                        errors=errors,
                        duration_ms=(time.time() - start_time) * 1000
                    )
            
            # Final validation
            final_format, final_version = self.detector.detect_version(migrated_data)
            if final_version != target_version:
                warnings.append(f"Migration completed but version mismatch: expected {target_version}, got {final_version}")
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Record performance event
            record_performance_event(
                operation="data_migration",
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'from_version': current_version,
                    'to_version': target_version,
                    'migration_steps': len(migration_path)
                }
            )
            
            self._stats['migrations_successful'] += 1
            
            return MigrationResult(
                status=MigrationStatus.SUCCESS,
                source_version=current_version,
                target_version=target_version,
                migrated_data=migrated_data,
                backup_data=backup_data,
                warnings=warnings,
                errors=errors,
                duration_ms=duration_ms,
                data_size_before=len(json.dumps(data, default=str)),
                data_size_after=len(json.dumps(migrated_data, default=str))
            )
            
        except Exception as e:
            error_msg = f"Unexpected migration error: {e}"
            errors.append(error_msg)
            
            record_error_event(
                error_type="MigrationError",
                error_message=error_msg,
                metadata={
                    'from_version': current_version,
                    'to_version': target_version
                }
            )
            
            self._stats['migrations_failed'] += 1
            
            return MigrationResult(
                status=MigrationStatus.FAILED,
                source_version=current_version,
                target_version=target_version,
                backup_data=backup_data,
                errors=errors,
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def rollback_migration(self, backup_data: Dict[str, Any]) -> MigrationResult:
        """
        Rollback to backup data.
        
        Args:
            backup_data: Backup data to restore
        
        Returns:
            MigrationResult for rollback operation
        """
        start_time = time.time()
        self._stats['rollbacks_performed'] += 1
        
        try:
            # Validate backup data
            data_format, version = self.detector.detect_version(backup_data)
            
            if data_format == DataFormat.UNKNOWN:
                return MigrationResult(
                    status=MigrationStatus.FAILED,
                    source_version="backup",
                    target_version="rollback",
                    errors=["Backup data format is unrecognizable"],
                    duration_ms=(time.time() - start_time) * 1000
                )
            
            return MigrationResult(
                status=MigrationStatus.ROLLBACK,
                source_version="backup",
                target_version=version,
                migrated_data=copy.deepcopy(backup_data),
                duration_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return MigrationResult(
                status=MigrationStatus.FAILED,
                source_version="backup",
                target_version="rollback",
                errors=[f"Rollback failed: {e}"],
                duration_ms=(time.time() - start_time) * 1000
            )
    
    def _find_migration_path(self, from_version: str, to_version: str) -> Optional[List[MigrationRule]]:
        """Find migration path between versions."""
        # Simple linear path for now - could be enhanced with graph traversal
        path = []
        current_version = from_version
        
        while current_version != to_version:
            # Find next migration step
            next_rule = None
            for rule in self._migration_rules:
                if rule.from_version == current_version:
                    next_rule = rule
                    break
            
            if not next_rule:
                return None  # No path found
            
            path.append(next_rule)
            current_version = next_rule.to_version
            
            # Prevent infinite loops
            if len(path) > 10:
                return None
        
        return path
    
    def _migrate_legacy_to_v1(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate legacy format to snapshot v1."""
        migrated = {
            'format_version': '1.0.0',
            'cards': []
        }

        # Migrate cards
        for card in data.get('cards', []):
            # Handle corrupted cards gracefully
            if not isinstance(card, dict):
                card = {}

            migrated_card = {
                'hanzi': card.get('hanzi') or '',
                'pinyin': card.get('pinyin') or '',
                'english': card.get('english') or ''
            }
            migrated['cards'].append(migrated_card)

        return migrated
    
    def _migrate_v1_to_v2(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate snapshot v1 to v2."""
        migrated = {
            'format_version': '2.0.0',
            'metadata': {
                'created_at': datetime.now(timezone.utc).isoformat(),
                'last_modified': datetime.now(timezone.utc).isoformat(),
                'migration_source': '1.0.0'
            },
            'cards': []
        }

        # Migrate cards with corruption handling
        for card in data.get('cards', []):
            if not isinstance(card, dict):
                card = {}

            migrated_card = {
                'hanzi': card.get('hanzi') or '',
                'pinyin': card.get('pinyin') or '',
                'english': card.get('english') or ''
            }
            migrated['cards'].append(migrated_card)

        return migrated
    
    def _migrate_v2_to_v3(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate snapshot v2 to v3."""
        migrated = {
            'format_version': '3.0.0',
            'metadata': data.get('metadata', {}),
            'cards': [],
            'export_history': []
        }

        # Update metadata
        migrated['metadata']['migration_source'] = '2.0.0'
        migrated['metadata']['last_modified'] = datetime.now(timezone.utc).isoformat()

        # Migrate cards with IDs and versions
        import uuid
        for card in data.get('cards', []):
            # Handle corrupted cards gracefully
            if not isinstance(card, dict):
                card = {}

            migrated_card = {
                'id': str(uuid.uuid4()),
                'version': 1,
                'hanzi': card.get('hanzi') or '',
                'pinyin': card.get('pinyin') or '',
                'english': card.get('english') or '',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            migrated['cards'].append(migrated_card)

        return migrated
    
    def _validate_snapshot_v1(self, data: Dict[str, Any]) -> bool:
        """Validate snapshot v1 format."""
        return (data.get('format_version') == '1.0.0' and
                'cards' in data and
                isinstance(data['cards'], list))
    
    def _validate_snapshot_v2(self, data: Dict[str, Any]) -> bool:
        """Validate snapshot v2 format."""
        return (data.get('format_version') == '2.0.0' and
                'metadata' in data and
                'cards' in data and
                isinstance(data['cards'], list))
    
    def _validate_snapshot_v3(self, data: Dict[str, Any]) -> bool:
        """Validate snapshot v3 format."""
        return (data.get('format_version') == '3.0.0' and
                'metadata' in data and
                'cards' in data and
                'export_history' in data and
                isinstance(data['cards'], list))
    
    def get_migration_stats(self) -> Dict[str, Any]:
        """Get migration statistics."""
        return dict(self._stats)


# Global migrator instance
_data_migrator: Optional[DataMigrator] = None


def get_data_migrator() -> DataMigrator:
    """Get global data migrator instance."""
    global _data_migrator
    if _data_migrator is None:
        _data_migrator = DataMigrator()
    return _data_migrator


# Convenience functions
def migrate_user_data(data: Dict[str, Any], target_version: str = "3.0.0") -> MigrationResult:
    """Migrate user data to target version."""
    return get_data_migrator().migrate_data(data, target_version)


def detect_data_version(data: Dict[str, Any]) -> Tuple[DataFormat, str]:
    """Detect data format version."""
    return get_data_migrator().detector.detect_version(data)


def rollback_to_backup(backup_data: Dict[str, Any]) -> MigrationResult:
    """Rollback to backup data."""
    return get_data_migrator().rollback_migration(backup_data)
