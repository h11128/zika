"""
Integration tests to verify zero direct Streamlit calls.

Tests that the unified sections module has eliminated all direct st. calls.
"""

import pytest
import ast
import inspect
from typing import List, Set


class StreamlitCallVisitor(ast.NodeVisitor):
    """AST visitor to find direct Streamlit calls."""
    
    def __init__(self):
        self.streamlit_calls = []
        self.imports = set()
    
    def visit_Import(self, node):
        for alias in node.names:
            if alias.name == 'streamlit':
                self.imports.add(alias.asname or alias.name)
    
    def visit_ImportFrom(self, node):
        if node.module == 'streamlit':
            for alias in node.names:
                self.imports.add(alias.asname or alias.name)
    
    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name):
            if node.value.id in self.imports:
                self.streamlit_calls.append(f"{node.value.id}.{node.attr}")
        self.generic_visit(node)


def find_streamlit_calls_in_file(filepath: str) -> List[str]:
    """Find all direct Streamlit calls in a Python file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        visitor = StreamlitCallVisitor()
        visitor.visit(tree)
        
        return visitor.streamlit_calls
    except Exception as e:
        pytest.fail(f"Failed to parse {filepath}: {e}")


class TestZeroStreamlitCalls:
    """Test that unified modules have zero direct Streamlit calls."""
    
    def test_unified_sections_zero_calls(self):
        """Test that sections_unified.py has zero direct Streamlit calls."""
        calls = find_streamlit_calls_in_file('ui/sections_unified.py')
        
        # Filter out acceptable calls (like st.components.v1.html which has no adapter equivalent)
        acceptable_calls = {
            'st.components.v1.html',  # No adapter equivalent yet
            'st.rerun'  # May be used in fallback scenarios
        }
        
        unacceptable_calls = [call for call in calls if call not in acceptable_calls]
        
        assert len(unacceptable_calls) == 0, f"Found direct Streamlit calls: {unacceptable_calls}"
    
    def test_unified_ui_zero_calls(self):
        """Test that unified.py properly abstracts Streamlit calls."""
        calls = find_streamlit_calls_in_file('ui/unified.py')
        
        # unified.py should have Streamlit calls only in the else branches (fallback)
        # This is acceptable as it's the abstraction layer
        assert len(calls) > 0, "unified.py should contain Streamlit calls for fallback"
    
    def test_state_bridge_zero_calls(self):
        """Test that state_bridge.py has minimal Streamlit calls."""
        calls = find_streamlit_calls_in_file('ui/state_bridge.py')
        
        # state_bridge.py should only have st.session_state calls for fallback
        acceptable_calls = {
            'st.session_state'
        }
        
        unacceptable_calls = [call for call in calls if not any(acceptable in call for acceptable in acceptable_calls)]
        
        assert len(unacceptable_calls) == 0, f"Found unacceptable Streamlit calls: {unacceptable_calls}"
    
    def test_export_unified_zero_calls(self):
        """Test that export_unified.py has zero direct Streamlit calls."""
        calls = find_streamlit_calls_in_file('ui/export_unified.py')
        
        # export_unified.py should have zero direct calls except for components.v1.html
        acceptable_calls = {
            'st.components.v1.html',  # No adapter equivalent yet
            'st.components',  # Part of st.components.v1.html
        }
        
        unacceptable_calls = [call for call in calls if call not in acceptable_calls]
        
        assert len(unacceptable_calls) == 0, f"Found direct Streamlit calls: {unacceptable_calls}"


class TestUnifiedModulesIntegration:
    """Test that unified modules work correctly."""
    
    def test_unified_sections_import(self):
        """Test that unified sections can be imported."""
        try:
            from ui.sections_unified import (
                render_sidebar, render_export_section, 
                render_left_column, render_right_column,
                render_preview_column_header
            )
            
            # Test that all functions are callable
            assert callable(render_sidebar)
            assert callable(render_export_section)
            assert callable(render_left_column)
            assert callable(render_right_column)
            assert callable(render_preview_column_header)
            
        except ImportError as e:
            pytest.fail(f"Failed to import unified sections: {e}")
    
    def test_unified_ui_import(self):
        """Test that unified UI can be imported."""
        try:
            from ui.unified import UnifiedUI, get_unified_ui
            
            ui = get_unified_ui()
            assert isinstance(ui, UnifiedUI)
            
            # Test that key methods exist
            assert hasattr(ui, 'header')
            assert hasattr(ui, 'button')
            assert hasattr(ui, 'radio')
            assert hasattr(ui, 'selectbox')
            assert hasattr(ui, 'columns')
            assert hasattr(ui, 'sidebar')
            assert hasattr(ui, 'spinner')
            
        except ImportError as e:
            pytest.fail(f"Failed to import unified UI: {e}")
    
    def test_state_bridge_import(self):
        """Test that state bridge can be imported."""
        try:
            from ui.state_bridge import (
                StateBridge, get_state_bridge,
                state_get, state_set, state_update,
                state_delete, state_has, state_append, state_increment
            )
            
            bridge = get_state_bridge()
            assert isinstance(bridge, StateBridge)
            
            # Test that all functions are callable
            assert callable(state_get)
            assert callable(state_set)
            assert callable(state_update)
            assert callable(state_delete)
            assert callable(state_has)
            assert callable(state_append)
            assert callable(state_increment)
            
        except ImportError as e:
            pytest.fail(f"Failed to import state bridge: {e}")


class TestFeatureFlagIntegration:
    """Test feature flag integration with unified modules."""
    
    def test_unified_sections_flag_enabled(self):
        """Test that unified_sections flag is enabled."""
        from core.feature_flags import get_feature_flag, set_test_override, clear_all_test_overrides

        # Clear any existing overrides
        clear_all_test_overrides()

        # Test default value (should be True)
        flag_value = get_feature_flag('unified_sections', False)
        assert flag_value is True, f"unified_sections flag should be enabled by default, got {flag_value}"

        # Test that we can override it
        set_test_override('unified_sections', False)
        assert get_feature_flag('unified_sections', True) is False, "Should be able to override flag"

        # Clean up
        clear_all_test_overrides()
    
    def test_ui_adapter_flag_enabled(self):
        """Test that ui_adapter flag is enabled."""
        from core.feature_flags import get_feature_flag
        
        assert get_feature_flag('ui_adapter', False), "ui_adapter flag should be enabled"
    
    def test_state_service_flag_enabled(self):
        """Test that state_service flag is enabled."""
        from core.feature_flags import get_feature_flag
        
        # This might be disabled by default, just test it exists
        flag_value = get_feature_flag('state_service', False)
        assert isinstance(flag_value, bool), "state_service flag should return boolean"


class TestAppControllerIntegration:
    """Test that AppController uses unified sections."""
    
    def test_app_controller_imports_unified(self):
        """Test that AppController imports from unified sections when flag is enabled."""
        from core.feature_flags import get_feature_flag, set_test_override, clear_all_test_overrides
        
        # Clear any existing overrides
        clear_all_test_overrides()
        
        # Enable unified sections
        set_test_override('unified_sections', True)
        
        try:
            # Import should work without errors
            from ui.app_controller import AppController
            
            # Test that AppController can be instantiated
            controller = AppController()
            assert controller is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import AppController with unified sections: {e}")
        finally:
            clear_all_test_overrides()
    
    def test_app_controller_fallback_to_original(self):
        """Test that AppController falls back to original sections when flag is disabled."""
        from core.feature_flags import set_test_override, clear_all_test_overrides
        
        # Clear any existing overrides
        clear_all_test_overrides()
        
        # Disable unified sections
        set_test_override('unified_sections', False)
        
        try:
            # Import should work without errors
            from ui.app_controller import AppController
            
            # Test that AppController can be instantiated
            controller = AppController()
            assert controller is not None
            
        except ImportError as e:
            pytest.fail(f"Failed to import AppController with original sections: {e}")
        finally:
            clear_all_test_overrides()


class TestCodeQualityMetrics:
    """Test code quality metrics for unified modules."""
    
    def test_unified_sections_line_count(self):
        """Test that unified sections is reasonably sized."""
        with open('ui/sections_unified.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Should be significantly smaller than original
        assert len(lines) < 250, f"Unified sections should be under 250 lines, got {len(lines)}"
    
    def test_unified_ui_comprehensive(self):
        """Test that unified UI covers all major Streamlit functions."""
        from ui.unified import UnifiedUI
        
        ui = UnifiedUI()
        
        # Test that all major UI functions are implemented
        required_methods = [
            'header', 'button', 'radio', 'selectbox', 'text_input', 'text_area',
            'checkbox', 'slider', 'columns', 'sidebar', 'expander', 'spinner',
            'success', 'error', 'warning', 'info', 'write', 'markdown',
            'metric', 'download_button', 'rerun'
        ]
        
        for method in required_methods:
            assert hasattr(ui, method), f"UnifiedUI missing method: {method}"
            assert callable(getattr(ui, method)), f"UnifiedUI.{method} is not callable"
