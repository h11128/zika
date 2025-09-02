"""
Sidebar module for the UI refactor.
Handles sidebar content including navigation, settings, and information.
"""

# Option C alias: route through ports.st while preserving module-level st for tests
import ui.ports as ports
st = ports.st
from typing import Dict, Any, Optional

from core.feature_flags import get_feature_flag, set_test_override, clear_all_test_overrides, DEFAULT_FLAGS
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel

# Import error boundaries for UI protection
try:
    from ui.error_boundaries import with_error_boundary
    ERROR_BOUNDARIES_AVAILABLE = True
except ImportError:
    ERROR_BOUNDARIES_AVAILABLE = False
    # Fallback decorator that does nothing
    def with_error_boundary(component_name: str, fallback_ui=None):
        def decorator(func):
            return func
        return decorator


@with_error_boundary("sidebar")
def render_sidebar() -> None:
    """Render the main sidebar with navigation and settings."""
    # Use adapter implementation
    adapter = get_ui_adapter()
    render_sidebar_adapted(adapter)


@with_error_boundary("sidebar_header")
def render_sidebar_header() -> None:
    """Render sidebar header with app title and version."""
    st.title("🀄 中文学习卡片")
    st.markdown("---")
    
    # App version and status
    st.caption("版本 2.0.0")
    
    # Quick status indicators
    if 'processed_cards' in st.session_state and st.session_state.processed_cards:
        card_count = len(st.session_state.processed_cards)
        st.success(f"✅ {card_count} 张卡片已生成")
    else:
        st.info("📝 等待输入文本")


@with_error_boundary("navigation_menu")
def render_navigation_menu() -> None:
    """Render navigation menu."""
    st.markdown("### 🧭 导航")
    
    # Main sections
    sections = {
        "📝 输入": "input",
        "⚙️ 选项": "options", 
        "👀 预览": "preview",
        "✏️ 编辑": "editor",
        "📤 导出": "export"
    }
    
    # Current section tracking
    if 'current_section' not in st.session_state:
        st.session_state.current_section = "input"
    
    for label, section_id in sections.items():
        if st.button(label, key=f"nav_{section_id}", use_container_width=True):
            st.session_state.current_section = section_id
            st.rerun()


@with_error_boundary("settings_section")
def render_settings_section() -> None:
    """Render settings and preferences."""
    st.markdown("---")
    st.markdown("### ⚙️ 设置")
    
    # Theme settings
    with st.expander("🎨 主题设置", expanded=False):
        theme = st.selectbox(
            "界面主题",
            ["自动", "浅色", "深色"],
            key="ui_theme",
            help="选择界面主题"
        )
        
        compact_mode = st.checkbox(
            "紧凑模式",
            value=st.session_state.get('compact_mode', False),
            key="compact_mode",
            help="使用更紧凑的界面布局"
        )
    
    # Language settings
    with st.expander("🌐 语言设置", expanded=False):
        ui_language = st.selectbox(
            "界面语言",
            ["中文", "English"],
            key="ui_language",
            help="选择界面显示语言"
        )
        
        auto_detect_language = st.checkbox(
            "自动检测输入语言",
            value=st.session_state.get('auto_detect_language', True),
            key="auto_detect_language",
            help="自动检测输入文本的语言"
        )
    
    # Performance settings
    with st.expander("⚡ 性能设置", expanded=False):
        enable_caching = st.checkbox(
            "启用缓存",
            value=st.session_state.get('enable_caching', True),
            key="enable_caching",
            help="启用预览和导出缓存以提高性能"
        )
        
        batch_processing = st.checkbox(
            "批量处理",
            value=st.session_state.get('batch_processing', False),
            key="batch_processing",
            help="对大量卡片使用批量处理"
        )


@with_error_boundary("info_section")
def render_info_section() -> None:
    """Render information and help section."""
    st.markdown("---")
    st.markdown("### ℹ️ 信息")
    
    # Statistics
    with st.expander("📊 统计信息", expanded=False):
        # Session statistics
        total_cards = len(st.session_state.get('processed_cards', []))
        total_exports = len(st.session_state.get('export_history', []))
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("当前卡片", total_cards)
        with col2:
            st.metric("导出次数", total_exports)
        
        # Memory usage (simplified)
        if total_cards > 0:
            avg_card_size = 50  # Estimated bytes per card
            memory_usage = total_cards * avg_card_size
            st.metric("内存使用", f"{memory_usage} B")
    
    # Help and documentation
    with st.expander("❓ 帮助", expanded=False):
        st.markdown("""
        **快速开始:**
        1. 在输入区域输入中文文本
        2. 调整选项和布局设置
        3. 预览生成的卡片
        4. 导出为PDF、PowerPoint或CSV
        
        **提示:**
        - 使用智能分词功能处理长句
        - 调整字体大小以适应不同用途
        - 使用搜索功能快速编辑特定卡片
        """)
        
        # Quick links
        st.markdown("### 🔗 快速链接")
        st.markdown("- [项目文档](https://github.com)")
        st.markdown("- [问题反馈](https://github.com)")
        st.markdown("- [使用教程](https://github.com)")


@with_error_boundary("debug_section")
def render_debug_section() -> None:
    """Render debug section for development."""
    if not get_feature_flag('show_debug_panel', False):
        return
    
    st.markdown("---")
    st.markdown("### 🔧 调试")
    
    with st.expander("🐛 调试信息", expanded=False):
        # Feature flags status
        st.markdown("**功能标志:**")
        debug_flags = [
            'use_state_service',
            'use_cache_v2', 
            'use_new_preview_pipeline',
            'adapted_inputs',
            'adapted_options',
            'adapted_preview',
            'adapted_editor',
            'adapted_export'
        ]
        
        for flag in debug_flags:
            status = get_feature_flag(flag, False)
            icon = "✅" if status else "❌"
            st.text(f"{icon} {flag}: {status}")
        
        # Session state info
        st.markdown("**会话状态:**")
        state_keys = list(st.session_state.keys())
        st.text(f"状态键数量: {len(state_keys)}")
        
        # Performance metrics
        st.markdown("**性能指标:**")
        if 'last_render_time' in st.session_state:
            st.text(f"上次渲染时间: {st.session_state.last_render_time}ms")
        
        # Clear session state button
        if st.button("🗑️ 清空会话状态", key="clear_session"):
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):  # Keep internal keys
                    del st.session_state[key]
            st.success("会话状态已清空")
            st.rerun()


def render_sidebar_adapted(adapter: UIAdapter) -> None:
    """Render sidebar using UI adapter."""
    with adapter.layout.sidebar():
        render_sidebar_header_adapted(adapter)
        render_navigation_menu_adapted(adapter)
        render_settings_section_adapted(adapter)
        render_info_section_adapted(adapter)
        render_debug_section_adapted(adapter)


def render_sidebar_header_adapted(adapter: UIAdapter) -> None:
    """Render sidebar header using UI adapter."""
    adapter.title("🀄 中文学习卡片")
    adapter.markdown("---")
    
    adapter.caption("版本 2.0.0")
    
    # Status indicators (simplified for adapter)
    adapter.notifications.show_message(
        "适配器模式运行中", NotificationLevel.INFO
    )


def render_navigation_menu_adapted(adapter: UIAdapter) -> None:
    """Render navigation menu using UI adapter."""
    adapter.markdown("### 🧭 导航")
    
    sections = [
        ("📝 输入", "input"),
        ("⚙️ 选项", "options"), 
        ("👀 预览", "preview"),
        ("✏️ 编辑", "editor"),
        ("📤 导出", "export")
    ]
    
    for label, section_id in sections:
        nav_config = ComponentConfig(
            key=f"nav_{section_id}_adapted",
            label=label
        )
        if adapter.inputs.button(nav_config):
            adapter.notifications.show_message(
                f"导航到 {label}", NotificationLevel.INFO
            )


def render_settings_section_adapted(adapter: UIAdapter) -> None:
    """Render settings section using UI adapter."""
    adapter.markdown("---")
    adapter.markdown("### ⚙️ 设置")
    
    # Theme settings
    with adapter.layout.expander("🎨 主题设置", expanded=False):
        theme_config = ComponentConfig(
            key="ui_theme_adapted",
            label="界面主题",
            help_text="选择界面主题"
        )
        theme = adapter.inputs.selectbox(
            theme_config, options=["自动", "浅色", "深色"], index=0
        )
        
        compact_config = ComponentConfig(
            key="compact_mode_adapted",
            label="紧凑模式",
            help_text="使用更紧凑的界面布局"
        )
        compact_mode = adapter.inputs.checkbox(compact_config, value=False)


def render_info_section_adapted(adapter: UIAdapter) -> None:
    """Render info section using UI adapter."""
    adapter.markdown("---")
    adapter.markdown("### ℹ️ 信息")
    
    # Statistics
    with adapter.layout.expander("📊 统计信息", expanded=False):
        col1, col2 = adapter.layout.columns([1, 1])
        
        with col1:
            adapter.metric("当前卡片", "0")
        with col2:
            adapter.metric("导出次数", "0")


def use_adapted_sidebar() -> bool:
    """Check if adapted sidebar should be used."""
    return True


def render_sidebar_unified() -> None:
    """
    Unified sidebar that chooses between legacy and adapted versions.
    """
    if use_adapted_sidebar():
        adapter = get_ui_adapter()
        render_sidebar_adapted(adapter)
    else:
        render_sidebar()


def render_debug_section_adapted(adapter: UIAdapter) -> None:
    """Render debug section using UI adapter."""
    if not get_feature_flag('show_debug_panel', False):
        return

    adapter.markdown("---")
    adapter.markdown("### 🔧 调试")

    with adapter.layout.expander("🐛 调试信息", expanded=False):
        # Feature flags status
        adapter.markdown("**功能标志 (会话覆盖)：**")

        # Build full list of flags from defaults plus any cached values
        all_flags = sorted(set(DEFAULT_FLAGS.keys()))

        # Toggle all flags
        for flag in all_flags:
            current = bool(get_feature_flag(flag, DEFAULT_FLAGS.get(flag, False)))
            cfg = ComponentConfig(key=f"flag_{flag}", label=f"{flag}")
            new_val = adapter.inputs.checkbox(cfg, value=current)
            if new_val != current:
                # Use test override to set during this session
                set_test_override(flag, new_val)
                adapter.notifications.show_message(
                    f"已切换 {flag} = {new_val}", NotificationLevel.INFO
                )
                adapter.rerun()

        # Reset overrides to defaults button
        reset_cfg = ComponentConfig(
            key="reset_flags_to_defaults",
            label="↩️ 重置功能标志为默认值",
            help_text="清除会话中的所有功能标志覆盖"
        )
        if adapter.inputs.button(reset_cfg):
            clear_all_test_overrides()
            adapter.notifications.show_message("已重置功能标志为默认值", NotificationLevel.SUCCESS)
            adapter.rerun()

        # Session state info
        adapter.markdown("**会话状态:**")
        state_keys = list(st.session_state.keys())
        adapter.text(f"状态键数量: {len(state_keys)}")

        # Performance metrics
        adapter.markdown("**性能指标:**")
        if 'last_render_time' in st.session_state:
            adapter.text(f"上次渲染时间: {st.session_state.last_render_time}ms")

        # Clear session state button
        clear_config = ComponentConfig(
            key="clear_session_adapted",
            label="🗑️ 清空会话状态",
            help_text="清空当前会话的所有状态数据"
        )
        if adapter.inputs.button(clear_config):
            for key in list(st.session_state.keys()):
                if not key.startswith('_'):  # Keep internal keys
                    del st.session_state[key]
            adapter.notifications.show_success("会话状态已清空")
            adapter.rerun()


# Export the main functions
__all__ = [
    'render_sidebar',
    'render_sidebar_adapted',
    'render_sidebar_unified',
    'use_adapted_sidebar'
]
