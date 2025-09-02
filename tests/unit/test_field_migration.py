"""
Unit tests for field migration system.
Tests aliasing, migration, and backward compatibility.
"""

import pytest
from unittest.mock import MagicMock

from core.field_migration import (
    get_canonical_field_name, get_legacy_field_name, resolve_field_value,
    migrate_fields, migrate_session_state, migrate_snapshot_data,
    get_field_with_alias, validate_field_units, get_migration_status,
    FIELD_ALIASES, REVERSE_ALIASES, MigrationResult
)


class TestFieldAliases:
    """Test field alias definitions and lookups."""
    
    def test_field_aliases_defined(self):
        """Test that field aliases are properly defined."""
        assert 'gap' in FIELD_ALIASES
        assert 'margin' in FIELD_ALIASES

        gap_alias = FIELD_ALIASES['gap']
        assert gap_alias.old_name == 'gap'
        assert gap_alias.new_name == 'gap_cm'
        assert gap_alias.unit_suffix == '_cm'
        assert gap_alias.conversion_factor == 1.0

        margin_alias = FIELD_ALIASES['margin']
        assert margin_alias.old_name == 'margin'
        assert margin_alias.new_name == 'margin_cm'
        assert margin_alias.unit_suffix == '_cm'
        assert margin_alias.conversion_factor == 1.0
    
    def test_reverse_aliases(self):
        """Test reverse alias mapping."""
        assert 'gap_cm' in REVERSE_ALIASES
        assert 'margin_cm' in REVERSE_ALIASES

        assert REVERSE_ALIASES['gap_cm'].old_name == 'gap'
        assert REVERSE_ALIASES['margin_cm'].old_name == 'margin'
    
    def test_get_canonical_field_name(self):
        """Test getting canonical field names."""
        assert get_canonical_field_name('gap') == 'gap_cm'
        assert get_canonical_field_name('margin') == 'margin_cm'
        assert get_canonical_field_name('gap_cm') == 'gap_cm'  # Already canonical
        assert get_canonical_field_name('layout_rows') == 'layout_rows'  # No alias

    def test_get_legacy_field_name(self):
        """Test getting legacy field names."""
        assert get_legacy_field_name('gap_cm') == 'gap'
        assert get_legacy_field_name('margin_cm') == 'margin'
        assert get_legacy_field_name('layout_rows') is None  # No alias


class TestFieldResolution:
    """Test field value resolution with aliasing."""
    
    def test_resolve_field_value_canonical_exists(self):
        """Test resolving when canonical field exists."""
        data = {'gap_cm': 0.8}  # Canonical field exists
        result = resolve_field_value(data, 'gap_cm', 1.0)
        assert result == 0.8  # Should use canonical
    
    def test_resolve_field_value_legacy_fallback(self):
        """Test resolving when only legacy field exists."""
        data = {'gap_cm': 0.5}  # Only legacy exists
        result = resolve_field_value(data, 'gap_cm', 1.0)
        assert result == 0.5  # Should use legacy with conversion
    
    def test_resolve_field_value_default(self):
        """Test resolving when neither field exists."""
        data = {'layout_rows': 3}  # Different field
        result = resolve_field_value(data, 'gap_cm', 1.0)
        assert result == 1.0  # Should use default
    
    def test_resolve_field_value_no_alias(self):
        """Test resolving field without alias."""
        data = {'layout_rows': 3}
        result = resolve_field_value(data, 'layout_rows', 2)
        assert result == 3  # Should use direct value
    
    def test_get_field_with_alias(self):
        """Test convenience function for field resolution."""
        data = {'gap_cm': 0.7, 'margin_cm': 1.5}
        
        gap_result = get_field_with_alias(data, 'gap_cm', 0.5)
        assert gap_result == 0.7  # From legacy field
        
        margin_result = get_field_with_alias(data, 'margin_cm', 1.0)
        assert margin_result == 1.5  # From canonical field


class TestFieldMigration:
    """Test field migration functions."""
    
    def test_migrate_fields_basic(self):
        """Test basic field migration."""
        data = {'gap': 0.5, 'margin': 1.0, 'layout_rows': 3}
        result = migrate_fields(data, in_place=False)

        assert result.migration_applied is True
        assert len(result.migrated_fields) == 2
        assert 'gap' in result.migrated_fields
        assert 'margin' in result.migrated_fields

        # Original data should be unchanged (not in_place)
        assert 'gap' in data
        assert 'margin' in data

        # Check migrated values
        assert result.migrated_fields['gap']['new_field'] == 'gap_cm'
        assert result.migrated_fields['gap']['new_value'] == 0.5
        assert result.migrated_fields['margin']['new_field'] == 'margin_cm'
        assert result.migrated_fields['margin']['new_value'] == 1.0
    
    def test_migrate_fields_in_place(self):
        """Test in-place field migration."""
        data = {'gap_cm': 0.5, 'margin_cm': 1.0, 'layout_rows': 3}
        result = migrate_fields(data, in_place=True)
        
        assert result.migration_applied is True
        
        # Data should be modified in place
        assert 'gap_cm' not in data  # Old field removed
        assert 'margin_cm' not in data  # Old field removed
        assert data['gap_cm'] == 0.5  # New field added
        assert data['margin_cm'] == 1.0  # New field added
        assert data['layout_rows'] == 3  # Unchanged field preserved
    
    def test_migrate_fields_conflict(self):
        """Test migration with field conflicts."""
        data = {'gap_cm': 0.5, 'gap_cm': 0.8, 'margin_cm': 1.0}
        result = migrate_fields(data, in_place=True)
        
        assert result.migration_applied is True
        assert len(result.warnings) == 1
        assert 'conflict' in result.warnings[0].lower()
        
        # Should keep canonical field and remove legacy
        assert 'gap_cm' not in data
        assert data['gap_cm'] == 0.8  # Canonical field preserved
    
    def test_migrate_fields_no_migration_needed(self):
        """Test migration when no migration is needed."""
        data = {'gap_cm': 0.5, 'margin_cm': 1.0, 'layout_rows': 3}
        result = migrate_fields(data, in_place=False)
        
        assert result.migration_applied is False
        assert len(result.migrated_fields) == 0
        assert len(result.warnings) == 0
        assert len(result.errors) == 0


class TestSessionStateMigration:
    """Test session state migration."""
    
    def test_migrate_session_state_success(self):
        """Test successful session state migration."""
        # Create a simple mock object that behaves like session state
        class MockSessionState:
            def __init__(self):
                self._attrs = {'gap_cm': 0.5, 'margin_cm': 1.0}
                self.setattr_calls = []
                self.delattr_calls = []

            def __getattr__(self, name):
                return self._attrs.get(name, None)

            def __setattr__(self, name, value):
                if name.startswith('_') or name.endswith('_calls'):
                    super().__setattr__(name, value)
                else:
                    self.setattr_calls.append((name, value))
                    self._attrs[name] = value

            def __delattr__(self, name):
                self.delattr_calls.append(name)
                if name in self._attrs:
                    del self._attrs[name]

        session_state = MockSessionState()

        result = migrate_session_state(session_state)

        assert result.migration_applied is True
        assert len(result.migrated_fields) == 2

        # Verify setattr and delattr were called
        assert ('gap_cm', 0.5) in session_state.setattr_calls
        assert ('margin_cm', 1.0) in session_state.setattr_calls
        assert 'gap_cm' in session_state.delattr_calls
        assert 'margin_cm' in session_state.delattr_calls
    
    def test_migrate_session_state_error_handling(self):
        """Test session state migration error handling."""
        # Create a mock that raises errors on setattr
        class ErrorSessionState:
            def __getattr__(self, name):
                if name == 'gap_cm':
                    return 0.5
                return None

            def __setattr__(self, name, value):
                raise Exception("Mock error")

            def __delattr__(self, name):
                pass

        session_state = ErrorSessionState()
        result = migrate_session_state(session_state)

        assert len(result.errors) > 0
        assert 'Mock error' in result.errors[0]


class TestSnapshotMigration:
    """Test snapshot data migration."""
    
    def test_migrate_snapshot_data_layout(self):
        """Test migrating snapshot layout data."""
        snapshot_data = {
            'layout': {
                'gap_cm': 0.5,
                'margin_cm': 1.0,
                'layout_rows': 3,
                'layout_cols': 2
            },
            'typography': {
                'hanzi_font_size': 48
            }
        }
        
        result = migrate_snapshot_data(snapshot_data)
        
        assert result.migration_applied is True
        assert len(result.migrated_fields) == 2
        assert 'layout.gap_cm' in result.migrated_fields
        assert 'layout.margin_cm' in result.migrated_fields
        
        # Check that layout was modified
        layout = snapshot_data['layout']
        assert 'gap_cm' not in layout
        assert 'margin_cm' not in layout
        assert layout['gap_cm'] == 0.5
        assert layout['margin_cm'] == 1.0
        assert layout['layout_rows'] == 3  # Unchanged
        
        # Typography should be unchanged
        assert snapshot_data['typography']['hanzi_font_size'] == 48
    
    def test_migrate_snapshot_data_no_layout(self):
        """Test migrating snapshot without layout section."""
        snapshot_data = {
            'typography': {
                'hanzi_font_size': 48
            }
        }
        
        result = migrate_snapshot_data(snapshot_data)
        
        assert result.migration_applied is False
        assert len(result.migrated_fields) == 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_validate_field_units(self):
        """Test field units validation."""
        units = validate_field_units()
        
        assert units['gap_cm'] == 'cm'
        assert units['margin_cm'] == 'cm'
        assert units['layout_rows'] == 'count'
        assert units['layout_cols'] == 'count'
        assert units['hanzi_font_size'] == 'pt'
        assert units['page_size'] == 'enum'
        assert units['layout_auto_fill'] == 'boolean'
    
    def test_get_migration_status(self):
        """Test migration status information."""
        status = get_migration_status()
        
        assert 'field_aliases' in status
        assert 'canonical_fields' in status
        assert 'legacy_fields' in status
        assert 'field_units' in status
        assert 'migration_timestamp' in status
        
        # Check field aliases structure
        aliases = status['field_aliases']
        assert 'gap_cm' in aliases
        assert aliases['gap_cm']['new_name'] == 'gap_cm'
        assert aliases['gap_cm']['unit_suffix'] == '_cm'
        
        # Check field lists
        assert 'gap_cm' in status['canonical_fields']
        assert 'margin_cm' in status['canonical_fields']
        assert 'gap_cm' in status['legacy_fields']
        assert 'margin_cm' in status['legacy_fields']
