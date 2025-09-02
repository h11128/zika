"""
Clean sections module for compatibility.

This module provides the minimum necessary functions for backward compatibility
while delegating to unified implementations where possible.
"""

import streamlit as st
from typing import List, Dict, Tuple, Any

# Import error boundaries for UI protection
try:
    from ui.error_boundaries import (
        with_error_boundary, preview_boundary, editor_boundary,
        sidebar_boundary, safe_call
    )
    ERROR_BOUNDARIES_AVAILABLE = True
except ImportError:
    ERROR_BOUNDARIES_AVAILABLE = False
    # Fallback decorators that do nothing
    def with_error_boundary(component_name: str, fallback_ui=None):
        def decorator(func):
            return func
        return decorator

    preview_boundary = lambda func: func
    editor_boundary = lambda func: func
    sidebar_boundary = lambda func: func
    safe_call = lambda func, *args, **kwargs: func(*args, **kwargs)


@with_error_boundary("sidebar")
def render_sidebar() -> None:
    """Render the sidebar with statistics, export history, and quick links."""
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_sidebar', False):
        from ui.sidebar import render_sidebar as render_sidebar_adapted
        render_sidebar_adapted()
        return

    # Use unified implementation if available
    if get_feature_flag('unified_sections', False):
        from ui.sections_unified import render_sidebar as render_sidebar_unified
        render_sidebar_unified()
        return

    # Adapter-based fallback
    from ui.ports import get_ui_adapter
    adapter = get_ui_adapter()

    with adapter.layout.sidebar():
        adapter.content.header("📊 使用统计")

        # Dictionary stats
        dict_stats = st.session_state.dictionary.get_statistics()
        adapter.content.metric("内置词典", f"{dict_stats['mini_dict_entries']} 词")
        adapter.content.metric("累计生成卡片", st.session_state.total_cards_generated)

        # Export history
        if st.session_state.export_history:
            adapter.content.subheader("📥 导出历史")
            for record in reversed(st.session_state.export_history[-5:]):  # Show last 5
                with adapter.layout.expander(f"{record['format'].upper()} - {record['cards']}张"):
                    adapter.content.write(f"时间: {record['time']}")
                    adapter.content.write(f"卡片: {record['cards']}张")
                    adapter.content.write(f"格式: {record['format'].upper()}")

        # Quick links
        adapter.content.markdown("### 🔗 快速链接")
        adapter.content.markdown("- [项目文档](https://github.com)")
        adapter.content.markdown("- [问题反馈](https://github.com)")
        adapter.content.markdown("- [使用教程](https://github.com)")


@with_error_boundary("export_section")
def render_export_section(processed_cards: List[Dict[str, str]]) -> None:
    """Render the export section with download buttons for different formats."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('adapted_export', False):
        from ui.export import render_export_section as render_export_adapted
        render_export_adapted(processed_cards)
        return

    # Use unified implementation if available
    if get_feature_flag('unified_sections', False):
        from ui.sections_unified import render_export_section as render_export_unified
        render_export_unified(processed_cards)
        return

    # Adapter-based fallback
    if not processed_cards:
        return

    from ui.ports import get_ui_adapter
    adapter = get_ui_adapter()
    adapter.content.header("📥 导出")
    adapter.notifications.info(f"💡 将导出 {len(processed_cards)} 张卡片")


def _effective_preview_params_from_state(passed: dict) -> dict:
    """Return effective preview params using state bridge as source of truth."""
    from ui.state_bridge import state_get
    
    return {
        'card_size_cm': state_get('card_size_cm', passed.get('card_size_cm')),
        'gap_cm': state_get('gap_cm', passed.get('gap_cm')),
        'margin_cm': state_get('margin_cm', passed.get('margin_cm')),
        'hanzi_font_size': state_get('hanzi_font_size', passed.get('hanzi_font_size')),
        'pinyin_font_size': state_get('pinyin_font_size', passed.get('pinyin_font_size')),
        'english_font_size': state_get('english_font_size', passed.get('english_font_size')),
        'page_size': state_get('page_size', passed.get('page_size')),
        'hanzi_font_family': state_get('hanzi_font_family', passed.get('hanzi_font_family')),
        'background_color': state_get('background_color', passed.get('background_color')),
        'layout_rows': state_get('layout_rows', passed.get('layout_rows')),
        'layout_cols': state_get('layout_cols', passed.get('layout_cols')),
        'layout_auto_fill': state_get('layout_auto_fill', passed.get('layout_auto_fill')),
    }


def render_left_column():
    """Render the left column with input and options, return all parameters."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('unified_sections', False):
        from ui.sections_unified import render_left_column as render_left_unified
        return render_left_unified()
    
    if get_feature_flag('adapted_inputs', False) and get_feature_flag('adapted_options', False):
        # Use safe re-exports from ui.sections which supply a default adapter
        from ui.sections import (
            render_input_section_adapted,
            render_options_section_adapted,
            render_advanced_options_adapted,
        )

        processed_cards = render_input_section_adapted()
        auto_pinyin, auto_translate, page_size, card_size_cm = render_options_section_adapted()
        gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = render_advanced_options_adapted()
    else:
        # Use existing implementations
        from ui.inputs import render_input_section
        from ui.options import render_options_section, render_advanced_options
        
        processed_cards = render_input_section()
        auto_pinyin, auto_translate, page_size, card_size_cm = render_options_section()
        gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = render_advanced_options()

    return {
        'processed_cards': processed_cards,
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size_cm': card_size_cm,
        'gap_cm': gap,
        'margin_cm': margin,
        'hanzi_font_size': hanzi_font_size,
        'pinyin_font_size': pinyin_font_size,
        'english_font_size': english_font_size,
        'layout_rows': layout_rows,
        'layout_cols': layout_cols
    }


def render_preview_column_header():
    """Render the preview column header with mode selection."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('unified_sections', False):
        from ui.sections_unified import render_preview_column_header as render_header_unified
        return render_header_unified()
    
    if get_feature_flag('adapted_preview', False):
        from ui.export_unified import render_right_column_unified
        return render_right_column_unified()
    else:
        # Legacy implementation
        from core.state import get_ui_preferences
        
        prefs = get_ui_preferences()
        hanzi_font_family, background_color = prefs['hanzi_font_family'], prefs['background_color']

        # Preview mode selection
        from ui.ports import get_ui_adapter
        adapter = get_ui_adapter()
        preview_mode = adapter.inputs.radio(
            "预览模式",
            ["📄 完整页面", "🔲 简单网格"],
            horizontal=True,
            help="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
        )
        
        # Use debouncing if available
        if get_feature_flag('debouncing', False):
            from ui.debounce import debounce_state_update
            debounce_state_update('preview_mode', preview_mode, delay_ms=150)
        else:
            st.session_state.preview_mode = preview_mode

        return {
            'hanzi_font_family': hanzi_font_family,
            'background_color': background_color,
            'preview_mode': preview_mode
        }


def render_improved_card_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render an improved card editor that can handle large numbers of cards."""
    # Delegate to editor module
    from ui.editor import render_improved_card_editor as render_editor
    render_editor(processed_cards)


def render_preview_content_legacy(processed_cards: List[Dict[str, str]], config) -> Tuple[int, int]:
    """Legacy preview content rendering."""
    # Delegate to preview module
    from ui.preview import render_preview_section_wrapper
    
    # Extract parameters from config
    render_preview_section_wrapper(
        processed_cards=processed_cards,
        card_size_cm=config.card_size_cm,
        gap_cm=config.gap_cm,
        margin_cm=config.margin_cm,
        page_size=config.page_size,
        hanzi_font_size=config.hanzi_font_size,
        pinyin_font_size=config.pinyin_font_size,
        english_font_size=config.english_font_size,
        hanzi_font_family=config.hanzi_font_family,
        background_color=config.background_color,
        layout_rows=config.layout_rows,
        layout_cols=config.layout_cols,
        layout_auto_fill=config.layout_auto_fill
    )
    
    return (0, 0)  # Return dummy values for compatibility


# Export all functions for compatibility
__all__ = [
    'render_sidebar',
    'render_export_section',
    'render_left_column',
    'render_preview_column_header',
    'render_improved_card_editor',
    'render_preview_content_legacy',
    '_effective_preview_params_from_state'
]
