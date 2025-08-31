#!/usr/bin/env python3
"""
Legacy Code Removal Script.
Systematically removes legacy code paths, fallback implementations, and deprecated functions.
"""

import os
import sys
import re
import ast
import logging
from typing import List, Dict, Set, Tuple
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class LegacyCodeRemover:
    """Removes legacy code patterns and deprecated functions."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.removed_items = []
        self.modified_files = []
        
        # Patterns to identify legacy code
        self.legacy_patterns = {
            'legacy_preview_fallbacks': [
                r'# Fall back to legacy implementation',
                r'# Legacy implementation fallback',
                r'logging\.warning\(.*V2 delegation failed.*\)',
                r'except Exception as e:\s*# Fall back to legacy',
            ],
            'deprecated_functions': [
                r'def create_page_preview_html\(',
                r'def cached_create_page_preview_html\(',
                r'def create_simple_grid_html\(',
                r'def cached_create_simple_grid_html\(',
                r'def render_sticky_wrapper_start\(',
                r'def render_sticky_wrapper_end\(',
            ],
            'feature_flag_checks': [
                r'if get_feature_flag\([\'"]preview_dataclasses_v2[\'"].*\):',
                r'get_feature_flag\([\'"]preview_dataclasses_v2[\'"].*\)',
            ],
            'legacy_imports': [
                r'from services\.cache import create_page_preview_html',
                r'from services\.cache import create_simple_grid_html',
                r'from services\.preview_types import extract_legacy_params',
            ],
            'direct_streamlit_calls': [
                r'st\.markdown\(',
                r'st\.html\(',
                r'st\.error\(',
                r'st\.warning\(',
                r'st\.info\(',
                r'st\.success\(',
                r'st\.cache_data\.clear\(\)',
            ]
        }
    
    def scan_for_legacy_code(self) -> Dict[str, List[Tuple[str, int, str]]]:
        """Scan project for legacy code patterns."""
        findings = {pattern_type: [] for pattern_type in self.legacy_patterns}
        
        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for pattern_type, patterns in self.legacy_patterns.items():
                    for pattern in patterns:
                        for line_num, line in enumerate(lines, 1):
                            if re.search(pattern, line):
                                findings[pattern_type].append((str(py_file), line_num, line.strip()))
            
            except Exception as e:
                logging.warning(f"Error scanning {py_file}: {e}")
        
        return findings
    
    def remove_legacy_preview_functions(self) -> bool:
        """Remove legacy preview functions that are fully delegated to v2."""
        cache_file = self.project_root / "services" / "cache.py"
        
        if not cache_file.exists():
            return False
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove legacy fallback implementations
            # Keep the function signatures but make them pure delegation
            
            # Pattern for create_page_preview_html
            page_preview_pattern = r'(def create_page_preview_html\(.*?\):.*?""".*?""")(.*?)(?=def|\Z)'
            
            def replace_page_preview(match):
                signature_and_docstring = match.group(1)
                return signature_and_docstring + '''
    import warnings
    warnings.warn(
        "create_page_preview_html() is deprecated. Use create_page_preview_html_v2() with dataclasses instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Always use v2 implementation
    from services.cache_v2 import create_page_preview_html_v2
    from services.preview_types import convert_legacy_params_to_preview_params

    # Convert legacy parameters to dataclasses
    preview_params = convert_legacy_params_to_preview_params(
        card_size, gap, margin, page_size,
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '📄 完整页面',
        layout_rows, layout_cols, auto_fill
    )

    # Delegate to v2 implementation
    return create_page_preview_html_v2(
        cards, page_num,
        preview_params.layout,
        preview_params.typography,
        preview_params.visual
    )


'''
            
            content = re.sub(page_preview_pattern, replace_page_preview, content, flags=re.DOTALL)
            
            # Similar pattern for create_simple_grid_html
            grid_pattern = r'(def create_simple_grid_html\(.*?\):.*?""".*?""")(.*?)(?=def|\Z)'
            
            def replace_grid_preview(match):
                signature_and_docstring = match.group(1)
                return signature_and_docstring + '''
    import warnings
    warnings.warn(
        "create_simple_grid_html() is deprecated. Use create_simple_grid_html_v2() with dataclasses instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Always use v2 implementation
    from services.cache_v2 import create_simple_grid_html_v2
    from services.preview_types import convert_legacy_params_to_preview_params

    # Convert legacy parameters to dataclasses
    preview_params = convert_legacy_params_to_preview_params(
        card_size, 0.5, 1.0, 'A4',  # gap and margin defaults for simple grid
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '🔲 简单网格',
        layout_rows, layout_cols, auto_fill
    )

    # Delegate to v2 implementation
    return create_simple_grid_html_v2(
        cards,
        preview_params.layout,
        preview_params.typography,
        preview_params.visual
    )


'''
            
            content = re.sub(grid_pattern, replace_grid_preview, content, flags=re.DOTALL)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified_files.append(str(cache_file))
            self.removed_items.append("Legacy preview function fallbacks")
            return True
            
        except Exception as e:
            logging.error(f"Error removing legacy preview functions: {e}")
            return False
    
    def remove_legacy_fallbacks_in_controllers(self) -> bool:
        """Remove legacy fallbacks in preview controllers."""
        controller_file = self.project_root / "ui" / "preview_controller.py"
        
        if not controller_file.exists():
            return False
        
        try:
            with open(controller_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove legacy fallback blocks
            patterns_to_remove = [
                r'except Exception as e:\s*# Fall back to legacy implementation.*?return create_page_preview_html\(.*?\)',
                r'# Legacy implementation fallback.*?return create_simple_grid_html\(.*?\)',
            ]
            
            for pattern in patterns_to_remove:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            # Remove legacy imports
            legacy_imports = [
                r'from services\.cache import create_page_preview_html\n',
                r'from services\.cache import create_simple_grid_html\n',
                r'from services\.preview_types import extract_legacy_params\n',
            ]
            
            for import_pattern in legacy_imports:
                content = re.sub(import_pattern, '', content)
            
            with open(controller_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified_files.append(str(controller_file))
            self.removed_items.append("Legacy fallbacks in preview controller")
            return True
            
        except Exception as e:
            logging.error(f"Error removing legacy fallbacks in controller: {e}")
            return False
    
    def remove_deprecated_sticky_functions(self) -> bool:
        """Remove deprecated sticky wrapper functions."""
        styles_file = self.project_root / "ui" / "styles.py"
        
        if not styles_file.exists():
            return False
        
        try:
            with open(styles_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove deprecated functions
            deprecated_functions = [
                r'def render_sticky_wrapper_start\(\).*?st\.markdown\(.*?\)',
                r'def render_sticky_wrapper_end\(\).*?st\.markdown\(.*?\)',
            ]
            
            for func_pattern in deprecated_functions:
                content = re.sub(func_pattern, '', content, flags=re.DOTALL)
            
            with open(styles_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified_files.append(str(styles_file))
            self.removed_items.append("Deprecated sticky wrapper functions")
            return True
            
        except Exception as e:
            logging.error(f"Error removing deprecated sticky functions: {e}")
            return False
    
    def remove_legacy_tests(self) -> bool:
        """Remove or update legacy test files."""
        legacy_test_files = [
            "tests/unit/test_legacy_delegation.py",
            "tests/unit/test_services_cache_legacy.py",
        ]
        
        for test_file in legacy_test_files:
            test_path = self.project_root / test_file
            if test_path.exists():
                # Instead of deleting, mark as deprecated
                try:
                    with open(test_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Add deprecation notice at the top
                    deprecation_notice = '''"""
DEPRECATED: This test file is deprecated as legacy delegation is no longer needed.
The v2 implementation is now the only implementation.
This file is kept for historical reference but tests may be outdated.
"""

'''
                    
                    if not content.startswith('"""'):
                        content = deprecation_notice + content
                    
                    with open(test_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    self.modified_files.append(str(test_path))
                    self.removed_items.append(f"Deprecated legacy test: {test_file}")
                    
                except Exception as e:
                    logging.error(f"Error updating legacy test {test_file}: {e}")
        
        return True
    
    def remove_feature_flag_checks(self) -> bool:
        """Remove feature flag checks for stable features."""
        stable_flags = [
            'preview_dataclasses_v2',
            'ui_adapter',
            'adapted_inputs',
            'adapted_preview',
        ]
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                modified = False
                for flag in stable_flags:
                    # Remove feature flag checks that are always True
                    pattern = rf'if get_feature_flag\([\'\"]{flag}[\'\"]\s*,\s*[^)]*\):'
                    if re.search(pattern, content):
                        # For now, just log - actual removal needs careful analysis
                        logging.info(f"Found stable feature flag check in {py_file}: {flag}")
                
            except Exception as e:
                logging.warning(f"Error checking feature flags in {py_file}: {e}")
        
        return True
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped during scanning."""
        skip_patterns = [
            "__pycache__",
            ".git",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            "build",
            "dist",
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)
    
    def generate_removal_report(self) -> str:
        """Generate a report of removed legacy code."""
        from datetime import datetime
        report = "# Legacy Code Removal Report\n\n"
        report += f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += "## Removed Items\n\n"
        for item in self.removed_items:
            report += f"- {item}\n"
        
        report += "\n## Modified Files\n\n"
        for file_path in self.modified_files:
            report += f"- {file_path}\n"
        
        report += "\n## Summary\n\n"
        report += f"- **Total items removed**: {len(self.removed_items)}\n"
        report += f"- **Files modified**: {len(self.modified_files)}\n"
        
        return report


def main():
    """Main entry point for legacy code removal."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Remove legacy code paths")
    parser.add_argument("--scan-only", action="store_true", help="Only scan for legacy code, don't remove")
    parser.add_argument("--output-dir", default="cleanup_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    remover = LegacyCodeRemover()
    
    print("🔍 Scanning for legacy code patterns...")
    findings = remover.scan_for_legacy_code()
    
    # Print findings
    for pattern_type, items in findings.items():
        if items:
            print(f"\n📋 {pattern_type.replace('_', ' ').title()}:")
            for file_path, line_num, line in items[:10]:  # Limit to first 10
                print(f"  {file_path}:{line_num} - {line}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")
    
    if args.scan_only:
        print("\n✅ Scan complete. Use --scan-only=false to perform removal.")
        return
    
    print("\n🧹 Starting legacy code removal...")
    
    # Remove legacy code
    success_count = 0
    
    if remover.remove_legacy_preview_functions():
        print("✅ Removed legacy preview function fallbacks")
        success_count += 1
    
    if remover.remove_legacy_fallbacks_in_controllers():
        print("✅ Removed legacy fallbacks in controllers")
        success_count += 1
    
    if remover.remove_deprecated_sticky_functions():
        print("✅ Removed deprecated sticky wrapper functions")
        success_count += 1
    
    if remover.remove_legacy_tests():
        print("✅ Updated legacy test files")
        success_count += 1
    
    if remover.remove_feature_flag_checks():
        print("✅ Analyzed feature flag usage")
        success_count += 1
    
    # Generate report
    os.makedirs(args.output_dir, exist_ok=True)
    report = remover.generate_removal_report()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(args.output_dir, f"legacy_removal_report_{timestamp}.md")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📊 Removal complete!")
    print(f"   - Operations completed: {success_count}")
    print(f"   - Items removed: {len(remover.removed_items)}")
    print(f"   - Files modified: {len(remover.modified_files)}")
    print(f"   - Report saved: {report_file}")


if __name__ == "__main__":
    main()
