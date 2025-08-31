"""
Automated Migration Tests for Compatibility Testing.
Tests migration scenarios with real user data patterns and rollback testing.
"""

import pytest
import json
import uuid
import tempfile
import os
from datetime import datetime, timezone
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

from services.migration import (
    DataMigrator, MigrationStatus, DataFormat,
    migrate_user_data, detect_data_version, rollback_to_backup
)


class TestAutomatedMigrationScenarios:
    """Test automated migration scenarios with real user data patterns."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    @pytest.fixture
    def real_user_data_samples(self):
        """Real user data samples for testing."""
        return {
            "empty_legacy": {
                'cards': []
            },
            "small_legacy": {
                'cards': [
                    {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
                    {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'}
                ]
            },
            "medium_legacy": {
                'cards': [
                    {'hanzi': '学习', 'pinyin': 'xué xí', 'english': 'study'},
                    {'hanzi': '工作', 'pinyin': 'gōng zuò', 'english': 'work'},
                    {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
                    {'hanzi': '家庭', 'pinyin': 'jiā tíng', 'english': 'family'},
                    {'hanzi': '学校', 'pinyin': 'xué xiào', 'english': 'school'},
                    {'hanzi': '医院', 'pinyin': 'yī yuàn', 'english': 'hospital'},
                    {'hanzi': '银行', 'pinyin': 'yín háng', 'english': 'bank'},
                    {'hanzi': '商店', 'pinyin': 'shāng diàn', 'english': 'store'},
                    {'hanzi': '餐厅', 'pinyin': 'cān tīng', 'english': 'restaurant'},
                    {'hanzi': '图书馆', 'pinyin': 'tú shū guǎn', 'english': 'library'}
                ]
            },
            "large_legacy": {
                'cards': [
                    {
                        'hanzi': f'汉字{i}',
                        'pinyin': f'hàn zì {i}',
                        'english': f'character {i}'
                    }
                    for i in range(100)
                ]
            },
            "special_chars_legacy": {
                'cards': [
                    {'hanzi': '你好世界！', 'pinyin': 'nǐ hǎo shì jiè!', 'english': 'Hello, world!'},
                    {'hanzi': '特殊字符：""''', 'pinyin': 'tè shū zì fú', 'english': 'Special chars: ""\'\''},
                    {'hanzi': '数字123', 'pinyin': 'shù zì 123', 'english': 'Numbers 123'},
                    {'hanzi': '🇨🇳中国', 'pinyin': 'zhōng guó', 'english': '🇨🇳 China'},
                    {'hanzi': '', 'pinyin': '', 'english': ''}  # Empty card
                ]
            },
            "corrupted_legacy": {
                'cards': [
                    {'hanzi': '正常卡片', 'pinyin': 'zhèng cháng kǎ piàn', 'english': 'normal card'},
                    {'hanzi': None, 'pinyin': 'null hanzi', 'english': 'null hanzi'},
                    {'pinyin': 'missing hanzi', 'english': 'missing hanzi'},
                    {'hanzi': '缺少英文', 'pinyin': 'quē shǎo yīng wén'},
                    {}  # Completely empty card
                ]
            }
        }
    
    def test_empty_data_migration(self, migrator, real_user_data_samples):
        """Test migration of empty data."""
        empty_data = real_user_data_samples["empty_legacy"]
        
        result = migrator.migrate_data(empty_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "3.0.0"
        assert len(result.migrated_data['cards']) == 0
        assert result.migrated_data['format_version'] == "3.0.0"
        assert 'metadata' in result.migrated_data
        assert 'export_history' in result.migrated_data
    
    def test_small_dataset_migration(self, migrator, real_user_data_samples):
        """Test migration of small dataset."""
        small_data = real_user_data_samples["small_legacy"]
        
        result = migrator.migrate_data(small_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 2
        
        # Verify data integrity
        migrated_cards = result.migrated_data['cards']
        original_cards = small_data['cards']
        
        for i, (original, migrated) in enumerate(zip(original_cards, migrated_cards)):
            assert migrated['hanzi'] == original['hanzi']
            assert migrated['pinyin'] == original['pinyin']
            assert migrated['english'] == original['english']
            assert 'id' in migrated
            assert 'version' in migrated
            assert 'created_at' in migrated
    
    def test_medium_dataset_migration(self, migrator, real_user_data_samples):
        """Test migration of medium dataset."""
        medium_data = real_user_data_samples["medium_legacy"]
        
        result = migrator.migrate_data(medium_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 10
        
        # Verify performance
        assert result.duration_ms < 1000  # Should complete within 1 second
        assert result.data_size_after > result.data_size_before  # V3 format is larger
    
    def test_large_dataset_migration(self, migrator, real_user_data_samples):
        """Test migration of large dataset."""
        large_data = real_user_data_samples["large_legacy"]
        
        result = migrator.migrate_data(large_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 100
        
        # Verify performance for large dataset
        assert result.duration_ms < 5000  # Should complete within 5 seconds
        
        # Verify all cards have proper structure
        for card in result.migrated_data['cards']:
            assert 'id' in card
            assert 'version' in card
            assert 'created_at' in card
            assert len(card['id']) > 0  # UUID should not be empty
    
    def test_special_characters_migration(self, migrator, real_user_data_samples):
        """Test migration with special characters and edge cases."""
        special_data = real_user_data_samples["special_chars_legacy"]
        
        result = migrator.migrate_data(special_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 5
        
        # Verify special characters are preserved
        migrated_cards = result.migrated_data['cards']
        original_cards = special_data['cards']
        
        for original, migrated in zip(original_cards, migrated_cards):
            assert migrated['hanzi'] == original['hanzi']
            assert migrated['pinyin'] == original['pinyin']
            assert migrated['english'] == original['english']
        
        # Verify emoji preservation
        emoji_card = migrated_cards[3]
        assert '🇨🇳' in emoji_card['hanzi']
        assert '🇨🇳' in emoji_card['english']
    
    def test_corrupted_data_migration(self, migrator, real_user_data_samples):
        """Test migration with corrupted/incomplete data."""
        corrupted_data = real_user_data_samples["corrupted_legacy"]
        
        result = migrator.migrate_data(corrupted_data, "3.0.0")
        
        # Should handle gracefully
        assert result.status == MigrationStatus.SUCCESS
        assert len(result.migrated_data['cards']) == 5
        
        # Verify corrupted cards are handled
        migrated_cards = result.migrated_data['cards']
        
        # First card should be normal
        assert migrated_cards[0]['hanzi'] == '正常卡片'
        
        # Other cards should have empty strings for missing fields
        for card in migrated_cards[1:]:
            assert 'hanzi' in card
            assert 'pinyin' in card
            assert 'english' in card
            # Missing fields should be empty strings, not None
            assert card['hanzi'] is not None
            assert card['pinyin'] is not None
            assert card['english'] is not None


class TestMigrationPathTesting:
    """Test all migration paths systematically."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    def test_legacy_to_v1_path(self, migrator):
        """Test legacy to v1 migration path."""
        legacy_data = {
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        result = migrator.migrate_data(legacy_data, "1.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "1.0.0"
        assert result.migrated_data['format_version'] == "1.0.0"
        assert 'cards' in result.migrated_data
        assert 'metadata' not in result.migrated_data  # V1 doesn't have metadata
    
    def test_legacy_to_v2_path(self, migrator):
        """Test legacy to v2 migration path (multi-step)."""
        legacy_data = {
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        result = migrator.migrate_data(legacy_data, "2.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "legacy"
        assert result.target_version == "2.0.0"
        assert result.migrated_data['format_version'] == "2.0.0"
        assert 'metadata' in result.migrated_data
        assert 'export_history' not in result.migrated_data  # V2 doesn't have export_history
    
    def test_v1_to_v2_path(self, migrator):
        """Test v1 to v2 migration path."""
        v1_data = {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        result = migrator.migrate_data(v1_data, "2.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "2.0.0"
        assert result.migrated_data['format_version'] == "2.0.0"
        assert 'metadata' in result.migrated_data
        assert result.migrated_data['metadata']['migration_source'] == "1.0.0"
    
    def test_v1_to_v3_path(self, migrator):
        """Test v1 to v3 migration path (multi-step)."""
        v1_data = {
            'format_version': '1.0.0',
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        result = migrator.migrate_data(v1_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "1.0.0"
        assert result.target_version == "3.0.0"
        assert result.migrated_data['format_version'] == "3.0.0"
        assert 'metadata' in result.migrated_data
        assert 'export_history' in result.migrated_data
        
        # Verify cards have IDs and versions
        for card in result.migrated_data['cards']:
            assert 'id' in card
            assert 'version' in card
    
    def test_v2_to_v3_path(self, migrator):
        """Test v2 to v3 migration path."""
        v2_data = {
            'format_version': '2.0.0',
            'metadata': {
                'created_at': '2024-01-15T10:30:00Z',
                'last_modified': '2024-01-15T10:30:00Z'
            },
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        result = migrator.migrate_data(v2_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        assert result.source_version == "2.0.0"
        assert result.target_version == "3.0.0"
        assert result.migrated_data['format_version'] == "3.0.0"
        assert result.migrated_data['metadata']['migration_source'] == "2.0.0"
        assert 'export_history' in result.migrated_data


class TestRollbackTesting:
    """Test rollback functionality comprehensively."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    def test_successful_migration_rollback(self, migrator):
        """Test rollback after successful migration."""
        original_data = {
            'cards': [
                {'hanzi': '原始数据', 'pinyin': 'yuán shǐ shù jù', 'english': 'original data'}
            ]
        }
        
        # Perform migration
        migration_result = migrator.migrate_data(original_data, "3.0.0")
        assert migration_result.status == MigrationStatus.SUCCESS
        
        # Perform rollback
        rollback_result = migrator.rollback_migration(migration_result.backup_data)
        
        assert rollback_result.status == MigrationStatus.ROLLBACK
        assert rollback_result.migrated_data == original_data
    
    def test_multi_step_migration_rollback(self, migrator):
        """Test rollback after multi-step migration."""
        legacy_data = {
            'cards': [
                {'hanzi': '多步迁移', 'pinyin': 'duō bù qiān yí', 'english': 'multi-step migration'},
                {'hanzi': '回滚测试', 'pinyin': 'huí gǔn cè shì', 'english': 'rollback test'}
            ]
        }
        
        # Perform multi-step migration (legacy -> v3)
        migration_result = migrator.migrate_data(legacy_data, "3.0.0")
        assert migration_result.status == MigrationStatus.SUCCESS
        assert migration_result.source_version == "legacy"
        assert migration_result.target_version == "3.0.0"
        
        # Perform rollback
        rollback_result = migrator.rollback_migration(migration_result.backup_data)
        
        assert rollback_result.status == MigrationStatus.ROLLBACK
        assert rollback_result.migrated_data == legacy_data
    
    def test_large_dataset_rollback(self, migrator):
        """Test rollback with large dataset."""
        large_data = {
            'cards': [
                {
                    'hanzi': f'大数据{i}',
                    'pinyin': f'dà shù jù {i}',
                    'english': f'big data {i}'
                }
                for i in range(50)
            ]
        }
        
        # Perform migration
        migration_result = migrator.migrate_data(large_data, "3.0.0")
        assert migration_result.status == MigrationStatus.SUCCESS
        
        # Perform rollback
        rollback_result = migrator.rollback_migration(migration_result.backup_data)
        
        assert rollback_result.status == MigrationStatus.ROLLBACK
        assert len(rollback_result.migrated_data['cards']) == 50
        assert rollback_result.migrated_data == large_data
    
    def test_corrupted_backup_rollback(self, migrator):
        """Test rollback with corrupted backup data."""
        corrupted_backup = {
            'invalid_structure': 'this is not valid data'
        }
        
        rollback_result = migrator.rollback_migration(corrupted_backup)
        
        assert rollback_result.status == MigrationStatus.FAILED
        assert len(rollback_result.errors) > 0
        assert "Backup data format is unrecognizable" in rollback_result.errors[0]


class TestMigrationPerformance:
    """Test migration performance characteristics."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    def test_migration_performance_benchmarks(self, migrator):
        """Test migration performance meets benchmarks."""
        test_sizes = [10, 50, 100, 200]
        
        for size in test_sizes:
            # Generate test data
            test_data = {
                'cards': [
                    {
                        'hanzi': f'性能测试{i}',
                        'pinyin': f'xìng néng cè shì {i}',
                        'english': f'performance test {i}'
                    }
                    for i in range(size)
                ]
            }
            
            # Migrate and measure performance
            result = migrator.migrate_data(test_data, "3.0.0")
            
            assert result.status == MigrationStatus.SUCCESS
            assert result.duration_ms > 0
            
            # Performance benchmarks
            if size <= 50:
                assert result.duration_ms < 1000, f"Migration too slow for {size} cards: {result.duration_ms}ms"
            elif size <= 100:
                assert result.duration_ms < 2000, f"Migration too slow for {size} cards: {result.duration_ms}ms"
            elif size <= 200:
                assert result.duration_ms < 5000, f"Migration too slow for {size} cards: {result.duration_ms}ms"
    
    def test_memory_efficiency(self, migrator):
        """Test migration memory efficiency."""
        # Large dataset with long strings
        large_data = {
            'cards': [
                {
                    'hanzi': f'内存效率测试汉字内容' * 10 + str(i),
                    'pinyin': f'nèi cún xiào lǜ cè shì hàn zì nèi róng' * 10 + str(i),
                    'english': f'memory efficiency test chinese character content' * 10 + str(i)
                }
                for i in range(50)
            ]
        }
        
        result = migrator.migrate_data(large_data, "3.0.0")
        
        assert result.status == MigrationStatus.SUCCESS
        
        # Verify data size tracking
        assert result.data_size_before > 0
        assert result.data_size_after > 0
        
        # V3 format should be larger due to additional fields
        assert result.data_size_after > result.data_size_before
        
        # But not excessively larger (should be reasonable overhead)
        size_increase_ratio = result.data_size_after / result.data_size_before
        assert size_increase_ratio < 3.0, f"Size increase too large: {size_increase_ratio}x"


class TestMigrationErrorHandling:
    """Test migration error handling and edge cases."""
    
    @pytest.fixture
    def migrator(self):
        """Create fresh migrator for each test."""
        return DataMigrator()
    
    def test_invalid_source_data(self, migrator):
        """Test migration with invalid source data."""
        invalid_data_scenarios = [
            None,
            "string_instead_of_dict",
            123,
            [],
            {'wrong_structure': 'no_cards_field'},
            {'cards': 'not_a_list'},
            {'cards': [None, 'invalid_card']},
        ]
        
        for invalid_data in invalid_data_scenarios:
            result = migrator.migrate_data(invalid_data, "3.0.0")
            
            # Should handle gracefully
            assert result.status in [MigrationStatus.FAILED, MigrationStatus.SKIPPED]
            assert isinstance(result.errors, list)
    
    def test_invalid_target_version(self, migrator):
        """Test migration to invalid target version."""
        valid_data = {
            'cards': [
                {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
            ]
        }
        
        invalid_versions = ["99.0.0", "invalid", "", None]
        
        for invalid_version in invalid_versions:
            if invalid_version is None:
                continue  # Skip None as it would cause TypeError
                
            result = migrator.migrate_data(valid_data, invalid_version)
            
            assert result.status == MigrationStatus.FAILED
            assert len(result.errors) > 0
    
    def test_migration_statistics_accuracy(self, migrator):
        """Test migration statistics are accurate."""
        initial_stats = migrator.get_migration_stats()
        
        # Perform successful migration
        valid_data = {'cards': [{'hanzi': '成功', 'pinyin': 'chéng gōng', 'english': 'success'}]}
        migrator.migrate_data(valid_data, "1.0.0")
        
        # Perform failed migration
        invalid_data = {'invalid': 'data'}
        migrator.migrate_data(invalid_data, "1.0.0")
        
        # Perform rollback
        backup_data = {'format_version': '1.0.0', 'cards': []}
        migrator.rollback_migration(backup_data)
        
        final_stats = migrator.get_migration_stats()
        
        # Verify statistics
        assert final_stats['migrations_attempted'] == initial_stats['migrations_attempted'] + 2
        assert final_stats['migrations_successful'] == initial_stats['migrations_successful'] + 1
        assert final_stats['migrations_failed'] == initial_stats['migrations_failed'] + 1
        assert final_stats['rollbacks_performed'] == initial_stats['rollbacks_performed'] + 1


if __name__ == "__main__":
    pytest.main([__file__])
