#!/usr/bin/env python3
"""
Naming Convention Standardization Script.
Standardizes naming across all modules, units, and field names.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class NamingRule:
    """A naming standardization rule."""
    pattern: str
    replacement: str
    description: str
    file_patterns: List[str]


@dataclass
class NamingStandardization:
    """Results of naming standardization."""
    files_modified: List[str]
    changes_made: List[Tuple[str, str, str]]  # (file, old, new)
    errors: List[str]


class NamingStandardizer:
    """Standardizes naming conventions across the codebase."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.modified_files = []
        self.changes_made = []
        self.errors = []
        
        # Define standardization rules
        self.naming_rules = self._define_naming_rules()
        self.unit_standardization = self._define_unit_standards()
        self.field_mappings = self._define_field_mappings()
    
    def _define_naming_rules(self) -> List[NamingRule]:
        """Define naming standardization rules."""
        return [
            # Function naming standardization
            NamingRule(
                pattern=r'\bexport_key\(',
                replacement='compute_export_key(',
                description="Standardize export key function name",
                file_patterns=["*.py"]
            ),
            
            # Variable naming standardization
            NamingRule(
                pattern=r'\bnav_digest\b',
                replacement='nav_index',
                description="Rename nav_digest to nav_index for clarity",
                file_patterns=["*.py"]
            ),
            
            # Module path standardization
            NamingRule(
                pattern=r'services\.cache(?!_v2)',
                replacement='services.cache_v2',
                description="Use cache_v2 consistently",
                file_patterns=["*.py"]
            ),
            
            # Field name standardization - font fields
            NamingRule(
                pattern=r'\bfont_hanzi\b',
                replacement='hanzi_font_size',
                description="Standardize hanzi font size field name",
                file_patterns=["*.py", "*.json"]
            ),
            
            NamingRule(
                pattern=r'\bfont_pinyin\b',
                replacement='pinyin_font_size',
                description="Standardize pinyin font size field name",
                file_patterns=["*.py", "*.json"]
            ),
            
            NamingRule(
                pattern=r'\bfont_english\b',
                replacement='english_font_size',
                description="Standardize english font size field name",
                file_patterns=["*.py", "*.json"]
            ),
            
            # Layout field standardization
            NamingRule(
                pattern=r'layout\.layout_rows',
                replacement='layout.layout_rows',
                description="Ensure consistent layout field access",
                file_patterns=["*.py"]
            ),
            
            NamingRule(
                pattern=r'layout\.layout_cols',
                replacement='layout.layout_cols',
                description="Ensure consistent layout field access",
                file_patterns=["*.py"]
            ),
        ]
    
    def _define_unit_standards(self) -> Dict[str, str]:
        """Define unit standardization mappings."""
        return {
            # Size units - standardize to cm
            'gap_cm': 'gap_cm',
            'margin_cm': 'margin_cm',
            'card_size_cm': 'card_size_cm',
            'width_cm': 'width_cm',
            'height_cm': 'height_cm',
            
            # Font units - standardize to pt
            'hanzi_font_size': 'hanzi_font_size_pt',
            'pinyin_font_size': 'pinyin_font_size_pt',
            'english_font_size': 'english_font_size_pt',
            
            # Pixel units - explicit px suffix
            'line_height_px': 'line_height_px',
            'margin_top_px': 'margin_top_px',
            'margin_bottom_px': 'margin_bottom_px',
        }
    
    def _define_field_mappings(self) -> Dict[str, str]:
        """Define field name mappings to resolve duplicates."""
        return {
            # Resolve font field duplication
            'hanzi_font_size': 'hanzi_font_size_pt',
            'hanzi_font_family': 'hanzi_font_family',
            'pinyin_font_size': 'pinyin_font_size_pt',
            'pinyin_font_family': 'pinyin_font_family',
            'english_font_size': 'english_font_size_pt',
            'english_font_family': 'english_font_family',
            
            # Layout field standardization
            'layout_rows': 'layout_rows',
            'layout_cols': 'layout_cols',
            'layout_auto_fill': 'layout_auto_fill',
            
            # Style field standardization
            'background_color': 'background_color',
            'border_color': 'border_color',
            'text_color': 'text_color',
        }
    
    def standardize_all(self) -> NamingStandardization:
        """Perform all naming standardizations."""
        print("🔧 Starting comprehensive naming standardization...")
        
        # 1. Apply naming rules
        self._apply_naming_rules()
        
        # 2. Standardize units
        self._standardize_units()
        
        # 3. Resolve field duplications
        self._resolve_field_duplications()
        
        # 4. Update documentation
        self._update_documentation()
        
        # 5. Validate consistency
        self._validate_naming_consistency()
        
        return NamingStandardization(
            files_modified=self.modified_files,
            changes_made=self.changes_made,
            errors=self.errors
        )
    
    def _apply_naming_rules(self):
        """Apply naming rules to source files."""
        print("📝 Applying naming rules...")
        
        for rule in self.naming_rules:
            for pattern in rule.file_patterns:
                for file_path in self.project_root.rglob(pattern):
                    if self._should_skip_file(file_path):
                        continue
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        content = re.sub(rule.pattern, rule.replacement, content)
                        
                        if content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            self._record_change(str(file_path), rule.pattern, rule.replacement)
                            print(f"  ✅ Applied rule '{rule.description}' to {file_path}")
                    
                    except Exception as e:
                        error_msg = f"Error applying rule '{rule.description}' to {file_path}: {e}"
                        self.errors.append(error_msg)
                        print(f"  ❌ {error_msg}")
    
    def _standardize_units(self):
        """Standardize unit naming across the codebase."""
        print("📏 Standardizing units...")
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply unit standardizations
                for old_unit, new_unit in self.unit_standardization.items():
                    # Pattern to match field assignments and references
                    patterns = [
                        rf'\b{old_unit}\b(?=\s*[=:])',  # Assignment context
                        rf'[\'\"]{old_unit}[\'\"]',      # String literal context
                        rf'\.{old_unit}\b',              # Attribute access
                    ]
                    
                    for pattern in patterns:
                        if re.search(pattern, content):
                            content = re.sub(pattern, lambda m: m.group().replace(old_unit, new_unit), content)
                
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self._record_change(str(py_file), "unit standardization", "multiple units")
                    print(f"  ✅ Standardized units in {py_file}")
            
            except Exception as e:
                error_msg = f"Error standardizing units in {py_file}: {e}"
                self.errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    def _resolve_field_duplications(self):
        """Resolve field name duplications."""
        print("🔄 Resolving field duplications...")
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Apply field mappings
                for old_field, new_field in self.field_mappings.items():
                    # Be careful to only replace in appropriate contexts
                    patterns = [
                        rf'\b{old_field}\b(?=\s*[=:])',  # Assignment
                        rf'[\'\"]{old_field}[\'\"]',      # String keys
                        rf'\.{old_field}\b',              # Attribute access
                        rf'\b{old_field}\b(?=\s*,)',      # Function parameters
                    ]
                    
                    for pattern in patterns:
                        content = re.sub(pattern, lambda m: m.group().replace(old_field, new_field), content)
                
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self._record_change(str(py_file), "field deduplication", "multiple fields")
                    print(f"  ✅ Resolved field duplications in {py_file}")
            
            except Exception as e:
                error_msg = f"Error resolving field duplications in {py_file}: {e}"
                self.errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    def _update_documentation(self):
        """Update documentation to reflect naming changes."""
        print("📚 Updating documentation...")
        
        doc_files = list(self.project_root.rglob("*.md")) + list(self.project_root.rglob("*.rst"))
        
        for doc_file in doc_files:
            if self._should_skip_file(doc_file):
                continue
            
            try:
                with open(doc_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Update function names in documentation
                content = re.sub(r'\bexport_key\(', 'compute_export_key(', content)
                content = re.sub(r'services\.cache(?!_v2)', 'services.cache_v2', content)
                
                # Update field references
                content = re.sub(r'\bfont_hanzi\b', 'hanzi_font_size_pt', content)
                content = re.sub(r'\bfont_pinyin\b', 'pinyin_font_size_pt', content)
                content = re.sub(r'\bfont_english\b', 'english_font_size_pt', content)
                
                if content != original_content:
                    with open(doc_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self._record_change(str(doc_file), "documentation update", "naming consistency")
                    print(f"  ✅ Updated documentation in {doc_file}")
            
            except Exception as e:
                error_msg = f"Error updating documentation in {doc_file}: {e}"
                self.errors.append(error_msg)
                print(f"  ❌ {error_msg}")
    
    def _validate_naming_consistency(self):
        """Validate naming consistency across the codebase."""
        print("✅ Validating naming consistency...")
        
        # Check for remaining inconsistencies
        inconsistencies = []
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for old patterns that should have been replaced
                old_patterns = [
                    r'\bexport_key\(',
                    r'\bnav_digest\b',
                    r'services\.cache(?!_v2)',
                ]
                
                for pattern in old_patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        inconsistencies.append(f"{py_file}: Found old pattern '{pattern}'")
            
            except Exception as e:
                self.errors.append(f"Error validating {py_file}: {e}")
        
        if inconsistencies:
            print("  ⚠️  Found naming inconsistencies:")
            for inconsistency in inconsistencies:
                print(f"    - {inconsistency}")
        else:
            print("  ✅ All naming conventions are consistent")
    
    def _record_change(self, file_path: str, old_pattern: str, new_pattern: str):
        """Record a change made during standardization."""
        self.changes_made.append((file_path, old_pattern, new_pattern))
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
    """Main entry point for naming standardization."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Standardize naming conventions")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    parser.add_argument("--output-dir", default="cleanup_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No files will be modified")
    
    standardizer = NamingStandardizer()
    
    if not args.dry_run:
        result = standardizer.standardize_all()
        
        # Generate report
        os.makedirs(args.output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(args.output_dir, f"naming_standardization_{timestamp}.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Naming Standardization Report\n\n")
            f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Files Modified**: {len(result.files_modified)}\n")
            f.write(f"- **Changes Made**: {len(result.changes_made)}\n")
            f.write(f"- **Errors**: {len(result.errors)}\n\n")
            
            if result.files_modified:
                f.write("## Modified Files\n\n")
                for file_path in result.files_modified:
                    f.write(f"- {file_path}\n")
                f.write("\n")
            
            if result.changes_made:
                f.write("## Changes Made\n\n")
                for file_path, old, new in result.changes_made:
                    f.write(f"- **{file_path}**: {old} → {new}\n")
                f.write("\n")
            
            if result.errors:
                f.write("## Errors\n\n")
                for error in result.errors:
                    f.write(f"- {error}\n")
        
        print(f"\n📊 Standardization complete!")
        print(f"   - Files modified: {len(result.files_modified)}")
        print(f"   - Changes made: {len(result.changes_made)}")
        print(f"   - Errors: {len(result.errors)}")
        print(f"   - Report saved: {report_file}")
    
    else:
        print("🔍 Dry run completed - use --dry-run=false to apply changes")


if __name__ == "__main__":
    main()
