"""
Test error boundaries and fallback UI components.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st

from ui.error_boundaries import (
    with_error_boundary, 
    with_smart_error_boundary,
    get_fallback_ui_for_component,
    render_fallback_input,
    render_fallback_options,
    render_fallback_editor,
    render_fallback_sidebar,
    render_fallback_debug,
    render_fallback_preview,
    render_fallback_export,
    render_fallback_navigation,
    render_fallback_components
)


class TestErrorBoundaries:
    """Test error boundary decorators and functionality."""
    
    def test_with_error_boundary_success(self, monkeypatch):
        """Test error boundary with successful function execution."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_error_boundary("test_component")
        def successful_function():
            return "success"
        
        result = successful_function()
        assert result == "success"
        mock_st.error.assert_not_called()
    
    def test_with_error_boundary_exception(self, monkeypatch):
        """Test error boundary with exception handling."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_error_boundary("test_component")
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result is None
        mock_st.error.assert_called_once()
        error_call = mock_st.error.call_args[0][0]
        assert "test_component" in error_call
        assert "Test error" in error_call
    
    def test_with_error_boundary_with_fallback(self, monkeypatch):
        """Test error boundary with fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        fallback_called = False
        def fallback_ui():
            nonlocal fallback_called
            fallback_called = True
            return "fallback_result"
        
        @with_error_boundary("test_component", fallback_ui)
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert fallback_called
        mock_st.error.assert_called_once()
    
    def test_with_error_boundary_fallback_exception(self, monkeypatch):
        """Test error boundary when fallback UI also fails."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        def failing_fallback():
            raise RuntimeError("Fallback error")
        
        @with_error_boundary("test_component", failing_fallback)
        def failing_function():
            raise ValueError("Test error")
        
        result = failing_function()
        assert result is None
        assert mock_st.error.call_count == 2  # Original error + fallback error


class TestFallbackUIComponents:
    """Test fallback UI component functions."""
    
    def test_render_fallback_input(self, monkeypatch):
        """Test input fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_input()
        
        mock_st.error.assert_called_once_with("输入组件加载失败")
        mock_st.info.assert_called_once()
        mock_st.text_area.assert_called_once()
    
    def test_render_fallback_options(self, monkeypatch):
        """Test options fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_options()
        
        mock_st.error.assert_called_once_with("选项组件加载失败")
        mock_st.info.assert_called_once()
        mock_st.button.assert_called_once()
    
    def test_render_fallback_editor(self, monkeypatch):
        """Test editor fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_editor()
        
        mock_st.error.assert_called_once_with("编辑器组件加载失败")
        mock_st.info.assert_called_once()
        mock_st.button.assert_called_once()
    
    def test_render_fallback_sidebar(self, monkeypatch):
        """Test sidebar fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_sidebar()
        
        mock_st.error.assert_called_once_with("侧边栏组件加载失败")
        mock_st.info.assert_called_once()
    
    def test_render_fallback_debug(self, monkeypatch):
        """Test debug fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_debug()
        
        mock_st.error.assert_called_once_with("调试面板加载失败")
        mock_st.info.assert_called_once()
    
    def test_render_fallback_preview(self, monkeypatch):
        """Test preview fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_preview()
        
        mock_st.error.assert_called_once_with("预览渲染失败，请检查参数设置")
        mock_st.info.assert_called_once()
    
    def test_render_fallback_export(self, monkeypatch):
        """Test export fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_export()
        
        mock_st.error.assert_called_once_with("导出功能暂时不可用")
        mock_st.info.assert_called_once()
    
    def test_render_fallback_navigation(self, monkeypatch):
        """Test navigation fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_navigation()
        
        mock_st.error.assert_called_once_with("导航组件加载失败")
        mock_st.button.assert_called_once()
    
    def test_render_fallback_components(self, monkeypatch):
        """Test general components fallback UI."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        render_fallback_components()
        
        mock_st.error.assert_called_once_with("组件加载失败")
        mock_st.info.assert_called_once()
        mock_st.button.assert_called_once()


class TestSmartErrorBoundary:
    """Test smart error boundary functionality."""
    
    def test_get_fallback_ui_for_component_input(self):
        """Test fallback UI selection for input components."""
        fallback = get_fallback_ui_for_component("input_section")
        assert fallback == render_fallback_input
    
    def test_get_fallback_ui_for_component_options(self):
        """Test fallback UI selection for options components."""
        fallback = get_fallback_ui_for_component("options_panel")
        assert fallback == render_fallback_options
    
    def test_get_fallback_ui_for_component_editor(self):
        """Test fallback UI selection for editor components."""
        fallback = get_fallback_ui_for_component("card_editor")
        assert fallback == render_fallback_editor
    
    def test_get_fallback_ui_for_component_sidebar(self):
        """Test fallback UI selection for sidebar components."""
        fallback = get_fallback_ui_for_component("sidebar_header")
        assert fallback == render_fallback_sidebar
    
    def test_get_fallback_ui_for_component_debug(self):
        """Test fallback UI selection for debug components."""
        fallback = get_fallback_ui_for_component("debug_panel")
        assert fallback == render_fallback_debug
    
    def test_get_fallback_ui_for_component_preview(self):
        """Test fallback UI selection for preview components."""
        fallback = get_fallback_ui_for_component("preview_section")
        assert fallback == render_fallback_preview
    
    def test_get_fallback_ui_for_component_export(self):
        """Test fallback UI selection for export components."""
        fallback = get_fallback_ui_for_component("export_buttons")
        assert fallback == render_fallback_export
    
    def test_get_fallback_ui_for_component_navigation(self):
        """Test fallback UI selection for navigation components."""
        fallback = get_fallback_ui_for_component("page_navigation")
        assert fallback == render_fallback_navigation
    
    def test_get_fallback_ui_for_component_default(self):
        """Test fallback UI selection for unknown components."""
        fallback = get_fallback_ui_for_component("unknown_component")
        assert fallback == render_fallback_components
    
    def test_with_smart_error_boundary(self, monkeypatch):
        """Test smart error boundary decorator."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_smart_error_boundary("input_test")
        def failing_input_function():
            raise ValueError("Input error")
        
        result = failing_input_function()
        assert result is None
        
        # Should call error and then input fallback UI
        mock_st.error.assert_called()
        mock_st.text_area.assert_called()  # From input fallback


class TestErrorBoundaryIntegration:
    """Test error boundary integration with real components."""
    
    def test_error_boundary_preserves_function_metadata(self):
        """Test that error boundary preserves function metadata."""
        @with_error_boundary("test")
        def test_function():
            """Test function docstring."""
            return "test"
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test function docstring."
    
    def test_error_boundary_with_args_kwargs(self, monkeypatch):
        """Test error boundary with function arguments."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_error_boundary("test")
        def function_with_args(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        result = function_with_args("a", "b", kwarg1="c")
        assert result == "a-b-c"
        mock_st.error.assert_not_called()
    
    def test_error_boundary_exception_with_args(self, monkeypatch):
        """Test error boundary exception handling with arguments."""
        mock_st = Mock()
        monkeypatch.setattr('ui.error_boundaries.st', mock_st)
        
        @with_error_boundary("test")
        def failing_function_with_args(arg1, arg2):
            raise ValueError(f"Error with {arg1} and {arg2}")
        
        result = failing_function_with_args("x", "y")
        assert result is None
        mock_st.error.assert_called_once()
