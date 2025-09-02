"""
Field aliasing and migration system.
Handles migration from gap/margin to gap_cm/margin_cm with backward compatibility.
"""

import logging
from typing import Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FieldAlias:
    """Configuration for a field alias."""
    old_name: str
    new_name: str
    unit_suffix: str = ""
    conversion_factor: float = 1.0
    description: str = ""


@dataclass
class MigrationResult:
    """Result of a field migration operation."""
    migrated_fields: Dict[str, Any]
    warnings: list[str]
    errors: list[str]
    migration_applied: bool


# Field alias definitions
FIELD_ALIASES = {
    'gap': FieldAlias(
        old_name='gap',
        new_name='gap_cm',
        unit_suffix='_cm',
        conversion_factor=1.0,  # Already in cm
        description='Card gap spacing in centimeters'
    ),
    'margin': FieldAlias(
        old_name='margin',
        new_name='margin_cm',
        unit_suffix='_cm',
        conversion_factor=1.0,  # Already in cm
        description='Page margin in centimeters'
    )
}

# Reverse mapping for lookups
REVERSE_ALIASES = {alias.new_name: alias for alias in FIELD_ALIASES.values()}


def get_canonical_field_name(field_name: str) -> str:
    """Get the canonical (new) field name for a given field."""
    if field_name in FIELD_ALIASES:
        return FIELD_ALIASES[field_name].new_name
    return field_name


def get_legacy_field_name(field_name: str) -> Optional[str]:
    """Get the legacy (old) field name for a canonical field."""
    if field_name in REVERSE_ALIASES:
        return REVERSE_ALIASES[field_name].old_name
    return None


def resolve_field_value(data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
    """
    Resolve field value with aliasing support.
    Tries canonical name first, then legacy name if available.
    """
    # Try canonical name first
    canonical_name = get_canonical_field_name(field_name)
    if canonical_name in data:
        return data[canonical_name]
    
    # Try legacy name if this is a canonical field
    legacy_name = get_legacy_field_name(field_name)
    if legacy_name and legacy_name in data:
        value = data[legacy_name]
        # Apply conversion if needed
        if field_name in REVERSE_ALIASES:
            alias = REVERSE_ALIASES[field_name]
            value = value * alias.conversion_factor
        return value
    
    # Try the field name as-is (for backward compatibility)
    if field_name in data:
        return data[field_name]
    
    return default


def migrate_fields(data: Dict[str, Any], in_place: bool = False) -> MigrationResult:
    """
    Migrate fields from legacy names to canonical names.
    
    Args:
        data: Dictionary containing field data
        in_place: Whether to modify the input dictionary
        
    Returns:
        MigrationResult with migration details
    """
    if not in_place:
        data = data.copy()
    
    migrated_fields = {}
    warnings = []
    errors = []
    migration_applied = False
    
    for old_name, alias in FIELD_ALIASES.items():
        if old_name in data and alias.new_name not in data:
            # Migrate old field to new field
            old_value = data[old_name]
            new_value = old_value * alias.conversion_factor
            
            data[alias.new_name] = new_value
            migrated_fields[old_name] = {
                'old_value': old_value,
                'new_value': new_value,
                'new_field': alias.new_name
            }
            
            # Remove old field to avoid confusion
            del data[old_name]
            migration_applied = True
            
            logger.info(f"Migrated field {old_name}={old_value} to {alias.new_name}={new_value}")
            
        elif old_name in data and alias.new_name in data:
            # Both old and new fields exist - this is a conflict
            old_value = data[old_name]
            new_value = data[alias.new_name]
            
            warnings.append(
                f"Field conflict: both {old_name}={old_value} and {alias.new_name}={new_value} exist. "
                f"Using canonical field {alias.new_name}."
            )
            
            # Remove old field to resolve conflict
            del data[old_name]
            migration_applied = True
    
    return MigrationResult(
        migrated_fields=migrated_fields,
        warnings=warnings,
        errors=errors,
        migration_applied=migration_applied
    )


def migrate_session_state(session_state: Any) -> MigrationResult:
    """
    Migrate session state fields from legacy to canonical names.
    
    Args:
        session_state: Streamlit session state object
        
    Returns:
        MigrationResult with migration details
    """
    migrated_fields = {}
    warnings = []
    errors = []
    migration_applied = False
    
    try:
        for old_name, alias in FIELD_ALIASES.items():
            old_attr = getattr(session_state, old_name, None)
            new_attr = getattr(session_state, alias.new_name, None)
            
            if old_attr is not None and new_attr is None:
                # Migrate old attribute to new attribute
                new_value = old_attr * alias.conversion_factor
                setattr(session_state, alias.new_name, new_value)
                
                migrated_fields[old_name] = {
                    'old_value': old_attr,
                    'new_value': new_value,
                    'new_field': alias.new_name
                }
                
                # Remove old attribute
                delattr(session_state, old_name)
                migration_applied = True
                
                logger.info(f"Migrated session state {old_name}={old_attr} to {alias.new_name}={new_value}")
                
            elif old_attr is not None and new_attr is not None:
                # Both old and new attributes exist - conflict
                warnings.append(
                    f"Session state conflict: both {old_name}={old_attr} and {alias.new_name}={new_attr} exist. "
                    f"Using canonical field {alias.new_name}."
                )
                
                # Remove old attribute to resolve conflict
                delattr(session_state, old_name)
                migration_applied = True
                
    except Exception as e:
        errors.append(f"Error migrating session state: {e}")
        logger.error(f"Session state migration error: {e}")
    
    return MigrationResult(
        migrated_fields=migrated_fields,
        warnings=warnings,
        errors=errors,
        migration_applied=migration_applied
    )


def migrate_snapshot_data(snapshot_data: Dict[str, Any]) -> MigrationResult:
    """
    Migrate snapshot data to use canonical field names.
    
    Args:
        snapshot_data: Snapshot data dictionary
        
    Returns:
        MigrationResult with migration details
    """
    all_migrated_fields = {}
    all_warnings = []
    all_errors = []
    overall_migration_applied = False
    
    # Migrate layout section
    if 'layout' in snapshot_data and isinstance(snapshot_data['layout'], dict):
        layout_result = migrate_fields(snapshot_data['layout'], in_place=True)
        if layout_result.migration_applied:
            all_migrated_fields.update({f"layout.{k}": v for k, v in layout_result.migrated_fields.items()})
            all_warnings.extend([f"Layout: {w}" for w in layout_result.warnings])
            all_errors.extend([f"Layout: {e}" for e in layout_result.errors])
            overall_migration_applied = True
    
    # Could extend to other sections if needed (typography, visual, etc.)
    
    return MigrationResult(
        migrated_fields=all_migrated_fields,
        warnings=all_warnings,
        errors=all_errors,
        migration_applied=overall_migration_applied
    )


def get_field_with_alias(data: Dict[str, Any], field_name: str, default: Any = None) -> Any:
    """
    Get field value with automatic aliasing support.
    This is the main function to use for reading configuration values.
    """
    return resolve_field_value(data, field_name, default)


def validate_field_units() -> Dict[str, str]:
    """
    Validate and document field units.
    Returns a dictionary mapping field names to their units.
    """
    field_units = {}
    
    for alias in FIELD_ALIASES.values():
        field_units[alias.new_name] = "cm"  # All current fields use centimeters
        
    # Add other known fields
    field_units.update({
        'layout_rows': 'count',
        'layout_cols': 'count',
        'card_size_cm': 'cm',
        'hanzi_font_size': 'pt',
        'pinyin_font_size': 'pt',
        'english_font_size': 'pt',
        'page_size': 'enum',
        'layout_auto_fill': 'boolean',
    })
    
    return field_units


def get_migration_status() -> Dict[str, Any]:
    """
    Get current migration status and field mapping information.
    Useful for debugging and documentation.
    """
    return {
        'field_aliases': {
            alias.old_name: {
                'new_name': alias.new_name,
                'unit_suffix': alias.unit_suffix,
                'conversion_factor': alias.conversion_factor,
                'description': alias.description
            }
            for alias in FIELD_ALIASES.values()
        },
        'canonical_fields': list(REVERSE_ALIASES.keys()),
        'legacy_fields': list(FIELD_ALIASES.keys()),
        'field_units': validate_field_units(),
        'migration_timestamp': datetime.now().isoformat()
    }
