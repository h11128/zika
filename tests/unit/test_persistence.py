"""
Unit tests for services/persistence.py
Tests UserSnapshot, migration functions, and storage management.
"""

import pytest
import json
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from services.persistence import (
    ExportRecord, UserSnapshot, migrate_snapshot, validate_snapshot_data,
    coerce_snapshot_data, is_persistence_enabled, create_snapshot_from_session,
    load_snapshot_from_data, CURRENT_SNAPSHOT_VERSION, MAX_INPUT_TEXT_LENGTH,
    MAX_EXPORT_HISTORY_RECORDS, EXPORT_HISTORY_RETENTION_DAYS
)


class TestExportRecord:
    """Test ExportRecord dataclass."""
    
    def test_export_record_creation(self):
        """Test basic ExportRecord creation."""
        timestamp = datetime.now(timezone.utc).isoformat()
        record = ExportRecord(
            timestamp=timestamp,
            format_type='pdf',
            card_count=10,
            filename='cards.pdf'
        )
        
        assert record.timestamp == timestamp
        assert record.format_type == 'pdf'
        assert record.card_count == 10
        assert record.filename == 'cards.pdf'
    
    def test_create_now(self):
        """Test creating record with current timestamp."""
        record = ExportRecord.create_now('pptx', 5, 'presentation.pptx')
        
        assert record.format_type == 'pptx'
        assert record.card_count == 5
        assert record.filename == 'presentation.pptx'
        
        # Check timestamp is recent
        record_time = datetime.fromisoformat(record.timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        assert (now - record_time).total_seconds() < 1
    
    def test_from_dict(self):
        """Test creating record from dictionary."""
        data = {
            'timestamp': '2023-01-01T12:00:00Z',
            'format_type': 'csv',
            'card_count': 15,
            'filename': 'data.csv'
        }
        
        record = ExportRecord.from_dict(data)
        
        assert record.timestamp == '2023-01-01T12:00:00Z'
        assert record.format_type == 'csv'
        assert record.card_count == 15
        assert record.filename == 'data.csv'
    
    def test_from_dict_missing_fields(self):
        """Test creating record from incomplete dictionary."""
        data = {'format_type': 'pdf'}
        
        record = ExportRecord.from_dict(data)
        
        assert record.format_type == 'pdf'
        assert record.card_count == 0
        assert record.filename == 'unknown'
        assert record.timestamp  # Should have a timestamp
    
    def test_to_dict(self):
        """Test converting record to dictionary."""
        record = ExportRecord(
            timestamp='2023-01-01T12:00:00Z',
            format_type='pdf',
            card_count=10,
            filename='cards.pdf'
        )
        
        data = record.to_dict()
        expected = {
            'timestamp': '2023-01-01T12:00:00Z',
            'format_type': 'pdf',
            'card_count': 10,
            'filename': 'cards.pdf'
        }
        
        assert data == expected
    
    def test_is_expired(self):
        """Test expiration check."""
        # Recent record
        recent_time = datetime.now(timezone.utc) - timedelta(days=1)
        recent_record = ExportRecord(
            timestamp=recent_time.isoformat(),
            format_type='pdf',
            card_count=10,
            filename='recent.pdf'
        )
        assert not recent_record.is_expired()
        
        # Old record
        old_time = datetime.now(timezone.utc) - timedelta(days=EXPORT_HISTORY_RETENTION_DAYS + 1)
        old_record = ExportRecord(
            timestamp=old_time.isoformat(),
            format_type='pdf',
            card_count=10,
            filename='old.pdf'
        )
        assert old_record.is_expired()
        
        # Invalid timestamp
        invalid_record = ExportRecord(
            timestamp='invalid-timestamp',
            format_type='pdf',
            card_count=10,
            filename='invalid.pdf'
        )
        assert invalid_record.is_expired()


class TestUserSnapshot:
    """Test UserSnapshot dataclass."""
    
    def test_snapshot_creation(self):
        """Test basic UserSnapshot creation."""
        now = datetime.now(timezone.utc).isoformat()
        snapshot = UserSnapshot(
            version=2,
            created_at=now,
            last_modified=now,
            input_text="测试文本",
            cards=[],
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=[]
        )
        
        assert snapshot.version == 2
        assert snapshot.input_text == "测试文本"
        assert snapshot.cards == []
        assert snapshot.total_cards_generated == 0
    
    def test_snapshot_validation(self):
        """Test snapshot validation."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Invalid version
        with pytest.raises(ValueError, match="Snapshot version must be >= 1"):
            UserSnapshot(
                version=0,
                created_at=now,
                last_modified=now,
                input_text="test",
                cards=[],
                options={},
                layout={},
                typography={},
                visual={},
                preview={},
                export_history=[]
            )
    
    def test_input_text_truncation(self):
        """Test input text truncation."""
        now = datetime.now(timezone.utc).isoformat()
        long_text = "x" * (MAX_INPUT_TEXT_LENGTH + 100)
        
        snapshot = UserSnapshot(
            version=2,
            created_at=now,
            last_modified=now,
            input_text=long_text,
            cards=[],
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=[]
        )
        
        assert len(snapshot.input_text) == MAX_INPUT_TEXT_LENGTH
    
    def test_export_history_cleanup(self):
        """Test export history cleanup."""
        now = datetime.now(timezone.utc).isoformat()
        
        # Create many old records
        old_records = []
        for i in range(MAX_EXPORT_HISTORY_RECORDS + 10):
            old_time = datetime.now(timezone.utc) - timedelta(days=EXPORT_HISTORY_RETENTION_DAYS + 1)
            old_records.append({
                'timestamp': old_time.isoformat(),
                'format_type': 'pdf',
                'card_count': i,
                'filename': f'old_{i}.pdf'
            })
        
        # Create some recent records
        recent_records = []
        for i in range(5):
            recent_time = datetime.now(timezone.utc) - timedelta(hours=i)
            recent_records.append({
                'timestamp': recent_time.isoformat(),
                'format_type': 'pdf',
                'card_count': i,
                'filename': f'recent_{i}.pdf'
            })
        
        all_records = old_records + recent_records
        
        snapshot = UserSnapshot(
            version=2,
            created_at=now,
            last_modified=now,
            input_text="test",
            cards=[],
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=all_records
        )
        
        # Should only keep recent records
        assert len(snapshot.export_history) == 5
        # Should be the recent ones
        for record in snapshot.export_history:
            assert 'recent_' in record['filename']
    
    def test_create_empty(self):
        """Test creating empty snapshot."""
        snapshot = UserSnapshot.create_empty()
        
        assert snapshot.version == CURRENT_SNAPSHOT_VERSION
        assert snapshot.input_text == ""
        assert snapshot.cards == []
        assert snapshot.total_cards_generated == 0
        assert snapshot.session_id  # Should have a session ID
    
    def test_from_session_state(self):
        """Test creating snapshot from session state."""
        mock_session_state = MagicMock()
        mock_session_state.input_text = "测试文本"
        mock_session_state.processed_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}
        ]
        mock_session_state.auto_pinyin = True
        mock_session_state.rows = 3
        mock_session_state.font_hanzi = 50
        mock_session_state.background_color = '#ff0000'
        mock_session_state.current_page = 1
        mock_session_state.export_history = []
        mock_session_state.total_cards_generated = 5
        
        # Mock missing attributes to return defaults
        def getattr_side_effect(obj, name, default=None):
            if hasattr(mock_session_state, name):
                return getattr(mock_session_state, name)
            return default
        
        with patch('builtins.getattr', side_effect=getattr_side_effect):
            snapshot = UserSnapshot.from_session_state(mock_session_state)
        
        assert snapshot.input_text == "测试文本"
        assert snapshot.options['auto_pinyin'] is True
        assert snapshot.layout['rows'] == 3
        assert snapshot.typography['font_hanzi'] == 50
        assert snapshot.visual['background_color'] == '#ff0000'
        assert snapshot.preview['current_page'] == 1
        assert snapshot.total_cards_generated == 5
    
    def test_apply_to_session_state(self):
        """Test applying snapshot to session state."""
        snapshot = UserSnapshot(
            version=2,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_modified=datetime.now(timezone.utc).isoformat(),
            input_text="测试文本",
            cards=[],
            options={'auto_pinyin': False},
            layout={'rows': 4},
            typography={'font_hanzi': 60},
            visual={'background_color': '#00ff00'},
            preview={'current_page': 2},
            export_history=[],
            total_cards_generated=10
        )
        
        mock_session_state = MagicMock()
        snapshot.apply_to_session_state(mock_session_state)
        
        assert mock_session_state.input_text == "测试文本"
        assert mock_session_state.auto_pinyin is False
        assert mock_session_state.rows == 4
        assert mock_session_state.font_hanzi == 60
        assert mock_session_state.background_color == '#00ff00'
        assert mock_session_state.current_page == 2
        assert mock_session_state.total_cards_generated == 10
    
    def test_size_estimation(self):
        """Test snapshot size estimation."""
        snapshot = UserSnapshot.create_empty()
        size = snapshot.estimate_size_bytes()
        
        assert size > 0
        assert isinstance(size, int)
    
    def test_truncate_for_storage(self):
        """Test truncating snapshot for storage."""
        # Create large snapshot
        large_text = "x" * MAX_INPUT_TEXT_LENGTH
        large_cards = [{'hanzi': f'字{i}', 'pinyin': f'zi{i}', 'english': f'char{i}'} for i in range(200)]
        large_history = [{'timestamp': datetime.now(timezone.utc).isoformat(), 'format_type': 'pdf', 'card_count': i, 'filename': f'file{i}.pdf'} for i in range(100)]
        
        snapshot = UserSnapshot(
            version=2,
            created_at=datetime.now(timezone.utc).isoformat(),
            last_modified=datetime.now(timezone.utc).isoformat(),
            input_text=large_text,
            cards=large_cards,
            options={},
            layout={},
            typography={},
            visual={},
            preview={},
            export_history=large_history
        )
        
        truncated = snapshot.truncate_for_storage()
        
        # Should be smaller
        assert len(truncated.input_text) <= len(snapshot.input_text)
        assert len(truncated.cards) <= len(snapshot.cards)
        assert len(truncated.export_history) <= len(snapshot.export_history)


class TestMigrationFunctions:
    """Test migration and validation functions."""
    
    def test_migrate_snapshot_current_version(self):
        """Test migration of current version snapshot."""
        data = {
            'version': CURRENT_SNAPSHOT_VERSION,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_modified': datetime.now(timezone.utc).isoformat(),
            'input_text': 'test',
            'cards': [],
            'options': {},
            'layout': {},
            'typography': {},
            'visual': {},
            'preview': {},
            'export_history': [],
            'session_id': 'test-session'
        }
        
        snapshot = migrate_snapshot(data)
        
        assert snapshot.version == CURRENT_SNAPSHOT_VERSION
        assert snapshot.input_text == 'test'
    
    def test_migrate_snapshot_v1_to_v2(self):
        """Test migration from version 1 to version 2."""
        v1_data = {
            'version': 1,
            'input_text': 'test v1',
            'cards': [],
            'options': {},
            'layout': {},
            'typography': {},
            'visual': {},
            'preview': {},
            'export_history': []
        }
        
        snapshot = migrate_snapshot(v1_data)
        
        assert snapshot.version == 2
        assert snapshot.input_text == 'test v1'
        assert snapshot.session_id  # Should have generated session_id
        assert snapshot.created_at  # Should have timestamps
        assert snapshot.last_modified
    
    def test_validate_snapshot_data_valid(self):
        """Test validation of valid snapshot data."""
        valid_data = {
            'version': 2,
            'input_text': 'test',
            'cards': []
        }
        
        assert validate_snapshot_data(valid_data) is True
    
    def test_validate_snapshot_data_invalid(self):
        """Test validation of invalid snapshot data."""
        # Not a dict
        assert validate_snapshot_data("not a dict") is False
        
        # Missing required fields
        assert validate_snapshot_data({}) is False
        
        # Invalid version
        assert validate_snapshot_data({'version': 'invalid', 'input_text': 'test', 'cards': []}) is False
        
        # Invalid input_text type
        assert validate_snapshot_data({'version': 2, 'input_text': 123, 'cards': []}) is False
        
        # Invalid cards type
        assert validate_snapshot_data({'version': 2, 'input_text': 'test', 'cards': 'not a list'}) is False
    
    def test_coerce_snapshot_data(self):
        """Test data type coercion."""
        raw_data = {
            'version': '2',  # String instead of int
            'input_text': 123,  # Number instead of string
            'cards': 'not a list',  # String instead of list
            'total_cards_generated': '5'  # String instead of int
        }
        
        coerced = coerce_snapshot_data(raw_data)
        
        assert coerced['version'] == 2
        assert coerced['input_text'] == '123'
        assert coerced['cards'] == []
        assert coerced['total_cards_generated'] == 5


class TestPersistenceUtilities:
    """Test persistence utility functions."""
    
    def test_is_persistence_enabled_env_var(self):
        """Test persistence enabled check with environment variable."""
        # Test with environment variable disabled
        with patch.dict(os.environ, {'DISABLE_PERSISTENCE': 'true'}):
            assert is_persistence_enabled() is False
        
        with patch.dict(os.environ, {'DISABLE_PERSISTENCE': '1'}):
            assert is_persistence_enabled() is False
        
        with patch.dict(os.environ, {'DISABLE_PERSISTENCE': 'yes'}):
            assert is_persistence_enabled() is False
    
    def test_is_persistence_enabled_feature_flag(self):
        """Test persistence enabled check with feature flag."""
        with patch('services.persistence.get_feature_flag', return_value=True):
            with patch.dict(os.environ, {}, clear=True):
                assert is_persistence_enabled() is True
        
        with patch('services.persistence.get_feature_flag', return_value=False):
            with patch.dict(os.environ, {}, clear=True):
                assert is_persistence_enabled() is False
    
    def test_create_snapshot_from_session_disabled(self):
        """Test creating snapshot when persistence is disabled."""
        with patch('services.persistence.is_persistence_enabled', return_value=False):
            result = create_snapshot_from_session(MagicMock())
            assert result is None
    
    def test_load_snapshot_from_data_disabled(self):
        """Test loading snapshot when persistence is disabled."""
        with patch('services.persistence.is_persistence_enabled', return_value=False):
            result = load_snapshot_from_data({'version': 2, 'input_text': 'test', 'cards': []})
            assert result is None
    
    def test_load_snapshot_from_data_invalid(self):
        """Test loading snapshot from invalid data."""
        with patch('services.persistence.is_persistence_enabled', return_value=True):
            result = load_snapshot_from_data("invalid data")
            assert result is None
