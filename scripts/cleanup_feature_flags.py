#!/usr/bin/env python3
"""
Feature Flag Cleanup Script.
Removes stable feature flags, updates configurations, and documents remaining flags.
"""

import os
import sys
import re
import ast
import logging
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class FeatureFlagUsage:
    """Information about feature flag usage."""
    file_path: str
    line_number: int
    flag_name: str
    usage_type: str  # 'conditional', 'assignment', 'function_call'
    context: str  # The line of code
    default_value: Optional[str] = None


@dataclass
class FlagCleanupResult:
    """Result of flag cleanup operation."""
    flag_name: str
    files_modified: List[str]
    usages_removed: int
    errors: List[str]


class FeatureFlagCleaner:
    """Cleans up stable feature flags from the codebase."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.modified_files = []
        self.cleanup_results = []
        
        # Define stable flags that should be removed
        self.stable_flags = {
            # Completed UI refactor flags - always True
            'preview_dataclasses_v2': True,
            'ui_adapter': True,
            'adapted_inputs': True,
            'adapted_preview': True,
            'adapted_editor': True,
            'adapted_export': True,
            'adapted_sidebar': True,
            'adapted_options': True,
            'new_preview_pipeline': True,
            'state_service': True,
            'cache_v2': True,
            'shared_render_core': True,
            'unified_sections': True,
            
            # Completed feature flags - always False (remove code)
            'clean_ui_components': False,  # If this was experimental and not used
        }
        
        # Flags that should remain (for debugging, operations, future features)
        self.keep_flags = {
            'persistence',  # Has kill-switch functionality
            'debug_panel',  # Development flag
            'ENABLE_DIGEST_DEBUG',  # Development flag
            'storage_debug_panel',  # Development flag
            'telemetry_enabled',  # Operational flag
            'telemetry_debug',  # Operational flag
        }
    
    def scan_feature_flag_usage(self) -> List[FeatureFlagUsage]:
        """Scan codebase for all feature flag usage."""
        usages = []
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Look for get_feature_flag calls
                    flag_usage = self._extract_flag_usage(line, str(py_file), line_num)
                    if flag_usage:
                        usages.append(flag_usage)
            
            except Exception as e:
                logging.warning(f"Error scanning {py_file}: {e}")
        
        return usages
    
    def cleanup_stable_flags(self) -> List[FlagCleanupResult]:
        """Remove stable feature flags from the codebase."""
        results = []
        
        for flag_name, default_value in self.stable_flags.items():
            result = self._cleanup_single_flag(flag_name, default_value)
            results.append(result)
            self.cleanup_results.append(result)
        
        return results
    
    def update_default_flags(self) -> bool:
        """Update DEFAULT_FLAGS in core/feature_flags.py."""
        flags_file = self.project_root / "core" / "feature_flags.py"
        
        if not flags_file.exists():
            return False
        
        try:
            with open(flags_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove stable flags from DEFAULT_FLAGS
            for flag_name in self.stable_flags.keys():
                # Pattern to match flag definition in DEFAULT_FLAGS
                pattern = rf"^\s*['\"]?{re.escape(flag_name)}['\"]?\s*:\s*[^,\n]+,?\s*#?.*$"
                content = re.sub(pattern, '', content, flags=re.MULTILINE)
            
            # Clean up empty lines in DEFAULT_FLAGS
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            
            with open(flags_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.modified_files.append(str(flags_file))
            return True
            
        except Exception as e:
            logging.error(f"Error updating DEFAULT_FLAGS: {e}")
            return False
    
    def remove_convenience_functions(self) -> bool:
        """Remove convenience functions for stable flags."""
        flags_file = self.project_root / "core" / "feature_flags.py"
        
        if not flags_file.exists():
            return False
        
        try:
            with open(flags_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove convenience functions for stable flags
            stable_function_patterns = [
                r'def use_new_preview_pipeline\(\).*?return.*?\n\n',
                r'def use_ui_adapter\(\).*?return.*?\n\n',
                r'def use_state_service\(\).*?return.*?\n\n',
                r'def use_cache_v2\(\).*?return.*?\n\n',
            ]
            
            for pattern in stable_function_patterns:
                content = re.sub(pattern, '', content, flags=re.DOTALL)
            
            with open(flags_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            logging.error(f"Error removing convenience functions: {e}")
            return False
    
    def generate_flag_documentation(self) -> str:
        """Generate documentation for remaining feature flags."""
        from datetime import datetime
        doc = "# Feature Flags Documentation\n\n"
        doc += f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        doc += "## Removed Flags\n\n"
        doc += "The following flags were removed as they represent completed, stable features:\n\n"
        
        for flag_name, default_value in self.stable_flags.items():
            status = "always enabled" if default_value else "always disabled"
            doc += f"- `{flag_name}` - {status}\n"
        
        doc += "\n## Remaining Flags\n\n"
        doc += "The following flags remain active for operational or development purposes:\n\n"
        
        for flag_name in self.keep_flags:
            doc += f"- `{flag_name}` - Active operational/development flag\n"
        
        doc += "\n## Usage Guidelines\n\n"
        doc += "- **Development flags** (`debug_panel`, `storage_debug_panel`) - For debugging and development\n"
        doc += "- **Operational flags** (`persistence`, `telemetry_enabled`) - For runtime configuration\n"
        doc += "- **Future flags** - For gradual rollout of new features\n"
        
        return doc
    
    def _cleanup_single_flag(self, flag_name: str, default_value: bool) -> FlagCleanupResult:
        """Clean up a single feature flag."""
        result = FlagCleanupResult(
            flag_name=flag_name,
            files_modified=[],
            usages_removed=0,
            errors=[]
        )
        
        for py_file in self.project_root.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                
                # Remove simple conditional checks
                if default_value:
                    # Remove if get_feature_flag('flag', True): and keep the code
                    content = self._remove_true_flag_conditionals(content, flag_name)
                else:
                    # Remove if get_feature_flag('flag', False): and remove the code
                    content = self._remove_false_flag_conditionals(content, flag_name)
                
                # Remove direct function calls that just return the flag
                content = self._remove_flag_function_calls(content, flag_name)
                
                if content != original_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    result.files_modified.append(str(py_file))
                    result.usages_removed += 1
                    
                    if str(py_file) not in self.modified_files:
                        self.modified_files.append(str(py_file))
            
            except Exception as e:
                error_msg = f"Error processing {py_file}: {e}"
                result.errors.append(error_msg)
                logging.error(error_msg)
        
        return result
    
    def _remove_true_flag_conditionals(self, content: str, flag_name: str) -> str:
        """Remove conditionals for flags that are always True."""
        # Pattern for: if get_feature_flag('flag', True):
        pattern = rf'if\s+get_feature_flag\([\'\"]{re.escape(flag_name)}[\'\"]\s*,\s*True\s*\):\s*\n'
        
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if re.search(pattern, line):
                # Found a conditional - extract the indented block
                base_indent = len(line) - len(line.lstrip())
                i += 1  # Skip the if line
                
                # Collect the indented block
                while i < len(lines):
                    if not lines[i].strip():  # Empty line
                        result_lines.append(lines[i])
                        i += 1
                        continue
                    
                    line_indent = len(lines[i]) - len(lines[i].lstrip())
                    if line_indent <= base_indent and lines[i].strip():
                        # End of block
                        break
                    
                    # Remove one level of indentation and add to result
                    if line_indent > base_indent:
                        unindented = lines[i][4:]  # Remove 4 spaces
                        result_lines.append(unindented)
                    else:
                        result_lines.append(lines[i])
                    i += 1
            else:
                result_lines.append(line)
                i += 1
        
        return '\n'.join(result_lines)
    
    def _remove_false_flag_conditionals(self, content: str, flag_name: str) -> str:
        """Remove conditionals for flags that are always False."""
        # Pattern for: if get_feature_flag('flag', False):
        pattern = rf'if\s+get_feature_flag\([\'\"]{re.escape(flag_name)}[\'\"]\s*,\s*False\s*\):\s*\n'
        
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            if re.search(pattern, line):
                # Found a conditional - skip the entire block
                base_indent = len(line) - len(line.lstrip())
                i += 1  # Skip the if line
                
                # Skip the indented block
                while i < len(lines):
                    if not lines[i].strip():  # Empty line
                        i += 1
                        continue
                    
                    line_indent = len(lines[i]) - len(lines[i].lstrip())
                    if line_indent <= base_indent and lines[i].strip():
                        # End of block
                        break
                    i += 1
            else:
                result_lines.append(line)
                i += 1
        
        return '\n'.join(result_lines)
    
    def _remove_flag_function_calls(self, content: str, flag_name: str) -> str:
        """Remove direct function calls that return the flag value."""
        # Remove lines like: return get_feature_flag('flag', True)
        pattern = rf'return\s+get_feature_flag\([\'\"]{re.escape(flag_name)}[\'\"]\s*,\s*[^)]+\)'
        
        if flag_name in self.stable_flags and self.stable_flags[flag_name]:
            # Replace with return True
            content = re.sub(pattern, 'return True', content)
        else:
            # Replace with return False
            content = re.sub(pattern, 'return False', content)
        
        return content
    
    def _extract_flag_usage(self, line: str, file_path: str, line_num: int) -> Optional[FeatureFlagUsage]:
        """Extract feature flag usage from a line of code."""
        # Pattern to match get_feature_flag calls
        pattern = r'get_feature_flag\([\'\"](.*?)[\'\"]\s*(?:,\s*([^)]+))?\)'
        match = re.search(pattern, line)
        
        if match:
            flag_name = match.group(1)
            default_value = match.group(2) if match.group(2) else None
            
            # Determine usage type
            if line.strip().startswith('if '):
                usage_type = 'conditional'
            elif '=' in line:
                usage_type = 'assignment'
            else:
                usage_type = 'function_call'
            
            return FeatureFlagUsage(
                file_path=file_path,
                line_number=line_num,
                flag_name=flag_name,
                usage_type=usage_type,
                context=line.strip(),
                default_value=default_value
            )
        
        return None
    
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
        ]
        
        return any(pattern in str(file_path) for pattern in skip_patterns)


def main():
    """Main entry point for feature flag cleanup."""
    import argparse
    from datetime import datetime
    
    parser = argparse.ArgumentParser(description="Clean up stable feature flags")
    parser.add_argument("--scan-only", action="store_true", help="Only scan for flag usage, don't modify")
    parser.add_argument("--output-dir", default="cleanup_reports", help="Output directory for reports")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    cleaner = FeatureFlagCleaner()
    
    print("🔍 Scanning for feature flag usage...")
    usages = cleaner.scan_feature_flag_usage()
    
    # Group usages by flag
    flag_usage_counts = {}
    for usage in usages:
        flag_usage_counts[usage.flag_name] = flag_usage_counts.get(usage.flag_name, 0) + 1
    
    print(f"\n📊 Found {len(usages)} feature flag usages across {len(flag_usage_counts)} flags:")
    for flag_name, count in sorted(flag_usage_counts.items()):
        status = "🟢 STABLE" if flag_name in cleaner.stable_flags else "🔵 KEEP"
        print(f"  {status} {flag_name}: {count} usages")
    
    if args.scan_only:
        print("\n✅ Scan complete. Use --scan-only=false to perform cleanup.")
        return
    
    print("\n🧹 Starting feature flag cleanup...")
    
    # Clean up stable flags
    results = cleaner.cleanup_stable_flags()
    
    # Update configurations
    if cleaner.update_default_flags():
        print("✅ Updated DEFAULT_FLAGS configuration")
    
    if cleaner.remove_convenience_functions():
        print("✅ Removed convenience functions")
    
    # Generate documentation
    os.makedirs(args.output_dir, exist_ok=True)
    doc = cleaner.generate_flag_documentation()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    doc_file = os.path.join(args.output_dir, f"feature_flags_cleanup_{timestamp}.md")
    
    with open(doc_file, 'w', encoding='utf-8') as f:
        f.write(doc)
    
    # Summary
    total_files = len(cleaner.modified_files)
    total_usages = sum(r.usages_removed for r in results)
    total_errors = sum(len(r.errors) for r in results)
    
    print(f"\n📊 Cleanup complete!")
    print(f"   - Flags cleaned: {len(cleaner.stable_flags)}")
    print(f"   - Files modified: {total_files}")
    print(f"   - Usages removed: {total_usages}")
    print(f"   - Errors: {total_errors}")
    print(f"   - Documentation: {doc_file}")


if __name__ == "__main__":
    main()
