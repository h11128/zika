"""
Unit tests for services/migration.py
Tests data migration, version detection, validation, and rollback functionality.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from services.migration import (
    MigrationStatus, DataFormat, MigrationResult, MigrationRule,
    DataVersionDetector, DataMigrator, get_data_migrator,
    migrate_user_data, detect_data_version, rollback_to_backup
)


class TestDataVersionDetector:
    """Test data version detection functionality."""
    
    def test_detector_creation(self):
        """Test detector creation."""
        detector = DataVersionDetector()
        assert len(detector._detection_rules) > 0
    
    def test_detect_legacy_v1_format(self):
        """Test detection of legacy v1 format."""
        detector = DataVersionDetector()
        legacy_data = {
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
                {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'}
            ]
        }
        
        data_format, version = detector.detect_version(legacy_data)
        
        assert data_format == DataFormat.LEGACY_V1
        assert version == "legacy"
    
    def test_detect_snapshot_v1_format(self):
        """Test detection of snapshot v1 format."""
        detector = DataVersionDetector()
        v1_data = {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        data_format, version = detector.detect_version(v1_data)
        
        assert data_format == DataFormat.SNAPSHOT_V1
        assert version == "1.0.0"
    
    def test_detect_snapshot_v2_format(self):
        """Test detection of snapshot v2 format."""
        detector = DataVersionDetector()
        v2_data = {
            'format_version': '2.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00Z',
                'last_modified': '2024-01-15T10:30:00Z'
            },
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        data_format, version = detector.detect_version(v2_data)
        
        assert data_format == DataFormat.SNAPSHOT_V2
        assert version == "2.0.0"
    
    def test_detect_snapshot_v3_format(self):
        """Test detection of snapshot v3 format."""
        detector = DataVersionDetector()
        v3_data = {
            'format_version': '3.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00Z',
                'last_modified': '2024-01-15T10:30:00Z'
            },
            'cards': [
                {
                    'id': str(uuid.uuid4()),
                    'version': 1,
                    'hanzi': '你好',
                    'pinyin': 'nǐ hǎo',
                    'english': 'hello',
                    'created_at': '2024-01-15T10:30:00Z'
                }
            ],
            'export_history': []
        }
        
        data_format, version = detector.detect_version(v3_data)
        
        assert data_format == DataFormat.SNAPSHOT_V3
        assert version == "3.0.0"
    
    def test_detect_unknown_format(self):
        """Test detection of unknown format."""
        detector = DataVersionDetector()
        unknown_data = {
            'some_field': 'some_value',
            'other_field': 123
        }
        
        data_format, version = detector.detect_version(unknown_data)
        
        assert data_format == DataFormat.UNKNOWN
        assert version == "unknown"
    
    def test_detect_invalid_input(self):
        """Test detection with invalid input."""
        detector = DataVersionDetector()
        
        # Test with non-dict input
        data_format, version = detector.detect_version("invalid")
        assert data_format == DataFormat.UNKNOWN
        assert version == "unknown"
        
        # Test with None input
        data_format, version = detector.detect_version(None)
        assert data_format == DataFormat.UNKNOWN
        assert version == "unknown"


class TestMigrationResult:
    """Test migration result functionality."""
    
    def test_migration_result_creation(self):
        """Test migration result creation."""
        result = MigrationResult(
            status=MigrationStatus.SUCCESS,
            source_version="1.0.0",
            target_version="2.0.0",
            duration_ms=150.5
        )
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "2.0.0"
        assert result.duration_ms == 150.5
        assert len(result.warnings) == 0
        assert len(result.errors) == 0
    
    def test_migration_result_to_dict(self):
        """Test migration result serialization."""
        result = MigrationResult(
            status=MigrationStatus.SUCCESS,
            source_version="1.0.0",
            target_version="2.0.0",
            warnings=["Minor issue"],
            errors=[]
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict['status'] == MigrationStatus.SUCCESS
        assert result_dict['source_version'] == "1.0.0"
        assert result_dict['target_version'] == "2.0.0"
        assert result_dict['warnings'] == ["Minor issue"]


class TestDataMigrator:
    """Test data migrator functionality."""
    
    def test_migrator_creation(self):
        """Test migrator creation."""
        migrator = DataMigrator()
        assert migrator.detector is not None
        assert len(migrator._migration_rules) > 0
        assert isinstance(migrator._stats, dict)
    
    def test_migrate_legacy_to_v1(self):
        """Test migration from legacy to v1."""
        migrator = DataMigrator()
        legacy_data = {
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
                {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'}
            ]
        }
        
        result = migrator.migrate_data(legacy_data, "1.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "1.0.0"
        assert result.migrated_data is not None
        assert result.migrated_data['format_version'] == "1.0.0"
        assert len(result.migrated_data['cards']) == 2
        assert result.backup_data is not None
    
    def test_migrate_v1_to_v2(self):
        """Test migration from v1 to v2."""
        migrator = DataMigrator()
        v1_data = {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        result = migrator.migrate_data(v1_data, "2.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "2.0.0"
        assert result.migrated_data['format_version'] == "2.0.0"
        assert 'metadata' in result.migrated_data
        assert 'created_at' in result.migrated_data['metadata']
        assert 'last_modified' in result.migrated_data['metadata']
    
    def test_migrate_v2_to_v3(self):
        """Test migration from v2 to v3."""
        migrator = DataMigrator()
        v2_data = {
            'format_version': '2.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00Z',
                'last_modified': '2024-01-15T10:30:00Z'
            },
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        result = migrator.migrate_data(v2_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "2.0.0"
        assert result.target_version == "3.0.0"
        assert result.migrated_data['format_version'] == "3.0.0"
        assert 'export_history' in result.migrated_data
        
        # Check that cards now have IDs and versions
        cards = result.migrated_data['cards']
        assert len(cards) == 1
        assert 'id' in cards[0]
        assert 'version' in cards[0]
        assert 'created_at' in cards[0]
    
    def test_migrate_legacy_to_v3_multi_step(self):
        """Test multi-step migration from legacy to v3."""
        migrator = DataMigrator()
        legacy_data = {
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        result = migrator.migrate_data(legacy_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "3.0.0"
        assert result.migrated_data['format_version'] == "3.0.0"
        
        # Verify all v3 features are present
        assert 'metadata' in result.migrated_data
        assert 'export_history' in result.migrated_data
        assert 'id' in result.migrated_data['cards'][0]
        assert 'version' in result.migrated_data['cards'][0]
    
    def test_migrate_no_migration_needed(self):
        """Test migration when no migration is needed."""
        migrator = DataMigrator()
        v3_data = {
            'format_version': '3.0.0',
            'metadata': {'created_at': '2024-01-15T10:30:00Z'},
            'cards': [],
            'export_history': []
        }
        
        result = migrator.migrate_data(v3_data, "3.0.0")
        
        assert result.status == MigrationStatus.SKIPPED
        assert result.source_version == "3.0.0"
        assert result.target_version == "3.0.0"
        assert result.migrated_data == v3_data
    
    def test_migrate_unknown_format(self):
        """Test migration with unknown format."""
        migrator = DataMigrator()
        unknown_data = {'unknown_field': 'value'}
        
        result = migrator.migrate_data(unknown_data, "3.0.0")
        
        assert result.status == MigrationStatus.FAILED
        assert result.source_version == "unknown"
        assert len(result.errors) > 0
        assert "Unable to detect data format version" in result.errors[0]
    
    def test_migrate_invalid_target_version(self):
        """Test migration to invalid target version."""
        migrator = DataMigrator()
        v1_data = {
            'format_version': '1.0.0',
            'cards': []
        }
        
        result = migrator.migrate_data(v1_data, "99.0.0")
        
        assert result.status == MigrationStatus.FAILED
        assert "No migration path found" in result.errors[0]
    
    def test_rollback_migration(self):
        """Test migration rollback."""
        migrator = DataMigrator()
        backup_data = {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}
            ]
        }
        
        result = migrator.rollback_migration(backup_data)
        
        assert result.status == MigrationStatus.ROLLBACK
        assert result.source_version == "backup"
        assert result.target_version == "1.0.0"
        assert result.migrated_data == backup_data
    
    def test_rollback_invalid_backup(self):
        """Test rollback with invalid backup data."""
        migrator = DataMigrator()
        invalid_backup = {'invalid': 'data'}
        
        result = migrator.rollback_migration(invalid_backup)
        
        assert result.status == MigrationStatus.FAILED
        assert "Backup data format is unrecognizable" in result.errors[0]
    
    def test_migration_statistics(self):
        """Test migration statistics tracking."""
        migrator = DataMigrator()
        initial_stats = migrator.get_migration_stats()
        
        # Perform a successful migration
        legacy_data = {'cards': [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]}
        migrator.migrate_data(legacy_data, "1.0.0")
        
        # Perform a failed migration
        invalid_data = {'invalid': 'data'}
        migrator.migrate_data(invalid_data, "1.0.0")
        
        # Perform a rollback
        backup_data = {'format_version': '1.0.0', 'cards': []}
        migrator.rollback_migration(backup_data)
        
        final_stats = migrator.get_migration_stats()
        
        assert final_stats['migrations_attempted'] == initial_stats['migrations_attempted'] + 2
        assert final_stats['migrations_successful'] == initial_stats['migrations_successful'] + 1
        assert final_stats['migrations_failed'] == initial_stats['migrations_failed'] + 1
        assert final_stats['rollbacks_performed'] == initial_stats['rollbacks_performed'] + 1


class TestMigrationValidation:
    """Test migration validation functions."""
    
    def test_validate_snapshot_v1(self):
        """Test v1 snapshot validation."""
        migrator = DataMigrator()
        
        valid_v1 = {
            'format_version': '1.0.0',
            'cards': []
        }
        
        invalid_v1 = {
            'format_version': '1.0.0'
            # Missing cards field
        }
        
        assert migrator._validate_snapshot_v1(valid_v1) is True
        assert migrator._validate_snapshot_v1(invalid_v1) is False
    
    def test_validate_snapshot_v2(self):
        """Test v2 snapshot validation."""
        migrator = DataMigrator()
        
        valid_v2 = {
            'format_version': '2.0.0',
            'metadata': {'created_at': '2024-01-15T10:30:00Z'},
            'cards': []
        }
        
        invalid_v2 = {
            'format_version': '2.0.0',
            'cards': []
            # Missing metadata field
        }
        
        assert migrator._validate_snapshot_v2(valid_v2) is True
        assert migrator._validate_snapshot_v2(invalid_v2) is False
    
    def test_validate_snapshot_v3(self):
        """Test v3 snapshot validation."""
        migrator = DataMigrator()
        
        valid_v3 = {
            'format_version': '3.0.0',
            'metadata': {'created_at': '2024-01-15T10:30:00Z'},
            'cards': [],
            'export_history': []
        }
        
        invalid_v3 = {
            'format_version': '3.0.0',
            'metadata': {'created_at': '2024-01-15T10:30:00Z'},
            'cards': []
            # Missing export_history field
        }
        
        assert migrator._validate_snapshot_v3(valid_v3) is True
        assert migrator._validate_snapshot_v3(invalid_v3) is False


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    @patch('services.migration.get_data_migrator')
    def test_migrate_user_data_function(self, mock_get_migrator):
        """Test migrate user data convenience function."""
        mock_migrator = MagicMock()
        mock_result = MigrationResult(MigrationStatus.SUCCESS, "1.0.0", "3.0.0")
        mock_migrator.migrate_data.return_value = mock_result
        mock_get_migrator.return_value = mock_migrator
        
        data = {'format_version': '1.0.0', 'cards': []}
        result = migrate_user_data(data, "3.0.0")
        
        assert result == mock_result
        mock_migrator.migrate_data.assert_called_once_with(data, "3.0.0")
    
    @patch('services.migration.get_data_migrator')
    def test_detect_data_version_function(self, mock_get_migrator):
        """Test detect data version convenience function."""
        mock_migrator = MagicMock()
        mock_migrator.detector.detect_version.return_value = (DataFormat.SNAPSHOT_V1, "1.0.0")
        mock_get_migrator.return_value = mock_migrator
        
        data = {'format_version': '1.0.0', 'cards': []}
        data_format, version = detect_data_version(data)
        
        assert data_format == DataFormat.SNAPSHOT_V1
        assert version == "1.0.0"
        mock_migrator.detector.detect_version.assert_called_once_with(data)
    
    @patch('services.migration.get_data_migrator')
    def test_rollback_to_backup_function(self, mock_get_migrator):
        """Test rollback to backup convenience function."""
        mock_migrator = MagicMock()
        mock_result = MigrationResult(MigrationStatus.ROLLBACK, "backup", "1.0.0")
        mock_migrator.rollback_migration.return_value = mock_result
        mock_get_migrator.return_value = mock_migrator
        
        backup_data = {'format_version': '1.0.0', 'cards': []}
        result = rollback_to_backup(backup_data)
        
        assert result == mock_result
        mock_migrator.rollback_migration.assert_called_once_with(backup_data)


class TestIntegration:
    """Test integration scenarios."""
    
    def test_full_migration_workflow(self):
        """Test complete migration workflow."""
        migrator = DataMigrator()
        
        # Start with legacy data
        legacy_data = {
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
                {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'},
                {'hanzi': '谢谢', 'pinyin': 'xiè xiè', 'english': 'thank you'}
            ]
        }
        
        # Migrate to latest version
        result = migrator.migrate_data(legacy_data, "3.0.0")
        
        # Verify successful migration
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "3.0.0"
        
        # Verify data integrity
        migrated_data = result.migrated_data
        assert migrated_data['format_version'] == "3.0.0"
        assert len(migrated_data['cards']) == 3
        
        # Verify all cards have required v3 fields
        for card in migrated_data['cards']:
            assert 'id' in card
            assert 'version' in card
            assert 'created_at' in card
            assert card['hanzi'] in ['你好', '再见', '谢谢']
        
        # Verify metadata and export history
        assert 'metadata' in migrated_data
        assert 'export_history' in migrated_data
        assert isinstance(migrated_data['export_history'], list)
        
        # Test rollback capability
        rollback_result = migrator.rollback_migration(result.backup_data)
        assert rollback_result.status == MigrationStatus.ROLLBACK
        assert rollback_result.migrated_data == legacy_data
    
    def test_migration_with_error_handling(self):
        """Test migration with error conditions."""
        migrator = DataMigrator()
        
        # Test with corrupted data
        corrupted_data = {
            'cards': "invalid_cards_format"  # Should be list, not string
        }
        
        result = migrator.migrate_data(corrupted_data, "3.0.0")

        # Should handle gracefully
        assert result.status in [MigrationStatus.FAILED, MigrationStatus.SKIPPED]
        # For unknown format, backup_data may be None, which is acceptable

        # Test statistics tracking
        stats = migrator.get_migration_stats()
        assert 'migrations_attempted' in stats
        assert 'migrations_failed' in stats


if __name__ == "__main__":
    pytest.main([__file__])
