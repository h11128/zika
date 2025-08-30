"""
Unified sections module with zero direct Streamlit calls.

This module provides a clean implementation of all UI sections using
the unified UI interface and state bridge.
"""

from typing import List, Dict, Tuple, Any
from ui.unified import get_unified_ui
from ui.state_bridge import state_get, state_set

# Import error boundaries for UI protection
try:
    from ui.error_boundaries import with_error_boundary
except ImportError:
    # Fallback decorator that does nothing
    def with_error_boundary(component_name: str, fallback_ui=None):
        def decorator(func):
            return func
        return decorator


@with_error_boundary("sidebar")
def render_sidebar() -> None:
    """Render the sidebar with statistics, export history, and quick links."""
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_sidebar', False):
        from ui.sidebar import render_sidebar as render_sidebar_adapted
        render_sidebar_adapted()
        return

    ui = get_unified_ui()
    
    with ui.sidebar():
        ui.header("📊 使用统计")

        # Dictionary stats
        dictionary = state_get('dictionary')
        if dictionary:
            dict_stats = dictionary.get_statistics()
            ui.metric("内置词典", f"{dict_stats['mini_dict_entries']} 词")
        
        ui.metric("累计生成卡片", str(state_get('total_cards_generated', 0)))

        # Export history
        export_history = state_get('export_history', [])
        if export_history:
            ui.header("📥 导出历史", level=2)
            for record in reversed(export_history[-5:]):  # Show last 5
                with ui.expander(f"{record['format'].upper()} - {record['cards']}张"):
                    ui.write(f"时间: {record['time']}")
                    ui.write(f"卡片: {record['cards']}张")
                    ui.write(f"格式: {record['format'].upper()}")

        # Quick links
        ui.markdown("### 🔗 快速链接")
        ui.markdown("- [项目文档](https://github.com)")
        ui.markdown("- [问题反馈](https://github.com)")
        ui.markdown("- [使用教程](https://github.com)")


@with_error_boundary("export_section")
def render_export_section(processed_cards: List[Dict[str, str]]) -> None:
    """Render the export section with download buttons for different formats."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('adapted_export', False):
        from ui.export import render_export_section as render_export_adapted
        render_export_adapted(processed_cards)
        return

    # Use unified implementation
    from ui.export_unified import render_export_section_unified
    render_export_section_unified(processed_cards)


def _effective_preview_params_from_state(passed: dict) -> dict:
    """Return effective preview params using state bridge as source of truth."""
    return {
        'card_size': state_get('card_size', passed.get('card_size')),
        'gap': state_get('gap_cm', passed.get('gap')),
        'margin': state_get('margin_cm', passed.get('margin')),
        'font_hanzi': state_get('font_hanzi', passed.get('font_hanzi')),
        'font_pinyin': state_get('font_pinyin', passed.get('font_pinyin')),
        'font_english': state_get('font_english', passed.get('font_english')),
        'page_size': state_get('page_size', passed.get('page_size')),
        'hanzi_font': state_get('hanzi_font', passed.get('hanzi_font')),
        'background_color': state_get('background_color', passed.get('background_color')),
        'rows': state_get('rows', passed.get('rows')),
        'cols': state_get('cols', passed.get('cols')),
        'auto_fill': state_get('auto_fill', passed.get('auto_fill')),
    }


def render_left_column():
    """Render the left column with input and options, return all parameters."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('adapted_inputs', False) and get_feature_flag('adapted_options', False):
        from ui.inputs import render_input_section_adapted
        from ui.options import render_options_section_adapted, render_advanced_options_adapted
        
        processed_cards = render_input_section_adapted()
        auto_pinyin, auto_translate, page_size, card_size = render_options_section_adapted()
        gap, margin, font_hanzi, font_pinyin, font_english, rows, cols = render_advanced_options_adapted()
    else:
        # Use existing implementations
        from ui.inputs import render_input_section
        from ui.options import render_options_section, render_advanced_options
        
        processed_cards = render_input_section()
        auto_pinyin, auto_translate, page_size, card_size = render_options_section()
        gap, margin, font_hanzi, font_pinyin, font_english, rows, cols = render_advanced_options()

    return {
        'processed_cards': processed_cards,
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'rows': rows,
        'cols': cols
    }


def render_right_column(processed_cards: List[Dict[str, str]], **params) -> None:
    """Render the right column with preview."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('adapted_preview', False):
        from ui.preview import render_preview_section_wrapper_adapted
        render_preview_section_wrapper_adapted(processed_cards, **params)
        return

    # Use unified implementation
    from ui.export_unified import render_right_column_unified, render_empty_preview_unified
    
    if not processed_cards:
        render_empty_preview_unified()
        return
    
    # Get preview settings
    preview_settings = render_right_column_unified()
    
    # Render preview with settings
    from ui.preview import render_preview_section_wrapper
    
    # Merge preview settings with params
    merged_params = {**params, **preview_settings}
    
    render_preview_section_wrapper(processed_cards, **merged_params)


def render_preview_column_header():
    """Render the preview column header with mode selection."""
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('adapted_preview', False):
        from ui.export_unified import render_right_column_unified
        return render_right_column_unified()
    else:
        # Legacy implementation using unified UI
        from core.state import get_ui_preferences
        
        ui = get_unified_ui()
        
        prefs = get_ui_preferences()
        hanzi_font, background_color = prefs['hanzi_font'], prefs['background_color']

        # Preview mode selection
        preview_mode = ui.radio(
            "预览模式",
            ["📄 完整页面", "🔲 简单网格"],
            horizontal=True,
            help_text="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
        )
        
        # Use debouncing if available
        if get_feature_flag('debouncing', False):
            from ui.debounce import debounce_state_update
            debounce_state_update('preview_mode', preview_mode, delay_ms=150)
        else:
            state_set('preview_mode', preview_mode)

        return {
            'hanzi_font': hanzi_font,
            'background_color': background_color,
            'preview_mode': preview_mode
        }


# Export all functions
__all__ = [
    'render_sidebar',
    'render_export_section',
    'render_left_column',
    'render_right_column',
    'render_preview_column_header',
    '_effective_preview_params_from_state'
]
