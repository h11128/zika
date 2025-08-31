"""
Migration Testing Matrix for Historical Data Formats.
Comprehensive testing of all migration paths with real-world data scenarios.
"""

import pytest
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any

from services.migration import (
    DataMigrator, MigrationStatus, DataFormat,
    migrate_user_data, detect_data_version
)


class TestMigrationMatrix:
    """Test migration matrix for all supported format combinations."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    @pytest.fixture
    def sample_legacy_data(self):
        """Sample legacy data without versioning."""
        return {
            'cards': [
                {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
                {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'},
                {'hanzi': '谢谢', 'pinyin': 'xiè xiè', 'english': 'thank you'},
                {'hanzi': '对不起', 'pinyin': 'duì bu qǐ', 'english': 'sorry'},
                {'hanzi': '请', 'pinyin': 'qǐng', 'english': 'please'}
            ]
        }
    
    @pytest.fixture
    def sample_v1_data(self):
        """Sample v1 snapshot data."""
        return {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '学习', 'pinyin': 'xué xí', 'english': 'study'},
                {'hanzi': '工作', 'pinyin': 'gōng zuò', 'english': 'work'},
                {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'}
            ]
        }
    
    @pytest.fixture
    def sample_v2_data(self):
        """Sample v2 snapshot data."""
        return {
            'format_version': '2.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00.000Z',
                'last_modified': '2024-01-15T11:45:00.000Z',
                'user_id': 'test_user_123'
            },
            'cards': [
                {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
                {'hanzi': '学校', 'pinyin': 'xué xiào', 'english': 'school'},
                {'hanzi': '医院', 'pinyin': 'yī yuàn', 'english': 'hospital'}
            ]
        }
    
    @pytest.fixture
    def sample_v3_data(self):
        """Sample v3 snapshot data."""
        return {
            'format_version': '3.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00.000Z',
                'last_modified': '2024-01-15T12:00:00.000Z',
                'user_id': 'test_user_123',
                'app_version': '1.0.0'
            },
            'cards': [
                {
                    'id': str(uuid.uuid4()),
                    'version': 1,
                    'hanzi': '电脑',
                    'pinyin': 'diàn nǎo',
                    'english': 'computer',
                    'created_at': '2024-01-15T10:30:00.000Z'
                },
                {
                    'id': str(uuid.uuid4()),
                    'version': 2,
                    'hanzi': '手机',
                    'pinyin': 'shǒu jī',
                    'english': 'mobile phone',
                    'created_at': '2024-01-15T10:35:00.000Z'
                }
            ],
            'export_history': [
                {
                    'timestamp': '2024-01-15T11:00:00.000Z',
                    'format': 'pdf',
                    'card_count': 2,
                    'filename': 'cards_20240115.pdf'
                }
            ]
        }
    
    def test_legacy_to_v1_migration(self, migrator, sample_legacy_data):
        """Test migration from legacy format to v1."""
        result = migrator.migrate_data(sample_legacy_data, "1.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "1.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "1.0.0"
        assert 'cards' in migrated
        assert len(migrated['cards']) == 5
        
        # Verify data integrity
        original_cards = sample_legacy_data['cards']
        migrated_cards = migrated['cards']
        for i, card in enumerate(migrated_cards):
            assert card['hanzi'] == original_cards[i]['hanzi']
            assert card['pinyin'] == original_cards[i]['pinyin']
            assert card['english'] == original_cards[i]['english']
    
    def test_legacy_to_v2_migration(self, migrator, sample_legacy_data):
        """Test migration from legacy format to v2."""
        result = migrator.migrate_data(sample_legacy_data, "2.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "2.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "2.0.0"
        assert 'metadata' in migrated
        assert 'cards' in migrated
        assert 'created_at' in migrated['metadata']
        assert 'last_modified' in migrated['metadata']
    
    def test_legacy_to_v3_migration(self, migrator, sample_legacy_data):
        """Test migration from legacy format to v3."""
        result = migrator.migrate_data(sample_legacy_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "3.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "3.0.0"
        assert 'metadata' in migrated
        assert 'cards' in migrated
        assert 'export_history' in migrated
        
        # Verify cards have IDs and versions
        for card in migrated['cards']:
            assert 'id' in card
            assert 'version' in card
            assert 'created_at' in card
    
    def test_v1_to_v2_migration(self, migrator, sample_v1_data):
        """Test migration from v1 to v2."""
        result = migrator.migrate_data(sample_v1_data, "2.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "2.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "2.0.0"
        assert 'metadata' in migrated
        assert migrated['metadata']['migration_source'] == "1.0.0"
    
    def test_v1_to_v3_migration(self, migrator, sample_v1_data):
        """Test migration from v1 to v3."""
        result = migrator.migrate_data(sample_v1_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "3.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "3.0.0"
        assert 'export_history' in migrated
        
        # Verify cards have been enhanced
        for card in migrated['cards']:
            assert 'id' in card
            assert 'version' in card
    
    def test_v2_to_v3_migration(self, migrator, sample_v2_data):
        """Test migration from v2 to v3."""
        result = migrator.migrate_data(sample_v2_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "2.0.0"
        assert result.target_version == "3.0.0"
        
        # Verify structure
        migrated = result.migrated_data
        assert migrated['format_version'] == "3.0.0"
        assert migrated['metadata']['migration_source'] == "2.0.0"
        assert 'export_history' in migrated
    
    def test_no_migration_needed(self, migrator, sample_v3_data):
        """Test when no migration is needed."""
        result = migrator.migrate_data(sample_v3_data, "3.0.0")
        
        assert result.status == MigrationStatus.SKIPPED
        assert result.source_version == "3.0.0"
        assert result.target_version == "3.0.0"
        assert result.migrated_data == sample_v3_data


class TestMigrationDataIntegrity:
    """Test data integrity across migrations."""
    
    def test_card_content_preservation(self):
        """Test that card content is preserved across all migrations."""
        migrator = DataMigrator()
        
        # Original data with special characters and edge cases
        original_data = {
            'cards': [
                {'hanzi': '你好世界！', 'pinyin': 'nǐ hǎo shì jiè!', 'english': 'Hello, world!'},
                {'hanzi': '中文测试', 'pinyin': 'zhōng wén cè shì', 'english': 'Chinese test'},
                {'hanzi': '特殊字符：""''', 'pinyin': 'tè shū zì fú', 'english': 'Special chars: ""\'\''},
                {'hanzi': '数字123', 'pinyin': 'shù zì 123', 'english': 'Numbers 123'},
                {'hanzi': '', 'pinyin': '', 'english': ''}  # Empty card
            ]
        }
        
        # Migrate to v3
        result = migrator.migrate_data(original_data, "3.0.0")
        assert result.status == MigrationStatus.SUCCESS
        
        # Verify all content is preserved
        migrated_cards = result.migrated_data['cards']
        original_cards = original_data['cards']
        
        assert len(migrated_cards) == len(original_cards)
        
        for i, (original, migrated) in enumerate(zip(original_cards, migrated_cards)):
            assert migrated['hanzi'] == original['hanzi'], f"Hanzi mismatch at index {i}"
            assert migrated['pinyin'] == original['pinyin'], f"Pinyin mismatch at index {i}"
            assert migrated['english'] == original['english'], f"English mismatch at index {i}"
    
    def test_large_dataset_migration(self):
        """Test migration with large dataset."""
        migrator = DataMigrator()
        
        # Generate large dataset
        large_data = {
            'cards': []
        }
        
        for i in range(1000):
            large_data['cards'].append({
                'hanzi': f'汉字{i}',
                'pinyin': f'hàn zì {i}',
                'english': f'character {i}'
            })
        
        # Migrate to v3
        result = migrator.migrate_data(large_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 1000
        
        # Verify performance metrics
        assert result.duration_ms > 0
        assert result.data_size_before > 0
        assert result.data_size_after > 0
    
    def test_unicode_handling(self):
        """Test proper Unicode handling in migrations."""
        migrator = DataMigrator()
        
        unicode_data = {
            'cards': [
                {'hanzi': '🇨🇳中国', 'pinyin': 'zhōng guó', 'english': '🇨🇳 China'},
                {'hanzi': '测试émoji😀', 'pinyin': 'cè shì', 'english': 'test emoji😀'},
                {'hanzi': 'ñiño', 'pinyin': 'special', 'english': 'special chars ñiño'},
                {'hanzi': '한국어', 'pinyin': 'korean', 'english': 'Korean text'},
                {'hanzi': 'العربية', 'pinyin': 'arabic', 'english': 'Arabic text'}
            ]
        }
        
        result = migrator.migrate_data(unicode_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        
        # Verify Unicode preservation
        migrated_cards = result.migrated_data['cards']
        for i, card in enumerate(migrated_cards):
            original_card = unicode_data['cards'][i]
            assert card['hanzi'] == original_card['hanzi']
            assert card['pinyin'] == original_card['pinyin']
            assert card['english'] == original_card['english']


class TestMigrationErrorScenarios:
    """Test migration error handling and edge cases."""
    
    def test_corrupted_data_handling(self):
        """Test handling of corrupted data."""
        migrator = DataMigrator()
        
        corrupted_scenarios = [
            {'cards': None},  # Null cards
            {'cards': 'invalid'},  # String instead of list
            {'cards': [{'invalid': 'structure'}]},  # Missing required fields
            {'format_version': '999.0.0', 'cards': []},  # Invalid version
            {},  # Empty data
            {'cards': [None, {'hanzi': 'test'}]},  # Mixed valid/invalid cards
        ]
        
        for i, corrupted_data in enumerate(corrupted_scenarios):
            result = migrator.migrate_data(corrupted_data, "3.0.0")
            
            # Should handle gracefully without crashing
            assert result.status in [MigrationStatus.FAILED, MigrationStatus.SKIPPED]
            assert isinstance(result.errors, list)
            
            # Should have meaningful error messages
            if result.status == MigrationStatus.FAILED:
                assert len(result.errors) > 0, f"No error message for scenario {i}"
    
    def test_partial_migration_rollback(self):
        """Test rollback capability for failed migrations."""
        migrator = DataMigrator()
        
        # Valid data that should migrate successfully
        valid_data = {
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        # Migrate successfully
        result = migrator.migrate_data(valid_data, "3.0.0")
        assert result.status == MigrationStatus.SUCCESS
        
        # Test rollback
        rollback_result = migrator.rollback_migration(result.backup_data)
        assert rollback_result.status == MigrationStatus.ROLLBACK
        assert rollback_result.migrated_data == valid_data
    
    def test_migration_statistics_accuracy(self):
        """Test accuracy of migration statistics."""
        migrator = DataMigrator()
        initial_stats = migrator.get_migration_stats()
        
        # Perform various migration operations
        valid_data = {'cards': [{'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}]}
        invalid_data = {'invalid': 'data'}
        backup_data = {'format_version': '1.0.0', 'cards': []}
        
        # Successful migration
        migrator.migrate_data(valid_data, "1.0.0")
        
        # Failed migration
        migrator.migrate_data(invalid_data, "1.0.0")
        
        # Rollback
        migrator.rollback_migration(backup_data)
        
        final_stats = migrator.get_migration_stats()
        
        # Verify statistics
        assert final_stats['migrations_attempted'] == initial_stats['migrations_attempted'] + 2
        assert final_stats['migrations_successful'] == initial_stats['migrations_successful'] + 1
        assert final_stats['migrations_failed'] == initial_stats['migrations_failed'] + 1
        assert final_stats['rollbacks_performed'] == initial_stats['rollbacks_performed'] + 1


class TestMigrationPerformance:
    """Test migration performance characteristics."""
    
    def test_migration_performance_benchmarks(self):
        """Test migration performance meets benchmarks."""
        migrator = DataMigrator()
        
        # Test with different data sizes
        test_sizes = [10, 100, 500]
        
        for size in test_sizes:
            # Generate test data
            test_data = {
                'cards': [
                    {
                        'hanzi': f'汉字{i}',
                        'pinyin': f'hàn zì {i}',
                        'english': f'character {i}'
                    }
                    for i in range(size)
                ]
            }
            
            # Migrate and measure performance
            result = migrator.migrate_data(test_data, "3.0.0")
            
            assert result.status == MigrationStatus.SUCCESS
            assert result.duration_ms > 0
            
            # Performance benchmarks (adjust based on requirements)
            if size <= 100:
                assert result.duration_ms < 1000, f"Migration too slow for {size} cards: {result.duration_ms}ms"
            elif size <= 500:
                assert result.duration_ms < 5000, f"Migration too slow for {size} cards: {result.duration_ms}ms"
    
    def test_memory_efficiency(self):
        """Test migration memory efficiency."""
        migrator = DataMigrator()
        
        # Large dataset
        large_data = {
            'cards': [
                {
                    'hanzi': f'汉字{i}' * 10,  # Longer strings
                    'pinyin': f'hàn zì {i}' * 10,
                    'english': f'character {i}' * 10
                }
                for i in range(100)
            ]
        }
        
        result = migrator.migrate_data(large_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        
        # Verify data size tracking
        assert result.data_size_before > 0
        assert result.data_size_after > 0
        
        # V3 format should be larger due to additional fields
        assert result.data_size_after > result.data_size_before


if __name__ == "__main__":
    pytest.main([__file__])
