"""
UI Components for the Chinese Character Learning Cards application.
Reusable Streamlit components for color palette, pagination, and preview areas.
"""

import streamlit as st
from typing import List, Dict
from core.constants import DEFAULT_BACKGROUND_COLOR
from services.cache import cached_create_page_preview_html, cached_create_simple_grid_html


def render_color_palette(preset_colors: List[str]) -> None:
    """Render color palette using working component."""
    current = st.session_state.background_color or DEFAULT_BACKGROUND_COLOR

    try:
        from components.color_palette import color_palette
        selected = color_palette(
            preset_colors=preset_colors,
            value=current,
            key="main_color_palette",
        )

        if isinstance(selected, str) and selected and selected != current:
            st.session_state.background_color = selected
            # Clear preview cache when color changes
            from services.cache import clear_preview_cache
            clear_preview_cache()
            # Force preview parameter reset
            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params
            st.rerun()

    except Exception as e:
        # Fallback to selectbox if component fails
        st.error(f"组件加载失败，使用备用选择器: {e}")
        try:
            current_index = preset_colors.index(current)
        except ValueError:
            current_index = 0

        selected_color = st.selectbox(
            "选择背景色",
            options=preset_colors,
            index=current_index,
            key="color_selector_fallback"
        )

        if selected_color != current:
            st.session_state.background_color = selected_color
            # Clear preview cache when color changes
            from services.cache import clear_preview_cache
            clear_preview_cache()
            # Force preview parameter reset
            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params
            st.rerun()


def render_page_navigation(total_pages: int) -> None:
    """Render pagination navigation controls."""
    if total_pages <= 1:
        return
        
    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])

    with col_nav1:
        if st.button("⏮️ 首页", disabled=st.session_state.current_page == 0, use_container_width=True):
            st.session_state.current_page = 0
            st.rerun()

    with col_nav2:
        if st.button("◀️ 上页", disabled=st.session_state.current_page == 0, use_container_width=True):
            st.session_state.current_page = max(0, st.session_state.current_page - 1)
            st.rerun()

    with col_nav3:
        # Page selector
        new_page = st.selectbox(
            "页码",
            options=list(range(total_pages)),
            index=st.session_state.current_page,
            format_func=lambda x: f"第 {x+1} 页 / 共 {total_pages} 页",
            key="page_selector"
        )
        if new_page != st.session_state.current_page:
            st.session_state.current_page = new_page
            st.rerun()

    with col_nav4:
        if st.button("▶️ 下页", disabled=st.session_state.current_page >= total_pages - 1, use_container_width=True):
            st.session_state.current_page = min(total_pages - 1, st.session_state.current_page + 1)
            st.rerun()

    with col_nav5:
        if st.button("⏭️ 末页", disabled=st.session_state.current_page >= total_pages - 1, use_container_width=True):
            st.session_state.current_page = total_pages - 1
            st.rerun()


def render_preview_section(processed_cards: List[Dict[str, str]], preview_mode: str,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str, hanzi_font: str, background_color: str,
                           rows: int, cols: int, auto_fill: bool) -> None:
    """Render the preview area with proper parameter change detection."""
    from services.cache import cached_create_page_preview_html, cached_create_simple_grid_html
    from services.cache import create_page_preview_html_immediate, create_simple_grid_html_immediate
    from core.state import check_params_changed, get_all_ui_params

    cards_per_page = max(1, rows * cols)
    preview_placeholder = st.empty()

    # Check if parameters have changed to decide whether to use cache or immediate rendering
    current_params = get_all_ui_params(
        card_size, gap, margin, page_size,
        font_hanzi, font_pinyin, font_english,
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
            st.write(f"🔍 Preview params: card_size={card_size}, auto_fill={auto_fill}, rows={rows}, cols={cols}")

        # 强制使用即时渲染，避免任何缓存导致的预览滞后
        html = create_page_preview_html_immediate(
            processed_cards, st.session_state.current_page,
            card_size, gap, margin,
            font_hanzi, font_pinyin, font_english,
            page_size, hanzi_font, background_color,
            rows, cols, auto_fill
        )
        with preview_placeholder.container():
            st.components.v1.html(html, height=850)
    else:
        start_idx = st.session_state.current_page * cards_per_page
        end_idx = min(start_idx + cards_per_page, len(processed_cards))
        current_page_cards = processed_cards[start_idx:end_idx]

        if use_immediate:
            html = create_simple_grid_html_immediate(current_page_cards, hanzi_font, background_color, rows, cols,
                                                     font_hanzi, font_pinyin, font_english, card_size, auto_fill)
        else:
            html = cached_create_simple_grid_html(current_page_cards, hanzi_font, background_color, rows, cols,
                                                  font_hanzi, font_pinyin, font_english, card_size, auto_fill)
        with preview_placeholder.container():
            st.components.v1.html(html, height=650)

    # Update last preview params
    st.session_state.last_preview_params = current_params


def render_page_info(processed_cards: List[Dict[str, str]], cards_per_page: int, total_pages: int) -> None:
    """Render page information display."""
    cards_on_current_page = min(cards_per_page, len(processed_cards) - st.session_state.current_page * cards_per_page)
    st.info(f"📊 总计 {len(processed_cards)} 张卡片，共 {total_pages} 页 | 当前第 {st.session_state.current_page + 1} 页，显示 {cards_on_current_page} 张卡片")


def create_preview_placeholder() -> st.empty:
    """Create a stable placeholder container for preview content."""
    return st.empty()
