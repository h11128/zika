"""
Integration tests for field migration system.
Tests end-to-end migration scenarios and backward compatibility.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.field_migration import (
    migrate_fields, migrate_snapshot_data, resolve_field_value,
    get_field_with_alias, get_migration_status
)
from services.persistence import migrate_snapshot


class TestFieldMigrationIntegration:
    """Integration tests for field migration."""
    
    def test_snapshot_migration_with_legacy_fields(self):
        """Test complete snapshot migration with legacy fields."""
        # Create a snapshot with legacy field names
        legacy_snapshot = {
            'version': 3,
            'created_at': '2025-08-30T12:00:00Z',
            'last_modified': '2025-08-30T12:00:00Z',
            'input_text': 'test text',
            'cards': [],
            'options': {
                'auto_pinyin': True,
                'auto_translate': True,
                'use_segmented': False
            },
            'layout': {
                'rows': 3,
                'cols': 2,
                'auto_fill': True,
                'card_size': 5.5,
                'gap': 0.7,  # Legacy field
                'margin': 1.2,  # Legacy field
                'page_size': 'A4'
            },
            'typography': {
                'font_hanzi': 48,
                'font_pinyin': 18,
                'font_english': 14,
                'hanzi_font': 'SimHei'
            },
            'visual': {
                'background_color': '#ffffff',
                'preview_mode': '📄 完整页面'
            },
            'preview': {
                'current_page': 1,
                'nav_index': 0
            },
            'export_history': []
        }
        
        # Migrate the snapshot
        migrated_snapshot = migrate_snapshot(legacy_snapshot)
        
        # Verify migration was successful
        assert migrated_snapshot.version == 3
        assert migrated_snapshot.input_text == 'test text'
        
        # Verify layout fields were migrated
        layout = migrated_snapshot.layout
        assert 'gap' not in layout  # Legacy field should be removed
        assert 'margin' not in layout  # Legacy field should be removed
        assert layout['gap_cm'] == 0.7  # Canonical field should exist
        assert layout['margin_cm'] == 1.2  # Canonical field should exist
        assert layout['rows'] == 3  # Other fields unchanged
        assert layout['cols'] == 2
        assert layout['page_size'] == 'A4'
        
        # Other sections should be unchanged
        assert migrated_snapshot.typography['font_hanzi'] == 48
        assert migrated_snapshot.visual['background_color'] == '#ffffff'
    
    def test_snapshot_migration_with_canonical_fields(self):
        """Test snapshot migration when canonical fields already exist."""
        # Create a snapshot with canonical field names
        canonical_snapshot = {
            'version': 3,
            'created_at': '2025-08-30T12:00:00Z',
            'last_modified': '2025-08-30T12:00:00Z',
            'input_text': 'test text',
            'cards': [],
            'options': {
                'auto_pinyin': True,
                'auto_translate': True,
                'use_segmented': False
            },
            'layout': {
                'rows': 3,
                'cols': 2,
                'auto_fill': True,
                'card_size': 5.5,
                'gap_cm': 0.7,  # Canonical field
                'margin_cm': 1.2,  # Canonical field
                'page_size': 'A4'
            },
            'typography': {
                'font_hanzi': 48,
                'font_pinyin': 18,
                'font_english': 14,
                'hanzi_font': 'SimHei'
            },
            'visual': {
                'background_color': '#ffffff',
                'preview_mode': '📄 完整页面'
            },
            'preview': {
                'current_page': 1,
                'nav_index': 0
            },
            'export_history': []
        }
        
        # Migrate the snapshot
        migrated_snapshot = migrate_snapshot(canonical_snapshot)
        
        # Verify no migration was needed
        assert migrated_snapshot.version == 3
        layout = migrated_snapshot.layout
        assert layout['gap_cm'] == 0.7  # Should remain unchanged
        assert layout['margin_cm'] == 1.2  # Should remain unchanged
        assert 'gap' not in layout  # Legacy fields should not exist
        assert 'margin' not in layout
    
    def test_snapshot_migration_with_field_conflicts(self):
        """Test snapshot migration with both legacy and canonical fields."""
        # Create a snapshot with both legacy and canonical fields
        conflict_snapshot = {
            'version': 3,
            'created_at': '2025-08-30T12:00:00Z',
            'last_modified': '2025-08-30T12:00:00Z',
            'input_text': 'test text',
            'cards': [],
            'options': {
                'auto_pinyin': True,
                'auto_translate': True,
                'use_segmented': False
            },
            'layout': {
                'rows': 3,
                'cols': 2,
                'auto_fill': True,
                'card_size': 5.5,
                'gap': 0.5,  # Legacy field
                'gap_cm': 0.7,  # Canonical field (should win)
                'margin': 1.0,  # Legacy field
                'margin_cm': 1.2,  # Canonical field (should win)
                'page_size': 'A4'
            },
            'typography': {
                'font_hanzi': 48,
                'font_pinyin': 18,
                'font_english': 14,
                'hanzi_font': 'SimHei'
            },
            'visual': {
                'background_color': '#ffffff',
                'preview_mode': '📄 完整页面'
            },
            'preview': {
                'current_page': 1,
                'nav_index': 0
            },
            'export_history': []
        }
        
        # Migrate the snapshot
        migrated_snapshot = migrate_snapshot(conflict_snapshot)
        
        # Verify canonical fields won the conflict
        layout = migrated_snapshot.layout
        assert layout['gap_cm'] == 0.7  # Canonical field should be preserved
        assert layout['margin_cm'] == 1.2  # Canonical field should be preserved
        assert 'gap' not in layout  # Legacy field should be removed
        assert 'margin' not in layout  # Legacy field should be removed
    
    def test_field_resolution_in_digest_computation(self):
        """Test field resolution in digest computation scenarios."""
        # Test with legacy fields only
        legacy_data = {
            'gap': 0.5,
            'margin': 1.0,
            'rows': 3,
            'cols': 2
        }
        
        gap_cm = resolve_field_value(legacy_data, 'gap_cm', 0.8)
        margin_cm = resolve_field_value(legacy_data, 'margin_cm', 1.5)
        
        assert gap_cm == 0.5  # Should resolve from legacy field
        assert margin_cm == 1.0  # Should resolve from legacy field
        
        # Test with canonical fields only
        canonical_data = {
            'gap_cm': 0.7,
            'margin_cm': 1.2,
            'rows': 3,
            'cols': 2
        }
        
        gap_cm = resolve_field_value(canonical_data, 'gap_cm', 0.8)
        margin_cm = resolve_field_value(canonical_data, 'margin_cm', 1.5)
        
        assert gap_cm == 0.7  # Should resolve from canonical field
        assert margin_cm == 1.2  # Should resolve from canonical field
        
        # Test with mixed fields (canonical should win)
        mixed_data = {
            'gap': 0.5,
            'gap_cm': 0.7,
            'margin': 1.0,
            'margin_cm': 1.2,
            'rows': 3,
            'cols': 2
        }
        
        gap_cm = resolve_field_value(mixed_data, 'gap_cm', 0.8)
        margin_cm = resolve_field_value(mixed_data, 'margin_cm', 1.5)
        
        assert gap_cm == 0.7  # Should resolve from canonical field
        assert margin_cm == 1.2  # Should resolve from canonical field
    
    def test_backward_compatibility_with_existing_code(self):
        """Test that existing code patterns still work with migration."""
        # Simulate existing code that might use either field name
        def get_layout_config(data):
            """Simulate existing function that gets layout config."""
            return {
                'gap_cm': get_field_with_alias(data, 'gap_cm', 0.5),
                'margin_cm': get_field_with_alias(data, 'margin_cm', 1.0),
                'rows': data.get('rows', 2),
                'cols': data.get('cols', 3)
            }
        
        # Test with legacy data
        legacy_config = get_layout_config({
            'gap': 0.8,
            'margin': 1.5,
            'rows': 4,
            'cols': 2
        })
        
        assert legacy_config['gap_cm'] == 0.8
        assert legacy_config['margin_cm'] == 1.5
        assert legacy_config['rows'] == 4
        assert legacy_config['cols'] == 2
        
        # Test with canonical data
        canonical_config = get_layout_config({
            'gap_cm': 0.6,
            'margin_cm': 1.3,
            'rows': 3,
            'cols': 4
        })
        
        assert canonical_config['gap_cm'] == 0.6
        assert canonical_config['margin_cm'] == 1.3
        assert canonical_config['rows'] == 3
        assert canonical_config['cols'] == 4
        
        # Test with mixed data (canonical should win)
        mixed_config = get_layout_config({
            'gap': 0.4,
            'gap_cm': 0.6,
            'margin': 0.8,
            'margin_cm': 1.3,
            'rows': 3,
            'cols': 4
        })
        
        assert mixed_config['gap_cm'] == 0.6  # Canonical wins
        assert mixed_config['margin_cm'] == 1.3  # Canonical wins
    
    def test_migration_status_and_documentation(self):
        """Test migration status and documentation functions."""
        status = get_migration_status()
        
        # Verify status structure
        assert 'field_aliases' in status
        assert 'canonical_fields' in status
        assert 'legacy_fields' in status
        assert 'field_units' in status
        assert 'migration_timestamp' in status
        
        # Verify field aliases
        aliases = status['field_aliases']
        assert 'gap' in aliases
        assert 'margin' in aliases
        assert aliases['gap']['new_name'] == 'gap_cm'
        assert aliases['margin']['new_name'] == 'margin_cm'
        
        # Verify field lists
        assert 'gap_cm' in status['canonical_fields']
        assert 'margin_cm' in status['canonical_fields']
        assert 'gap' in status['legacy_fields']
        assert 'margin' in status['legacy_fields']
        
        # Verify field units
        units = status['field_units']
        assert units['gap_cm'] == 'cm'
        assert units['margin_cm'] == 'cm'
        assert units['rows'] == 'count'
        assert units['cols'] == 'count'
        assert units['font_hanzi'] == 'pt'
    
    def test_end_to_end_migration_workflow(self):
        """Test complete end-to-end migration workflow."""
        # Step 1: Start with legacy snapshot data
        legacy_data = {
            'version': 2,  # Old version
            'layout': {
                'gap': 0.6,
                'margin': 1.1,
                'rows': 4,
                'cols': 3
            }
        }
        
        # Step 2: Migrate snapshot data
        migration_result = migrate_snapshot_data(legacy_data)
        
        assert migration_result.migration_applied is True
        assert len(migration_result.migrated_fields) == 2
        assert 'layout.gap' in migration_result.migrated_fields
        assert 'layout.margin' in migration_result.migrated_fields
        
        # Step 3: Verify migrated data structure
        layout = legacy_data['layout']
        assert 'gap' not in layout
        assert 'margin' not in layout
        assert layout['gap_cm'] == 0.6
        assert layout['margin_cm'] == 1.1
        assert layout['rows'] == 4  # Unchanged
        assert layout['cols'] == 3  # Unchanged
        
        # Step 4: Test field resolution on migrated data
        gap_resolved = resolve_field_value(layout, 'gap_cm', 0.5)
        margin_resolved = resolve_field_value(layout, 'margin_cm', 1.0)
        
        assert gap_resolved == 0.6
        assert margin_resolved == 1.1
        
        # Step 5: Test that legacy field resolution still works (should resolve to canonical)
        gap_legacy = resolve_field_value(layout, 'gap', 0.5)
        margin_legacy = resolve_field_value(layout, 'margin', 1.0)

        assert gap_legacy == 0.6  # Should resolve to canonical field value
        assert margin_legacy == 1.1  # Should resolve to canonical field value
