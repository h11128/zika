#!/usr/bin/env python3
"""
Field Duplication Resolution Script.
Establishes canonical field names and resolves duplications across the codebase.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class FieldMapping:
    """A field mapping rule."""
    old_field: str
    new_field: str
    description: str
    contexts: List[str]  # Where this mapping applies


@dataclass
class FieldResolution:
    """Results of field duplication resolution."""
    files_modified: List[str]
    mappings_applied: List[Tuple[str, str, str]]  # (file, old, new)
    conflicts_resolved: List[str]
    errors: List[str]


class FieldDuplicationResolver:
    """Resolves field name duplications and establishes canonical naming."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.modified_files = []
        self.mappings_applied = []
        self.conflicts_resolved = []
        self.errors = []
        
        # Define canonical field mappings
        self.canonical_fields = self._define_canonical_fields()
        self.field_mappings = self._define_field_mappings()
        self.unit_standards = self._define_unit_standards()
    
    def _define_canonical_fields(self) -> Dict[str, Dict[str, str]]:
        """Define canonical field names by category."""
        return {
            # Typography fields - use _pt suffix for font sizes
            'typography': {
                'hanzi_font_size_pt': 'Font size for Chinese characters in points',
                'pinyin_font_size_pt': 'Font size for pinyin in points', 
                'english_font_size_pt': 'Font size for English in points',
                'hanzi_font_family': 'Font family for Chinese characters',
                'pinyin_font_family': 'Font family for pinyin',
                'english_font_family': 'Font family for English',
                'line_height_multiplier': 'Line height multiplier for text',
            },
            
            # Layout fields - use _cm suffix for dimensions
            'layout': {
                'layout_rows': 'Number of rows in layout grid',
                'layout_cols': 'Number of columns in layout grid',
                'card_size_cm': 'Card size in centimeters',
                'gap_cm': 'Gap between cards in centimeters',
                'margin_cm': 'Page margin in centimeters',
                'layout_auto_fill': 'Whether to auto-fill empty cards',
            },
            
            # Visual/Style fields
            'visual': {
                'background_color': 'Background color (hex)',
                'border_color': 'Border color (hex)',
                'text_color': 'Text color (hex)',
                'hanzi_color': 'Chinese character color (hex)',
                'pinyin_color': 'Pinyin text color (hex)',
                'english_color': 'English text color (hex)',
            },
            
            # Page/Export fields
            'page': {
                'page_size': 'Page size (A4, Letter, etc.)',
                'page_width_cm': 'Page width in centimeters',
                'page_height_cm': 'Page height in centimeters',
                'orientation': 'Page orientation (portrait/landscape)',
            }
        }
    
    def _define_field_mappings(self) -> List[FieldMapping]:
        """Define field mappings to resolve duplications."""
        return [
            # Font size field mappings
            FieldMapping(
                old_field="hanzi_font_size_pt",
                new_field='hanzi_font_size_pt',
                description='Standardize hanzi font size field',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="pinyin_font_size_pt", 
                new_field='pinyin_font_size_pt',
                description='Standardize pinyin font size field',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="english_font_size_pt",
                new_field='english_font_size_pt', 
                description='Standardize english font size field',
                contexts=['*.py', '*.json']
            ),
            
            # Font family field mappings
            FieldMapping(
                old_field="hanzi_font_family",
                new_field='hanzi_font_family',
                description='Standardize hanzi font family field',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="pinyin_font_family",
                new_field='pinyin_font_family',
                description='Standardize pinyin font family field', 
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="english_font_family",
                new_field='english_font_family',
                description='Standardize english font family field',
                contexts=['*.py', '*.json']
            ),
            
            # Size/dimension field mappings
            FieldMapping(
                old_field="gap_cm",
                new_field='gap_cm',
                description='Standardize gap field with unit',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="margin_cm",
                new_field='margin_cm', 
                description='Standardize margin field with unit',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="card_size_cm",
                new_field='card_size_cm',
                description='Standardize card size field with unit',
                contexts=['*.py', '*.json']
            ),
            
            # Layout field mappings
            FieldMapping(
                old_field="layout_rows",
                new_field='layout_rows',
                description='Standardize rows field with layout prefix',
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="layout_cols",
                new_field='layout_cols',
                description='Standardize cols field with layout prefix', 
                contexts=['*.py', '*.json']
            ),
            FieldMapping(
                old_field="layout_auto_fill",
                new_field='layout_auto_fill',
                description='Standardize auto_fill field with layout prefix',
                contexts=['*.py', '*.json']
            ),
        ]
    
    def _define_unit_standards(self) -> Dict[str, str]:
        """Define unit standardization rules."""
        return {
            # Size units - always use cm
            'cm': 'cm',
            'mm': 'cm',  # Convert mm to cm
            'in': 'cm',  # Convert inches to cm
            
            # Font units - always use pt
            'pt': 'pt',
            'px': 'pt',  # Convert px to pt where appropriate
            'em': 'pt',  # Convert em to pt
            
            # Color units - always use hex
            'hex': 'hex',
            'rgb': 'hex',  # Convert rgb to hex
            'hsl': 'hex',  # Convert hsl to hex
        }
    
    def resolve_all_duplications(self) -> FieldResolution:
        """Resolve all field duplications across the codebase."""
        print("🔧 Starting comprehensive field duplication resolution...")
        
        # 1. Apply field mappings
        self._apply_field_mappings()
        
        # 2. Resolve conflicts
        self._resolve_field_conflicts()
        
        # 3. Validate consistency
        self._validate_field_consistency()
        
        # 4. Update documentation
        self._update_field_documentation()
        
        return FieldResolution(
            files_modified=self.modified_files,
            mappings_applied=self.mappings_applied,
            conflicts_resolved=self.conflicts_resolved,
            errors=self.errors
        )
    
    def _apply_field_mappings(self):
        """Apply field mappings to resolve duplications."""
        print("📝 Applying field mappings...")
        
        for mapping in self.field_mappings:
            for context in mapping.contexts:
                for file_path in self.project_root.rglob(context):
                    if self._should_skip_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        
                        # Apply mapping with context-aware patterns
                        patterns = self._get_mapping_patterns(mapping.old_field, mapping.new_field)
                        
                        for pattern, replacement in patterns:
                            content = re.sub(pattern, replacement, content)
                        
                        if content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            self._record_mapping(str(file_path), mapping.old_field, mapping.new_field)
                            print(f"  ✅ Applied mapping '{mapping.description}' to {file_path}")
                    
                    except Exception as e:
                        error_msg = f"Error applying mapping '{mapping.description}' to {file_path}: {e}"
                        self.errors.append(error_msg)
                        print(f"  ❌ {error_msg}")
    
    def _get_mapping_patterns(self, old_field: str, new_field: str) -> List[Tuple[str, str]]:
        """Get regex patterns for field mapping."""
        return [
            # Dictionary key patterns
            (rf'[\'\"]{old_field}[\'\"]', f'"{new_field}"'),
            
            # Attribute access patterns
            (rf'\.{old_field}\b', f'.{new_field}'),
            
            # Variable assignment patterns
            (rf'\b{old_field}\s*=', f'{new_field} ='),
            
            # Function parameter patterns
            (rf'\b{old_field}\s*:', f'{new_field}:'),
            
            # Comment patterns
            (rf'#{old_field}\b', f'#{new_field}'),
        ]
    
    def _resolve_field_conflicts(self):
        """Resolve conflicts between different field naming conventions."""
        print("🔄 Resolving field conflicts...")
        
        # Define conflict resolution rules
        conflicts = [
            # Font size conflicts
            ('hanzi_font_size_pt', 'hanzi_font_size_pt', 'hanzi_font_size_pt'),
            ('pinyin_font_size_pt', 'pinyin_font_size_pt', 'pinyin_font_size_pt'),
            ('english_font_size_pt', 'english_font_size_pt', 'english_font_size_pt'),
            
            # Font family conflicts
            ("hanzi_font_family", 'hanzi_font_family', 'hanzi_font_family'),
            ("pinyin_font_family", 'pinyin_font_family', 'pinyin_font_family'),
            ("english_font_family", 'english_font_family', 'english_font_family'),
        ]
        
        for old_field1, old_field2, canonical_field in conflicts:
            self._resolve_specific_conflict(old_field1, old_field2, canonical_field)
    
    def _resolve_specific_conflict(self, field1: str, field2: str, canonical: str):
        """Resolve a specific field conflict."""
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Replace both conflicting fields with canonical
                content = re.sub(rf'\b{field1}\b', canonical, content)
                content = re.sub(rf'\b{field2}\b', canonical, content)
                
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.conflicts_resolved.append(f"{py_file}: {field1}/{field2} → {canonical}")
                    print(f"  ✅ Resolved conflict {field1}/{field2} → {canonical} in {py_file}")
            
            except Exception as e:
                error_msg = f"Error resolving conflict in {py_file}: {e}"
                self.errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    def _validate_field_consistency(self):
        """Validate field consistency across the codebase."""
        print("✅ Validating field consistency...")
        
        # Check for remaining duplications
        duplications = []
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for old field patterns
                old_patterns = [
                    r'\bfont_hanzi\b(?!_)',
                    r'\bfont_pinyin\b(?!_)',
                    r'\bfont_english\b(?!_)',
                    r'\bhanzi_font\b(?!_family)',
                    r'\bgap\b(?!_cm)',
                    r'\bmargin\b(?!_cm)',
                ]
                
                for pattern in old_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        duplications.append(f"{py_file}: Found old pattern '{pattern}'")
            
            except Exception as e:
                self.errors.append(f"Error validating {py_file}: {e}")
        
        if duplications:
            print("  ⚠️  Found remaining field duplications:")
            for duplication in duplications:
                print(f"    - {duplication}")
        else:
            print("  ✅ All field duplications resolved")
    
    def _update_field_documentation(self):
        """Update documentation to reflect canonical field names."""
        print("📚 Updating field documentation...")
        
        # Create canonical fields reference
        canonical_ref_path = self.project_root / "docs" / "CANONICAL_FIELDS.md"
        self._create_canonical_fields_reference(canonical_ref_path)
        
        # Update existing documentation
        doc_files = list(self.project_root.rglob("*.md"))
        
        for doc_file in doc_files:
            if self._should_skip_file(doc_file):
                continue
            
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Update field references in documentation
                field_updates = [
                    (r'\bfont_hanzi\b', 'hanzi_font_size_pt'),
                    (r'\bfont_pinyin\b', 'pinyin_font_size_pt'),
                    (r'\bfont_english\b', 'english_font_size_pt'),
                    (r'\bhanzi_font\b(?!_family)', 'hanzi_font_family'),
                ]
                
                for pattern, replacement in field_updates:
                    content = re.sub(pattern, replacement, content)
                
                if content != original_content:
                    with open(doc_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"  ✅ Updated field references in {doc_file}")
            
            except Exception as e:
                error_msg = f"Error updating documentation in {doc_file}: {e}"
                self.errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    def _create_canonical_fields_reference(self, ref_path: Path):
        """Create canonical fields reference documentation."""
        ref_path.parent.mkdir(exist_ok=True)
        
        content = "# Canonical Field Names Reference\n\n"
        content += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "This document defines the canonical field names used throughout the application.\n\n"
        
        for category, fields in self.canonical_fields.items():
            content += f"## {category.title()} Fields\n\n"
            for field, description in fields.items():
                content += f"- **`{field}`**: {description}\n"
            content += "\n"
        
        content += "## Field Mapping Rules\n\n"
        content += "The following mappings are applied to resolve field duplications:\n\n"
        
        for mapping in self.field_mappings:
            content += f"- `{mapping.old_field}` → `{mapping.new_field}`: {mapping.description}\n"
        
        with open(ref_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"  ✅ Created canonical fields reference: {ref_path}")
    
    def _record_mapping(self, file_path: str, old_field: str, new_field: str):
        """Record a mapping that was applied."""
        self.mappings_applied.append((file_path, old_field, new_field))
        if file_path not in self.modified_files:
            self.modified_files.append(file_path)
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during processing."""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            "build",
            "dist",
            "cleanup_reports",
            ".mypy_cache",
            "htmlcov",
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)


def main():
    """Main entry point for field duplication resolution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Resolve field duplications")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--output-dir", default="cleanup_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
        return
    
    resolver = FieldDuplicationResolver()
    result = resolver.resolve_all_duplications()
    
    # Generate report
    os.makedirs(args.output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(args.output_dir, f"field_duplication_resolution_{timestamp}.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Field Duplication Resolution Report\n\n")
        f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Files Modified**: {len(result.files_modified)}\n")
        f.write(f"- **Mappings Applied**: {len(result.mappings_applied)}\n")
        f.write(f"- **Conflicts Resolved**: {len(result.conflicts_resolved)}\n")
        f.write(f"- **Errors**: {len(result.errors)}\n\n")
        
        if result.files_modified:
            f.write("## Modified Files\n\n")
            for file_path in result.files_modified:
                f.write(f"- {file_path}\n")
            f.write("\n")
        
        if result.mappings_applied:
            f.write("## Mappings Applied\n\n")
            for file_path, old, new in result.mappings_applied:
                f.write(f"- **{file_path}**: `{old}` → `{new}`\n")
            f.write("\n")
        
        if result.conflicts_resolved:
            f.write("## Conflicts Resolved\n\n")
            for conflict in result.conflicts_resolved:
                f.write(f"- {conflict}\n")
            f.write("\n")
        
        if result.errors:
            f.write("## Errors\n\n")
            for error in result.errors:
                f.write(f"- {error}\n")
    
    print(f"\n📊 Field duplication resolution complete!")
    print(f"   - Files modified: {len(result.files_modified)}")
    print(f"   - Mappings applied: {len(result.mappings_applied)}")
    print(f"   - Conflicts resolved: {len(result.conflicts_resolved)}")
    print(f"   - Errors: {len(result.errors)}")
    print(f"   - Report saved: {report_file}")


if __name__ == "__main__":
    main()
