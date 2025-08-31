#!/usr/bin/env python3
"""
Fix Test Mocks Script.
Removes feature flag mocks from test files and fixes indentation.
"""

import os
import re
from pathlib import Path


def fix_cache_v2_test_mocks(file_path: Path) -> bool:
    """Fix cache v2 test mocks by removing them and fixing indentation."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match: with patch('services.cache_v2.use_cache_v2', return_value=True/False):
        pattern = r"(\s*)with patch\('services\.cache_v2\.use_cache_v2', return_value=(True|False)\):\s*\n"
        
        lines = content.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Check if this line matches the pattern
            match = re.search(pattern, line)
            if match:
                base_indent = match.group(1)  # The indentation before 'with'
                return_value = match.group(2)  # True or False
                
                # Add comment about cache being always enabled
                if return_value == "True":
                    result_lines.append(f"{base_indent}# Cache v2 is always enabled - no need to mock")
                else:
                    result_lines.append(f"{base_indent}# Cache v2 is always enabled - skipping disabled test")
                    # For False cases, we might want to skip the entire test block
                    # For now, just add the comment and continue
                
                i += 1  # Skip the 'with patch' line
                
                # Process the indented block
                while i < len(lines):
                    if not lines[i].strip():  # Empty line
                        result_lines.append(lines[i])
                        i += 1
                        continue
                    
                    line_indent = len(lines[i]) - len(lines[i].lstrip())
                    base_indent_len = len(base_indent)
                    
                    # If we've reached a line that's not more indented than the base, we're done
                    if line_indent <= base_indent_len and lines[i].strip():
                        break
                    
                    # Remove one level of indentation (4 spaces) from the content
                    if line_indent > base_indent_len + 4:
                        unindented = lines[i][4:]  # Remove 4 spaces
                        result_lines.append(unindented)
                    elif line_indent > base_indent_len:
                        # This line was directly under the 'with' block
                        unindented = lines[i][4:]  # Remove 4 spaces
                        result_lines.append(unindented)
                    else:
                        result_lines.append(lines[i])
                    i += 1
            else:
                result_lines.append(line)
                i += 1
        
        new_content = '\n'.join(result_lines)
        
        if new_content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False


def fix_other_feature_flag_mocks(file_path: Path) -> bool:
    """Fix other feature flag mocks in test files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove other stable feature flag mocks
        stable_flag_patterns = [
            r"with patch\('.*\.use_ui_adapter', return_value=True\):",
            r"with patch\('.*\.use_state_service', return_value=True\):",
            r"with patch\('.*\.use_new_preview_pipeline', return_value=True\):",
            r"@patch\('.*\.use_cache_v2', return_value=True\)",
            r"@patch\('.*\.use_ui_adapter', return_value=True\)",
        ]
        
        for pattern in stable_flag_patterns:
            content = re.sub(pattern, '# Feature flag mock removed - always enabled', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error fixing other mocks in {file_path}: {e}")
        return False


def main():
    """Main entry point."""
    project_root = Path(".")
    
    # Find test files that might have feature flag mocks
    test_files = list(project_root.rglob("test_*.py"))
    
    fixed_files = []
    
    for test_file in test_files:
        print(f"Processing {test_file}...")
        
        # Fix cache v2 mocks
        if fix_cache_v2_test_mocks(test_file):
            print(f"  ✅ Fixed cache v2 mocks in {test_file}")
            fixed_files.append(str(test_file))
        
        # Fix other feature flag mocks
        if fix_other_feature_flag_mocks(test_file):
            print(f"  ✅ Fixed other feature flag mocks in {test_file}")
            if str(test_file) not in fixed_files:
                fixed_files.append(str(test_file))
    
    print(f"\n📊 Summary:")
    print(f"  - Files processed: {len(test_files)}")
    print(f"  - Files modified: {len(fixed_files)}")
    
    if fixed_files:
        print(f"\n📝 Modified files:")
        for file_path in fixed_files:
            print(f"  - {file_path}")


if __name__ == "__main__":
    main()
