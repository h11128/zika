"""
UI Components for the preview system.
Provides reusable UI components for navigation and information display.
"""

import streamlit as st
from typing import List, Dict, Any

from ui.ports import get_ui_adapter, ComponentConfig


def render_page_navigation(total_pages: int) -> None:
    """Render page navigation controls."""
    if total_pages <= 1:
        return
    
    current_page = getattr(st.session_state, 'current_page', 0)
    
    adapter = get_ui_adapter()
    col1, col2, col3 = adapter.layout.columns([1, 2, 1])

    with col1:
        prev_config = ComponentConfig(key="prev_page", label="◀️ 上一页")
        if adapter.inputs.button(prev_config, disabled=current_page == 0):
            st.session_state.current_page = max(0, current_page - 1)
            st.rerun()

    with col2:
        adapter.markdown(f"**第 {current_page + 1} 页，共 {total_pages} 页**")

    with col3:
        next_config = ComponentConfig(key="next_page", label="下一页 ▶️")
        if adapter.inputs.button(next_config, disabled=current_page >= total_pages - 1):
            st.session_state.current_page = min(total_pages - 1, current_page + 1)
            st.rerun()


def render_page_info(processed_cards: List[Dict[str, str]], 
                    cards_per_page: int, total_pages: int) -> None:
    """Render page information."""
    adapter = get_ui_adapter()
    if not processed_cards:
        adapter.notifications.show_message("暂无卡片内容")
        return

    current_page = getattr(st.session_state, 'current_page', 0)
    start_idx = current_page * cards_per_page
    end_idx = min(start_idx + cards_per_page, len(processed_cards))

    adapter.markdown(f"*显示第 {start_idx + 1}-{end_idx} 张卡片，共 {len(processed_cards)} 张*")


def render_color_palette(preset_colors: List[str], on_change=None) -> str:
    """
    Render color palette using working component.

    Args:
        preset_colors: List of color hex codes to display
        on_change: Optional callback function called when color changes

    Returns:
        Selected color hex code

    Note: This function no longer directly modifies session state or triggers
    cache invalidation. The caller is responsible for handling the returned
    value and triggering appropriate invalidations through the state service.
    """
    from core.constants import DEFAULT_BACKGROUND_COLOR
    current = st.session_state.background_color or DEFAULT_BACKGROUND_COLOR

    try:
        from components.color_palette import color_palette
        selected = color_palette(
            preset_colors=preset_colors,
            value=current,
            key="main_color_palette",
        )

        if isinstance(selected, str) and selected and selected != current:
            # Call the on_change callback if provided
            if on_change:
                on_change(selected)
            return selected

        return current

    except Exception as e:
        # Fallback to selectbox if component fails
        adapter = get_ui_adapter()
        adapter.notifications.show_error(f"组件加载失败，使用备用选择器: {e}")
        try:
            current_index = preset_colors.index(current)
        except ValueError:
            current_index = 0

        color_config = ComponentConfig(
            key="color_selector_fallback",
            label="选择背景色"
        )
        selected_color = adapter.inputs.selectbox(
            color_config,
            options=preset_colors,
            index=current_index
        )

        if selected_color != current:
            # Call the on_change callback if provided
            if on_change:
                on_change(selected_color)
            return selected_color

        return current


def render_color_palette_legacy(preset_colors: List[str]) -> None:
    """
    Legacy wrapper for render_color_palette() with old behavior.

    DEPRECATED: Use render_color_palette() with on_change callback instead.
    This function maintains the old behavior for backward compatibility.
    """
    import warnings
    warnings.warn(
        "render_color_palette_legacy() is deprecated. Use render_color_palette() with on_change callback instead.",
        DeprecationWarning,
        stacklevel=2
    )

    def handle_color_change(new_color: str):
        """Handle color change with legacy behavior."""
        st.session_state.background_color = new_color
        # Clear preview cache when color changes
        from services.cache_v2 import clear_preview_cache
        clear_preview_cache()
        # Force preview parameter reset
        if 'last_preview_params' in st.session_state:
            del st.session_state.last_preview_params
        st.rerun()

    # Use the new function with legacy behavior
    render_color_palette(preset_colors, on_change=handle_color_change)


def render_color_palette_with_state_service(preset_colors: List[str], state_service=None) -> str:
    """
    Render color palette integrated with state service.

    Args:
        preset_colors: List of color hex codes to display
        state_service: State service instance for handling changes

    Returns:
        Selected color hex code

    This version integrates with the state service for proper invalidation
    handling without direct cache manipulation.
    """
    def handle_color_change(new_color: str):
        """Handle color change through state service."""
        if state_service:
            # Use state service for proper invalidation
            changeset = state_service.set_options_batch({'background_color': new_color})

            # Trigger appropriate invalidations based on changeset
            if changeset.affects_style:
                from ui.state.invalidations import get_invalidation_service
                invalidation_service = get_invalidation_service()
                invalidation_service.invalidate(
                    reason="background_color_changed",
                    affected_keys=["preview_cache", "style_digest"]
                )
        else:
            # Fallback to direct session state update
            st.session_state.background_color = new_color
            st.rerun()

    return render_color_palette(preset_colors, on_change=handle_color_change)


def render_preview_section(processed_cards: List[Dict[str, str]], preview_mode: str,
                          card_size_cm: float, gap_cm: float, margin_cm: float,
                          hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                          page_size: str, hanzi_font_family: str, background_color: str,
                          layout_rows: int, layout_cols: int, layout_auto_fill: bool) -> None:
    """Render the preview area with proper parameter change detection."""
    from services.cache_v2 import cached_create_page_preview_html, cached_create_simple_grid_html
    from services.cache_v2 import create_page_preview_html_immediate, create_simple_grid_html_immediate
    from core.state import check_params_changed, get_all_ui_params

    cards_per_page = max(1, rows * cols)
    adapter = get_ui_adapter()
    preview_placeholder = adapter.preview.empty_placeholder()

    # Check if parameters have changed to decide whether to use cache or immediate rendering
    current_params = get_all_ui_params(
        card_size, gap, margin, page_size,
        hanzi_font_size, pinyin_font_size, english_font_size,
        processed_cards,
        preview_mode
    )

    # Use immediate rendering if parameters changed recently or if this is a fresh session
    use_immediate = (
        check_params_changed(current_params) or
        not hasattr(st.session_state, 'last_preview_params') or
        st.session_state.get('last_preview_params') != current_params
    )

    if preview_mode == "📄 完整页面":
        # Debug: Print parameters when debug mode is enabled
        if st.session_state.get('debug_preview', False):
            adapter.write(f"🔍 Preview params: card_size_cm={card_size}, layout_auto_fill={auto_fill}, layout_rows={rows}, layout_cols={cols}")

        # 强制使用即时渲染，避免任何缓存导致的预览滞后
        html = create_page_preview_html_immediate(
            processed_cards, st.session_state.current_page,
            card_size, gap, margin,
            hanzi_font_size, pinyin_font_size, english_font_size,
            page_size, hanzi_font_family, background_color,
            layout_rows, layout_cols, auto_fill
        )
        with preview_placeholder.container():
            adapter.preview.html_component(html, height_cm=850)
    else:
        start_idx = st.session_state.current_page * cards_per_page
        end_idx = min(start_idx + cards_per_page, len(processed_cards))
        current_page_cards = processed_cards[start_idx:end_idx]

        if use_immediate:
            html = create_simple_grid_html_immediate(current_page_cards, hanzi_font_family, background_color, layout_rows, layout_cols,
                                                     hanzi_font_size, pinyin_font_size, english_font_size, card_size, auto_fill)
        else:
            html = cached_create_simple_grid_html(current_page_cards, hanzi_font_family, background_color, layout_rows, layout_cols,
                                                  hanzi_font_size, pinyin_font_size, english_font_size, card_size, auto_fill)
        with preview_placeholder.container():
            adapter.preview.html_component(html, height_cm=650)

    # Update last preview params
    st.session_state.last_preview_params = current_params