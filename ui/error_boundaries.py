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
