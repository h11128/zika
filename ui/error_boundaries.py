"""
Error boundaries for the UI refactor.
Provides error handling decorators and fallback UI components.
"""

import functools
import streamlit as st
from typing import Callable, Any, Optional


def with_error_boundary(component_name: str, fallback_ui: Optional[Callable] = None):
    """
    Decorator to wrap UI components with error boundaries.
    
    Args:
        component_name: Name of the component for logging
        fallback_ui: Optional fallback UI function to call on error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Log error
                st.error(f"组件 {component_name} 发生错误: {str(e)}")
                
                # Call fallback UI if provided
                if fallback_ui:
                    try:
                        return fallback_ui(*args, **kwargs)
                    except Exception as fallback_error:
                        st.error(f"备用组件也发生错误: {str(fallback_error)}")
                
                # Return None or empty result
                return None
        
        return wrapper
    return decorator


def render_fallback_preview():
    """Fallback UI for preview rendering errors."""
    st.error("预览渲染失败，请检查参数设置")
    st.info("💡 提示：尝试调整字体大小或页面布局")


def render_fallback_navigation():
    """Fallback UI for navigation errors."""
    st.error("导航组件加载失败")
    st.button("刷新页面", on_click=lambda: st.rerun())


def render_fallback_export():
    """Fallback UI for export errors."""
    st.error("导出功能暂时不可用")
    st.info("💡 提示：请稍后重试或联系技术支持")


def render_fallback_input():
    """Fallback UI for input section errors."""
    st.error("输入组件加载失败")
    st.info("💡 提示：请刷新页面或检查输入格式")
    st.text_area("备用输入", placeholder="请在此输入文本...", key="fallback_input")


def render_fallback_options():
    """Fallback UI for options section errors."""
    st.error("选项组件加载失败")
    st.info("💡 提示：使用默认设置继续")
    st.button("使用默认设置", key="fallback_options")


def render_fallback_editor():
    """Fallback UI for editor errors."""
    st.error("编辑器组件加载失败")
    st.info("💡 提示：请尝试刷新页面")
    st.button("重新加载编辑器", key="fallback_editor")


def render_fallback_sidebar():
    """Fallback UI for sidebar errors."""
    st.error("侧边栏组件加载失败")
    st.info("💡 提示：基本功能仍可使用")


def render_fallback_debug():
    """Fallback UI for debug panel errors."""
    st.error("调试面板加载失败")
    st.info("💡 提示：调试功能暂时不可用")


def render_fallback_components():
    """Fallback UI for general component errors."""
    st.error("组件加载失败")
    st.info("💡 提示：请刷新页面重试")
    st.button("刷新页面", on_click=lambda: st.rerun(), key="fallback_refresh")


def get_fallback_ui_for_component(component_name: str):
    """Get appropriate fallback UI function based on component name."""
    fallback_map = {
        'input': render_fallback_input,
        'options': render_fallback_options,
        'editor': render_fallback_editor,
        'sidebar': render_fallback_sidebar,
        'debug': render_fallback_debug,
        'preview': render_fallback_preview,
        'export': render_fallback_export,
        'navigation': render_fallback_navigation,
    }

    # Find matching fallback based on component name keywords
    for keyword, fallback_func in fallback_map.items():
        if keyword in component_name.lower():
            return fallback_func

    # Default fallback
    return render_fallback_components


def with_smart_error_boundary(component_name: str):
    """
    Enhanced error boundary that automatically selects appropriate fallback UI.
    """
    fallback_ui = get_fallback_ui_for_component(component_name)
    return with_error_boundary(component_name, fallback_ui)
