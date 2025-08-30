"""
Unified card editor module with zero direct Streamlit calls.
Handles card editing with pagination and search functionality using unified UI.
"""

from typing import List, Dict, Any, Optional

from core.feature_flags import get_feature_flag
from ui.error_boundary import with_error_boundary
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
from ui.unified import get_unified_ui
from ui.state_bridge import state_get, state_set, state_delete


@with_error_boundary("card_editor")
def render_improved_card_editor_unified(processed_cards: List[Dict[str, str]]) -> None:
    """Render an improved card editor that can handle large numbers of cards using unified UI."""
    # Try to use table editor if enabled
    try:
        from ui.table_editor import use_table_editor, render_table_editor, TableEditorConfig
        from services.card_models import CardCollection, use_stable_card_ids

        if use_table_editor() and use_stable_card_ids():
            ui = get_unified_ui()
            ui.write("**📊 表格编辑器**")

            # Convert to CardCollection and use table editor
            collection = CardCollection.from_legacy_format(processed_cards)
            config = TableEditorConfig(
                page_size=10,
                show_search=True,
                show_pagination=True,
                editable=True
            )
            updated_collection, needs_refresh = render_table_editor(collection, config)

            # Update processed_cards if changes were made
            if needs_refresh:
                state_set('processed_cards', updated_collection.to_legacy_format())

                # Clear preview cache to force regeneration
                try:
                    from ui.cache_manager import invalidate_preview_cache
                    invalidate_preview_cache("Card collection updated", "table_editor")
                except ImportError:
                    # Fallback to legacy cache clearing
                    try:
                        from services.cache import clear_preview_cache
                        clear_preview_cache()
                    except ImportError:
                        pass

                if state_get('last_preview_params') is not None:
                    state_delete('last_preview_params')

                ui.success("卡片已更新！")
                ui.rerun()

            return

    except ImportError:
        pass  # Fall back to legacy editor

    # Legacy editor implementation using unified UI
    total_cards = len(processed_cards)

    # Initialize edit page state
    if state_get('edit_page') is None:
        state_set('edit_page', 0)

    # Configuration for editing
    max_tabs_per_page = 8  # Reasonable number of tabs per page
    total_edit_pages = (total_cards + max_tabs_per_page - 1) // max_tabs_per_page

    ui = get_unified_ui()
    
    # Edit mode selection
    ui.write("**编辑模式选择:**")
    edit_mode = ui.radio(
        "选择编辑方式",
        ["分页编辑", "搜索编辑", "表格编辑"],
        horizontal=True,
        help_text="分页编辑：按页编辑卡片；搜索编辑：搜索特定卡片进行编辑；表格编辑：使用表格界面编辑"
    )

    if edit_mode == "表格编辑":
        # Try table editor again with different approach
        try:
            from ui.table_editor import render_table_editor, TableEditorConfig
            from services.card_models import CardCollection

            collection = CardCollection.from_legacy_format(processed_cards)
            config = TableEditorConfig(
                page_size=10,
                editable=True
            )
            updated_collection, needs_refresh = render_table_editor(collection, config)

            if needs_refresh:
                state_set('processed_cards', updated_collection.to_legacy_format())
                ui.rerun()

        except ImportError:
            ui.error("表格编辑器不可用，请使用其他编辑方式")

    elif edit_mode == "分页编辑":
        render_paginated_editor_unified(processed_cards, max_tabs_per_page, total_edit_pages)
    else:  # 搜索编辑
        render_search_editor_unified(processed_cards)


def render_paginated_editor_unified(processed_cards: List[Dict[str, str]], max_tabs_per_page: int, total_edit_pages: int) -> None:
    """Render paginated card editor using unified UI."""
    ui = get_unified_ui()
    total_cards = len(processed_cards)
    
    # Edit page navigation
    if total_edit_pages > 1:
        ui.write("**编辑页面导航:**")
        col1, col2, col3, col4, col5 = ui.columns([1, 1, 2, 1, 1])

        current_edit_page = state_get('edit_page', 0)

        with col1:
            if ui.button("⏮️ 首页", key="edit_first"):
                state_set('edit_page', 0)

        with col2:
            if ui.button("◀️ 上页", key="edit_prev"):
                state_set('edit_page', max(0, current_edit_page - 1))

        with col3:
            ui.write(f"编辑页 {current_edit_page + 1} / {total_edit_pages}")

        with col4:
            if ui.button("▶️ 下页", key="edit_next"):
                state_set('edit_page', min(total_edit_pages - 1, current_edit_page + 1))

        with col5:
            if ui.button("⏭️ 末页", key="edit_last"):
                state_set('edit_page', total_edit_pages - 1)

    # Calculate cards for current edit page
    current_edit_page = state_get('edit_page', 0)
    start_idx = current_edit_page * max_tabs_per_page
    end_idx = min(start_idx + max_tabs_per_page, total_cards)
    current_page_cards = processed_cards[start_idx:end_idx]

    if current_page_cards:
        tab_names = [f"卡片 {start_idx + i + 1}" for i in range(len(current_page_cards))]
        tabs = ui.tabs(tab_names)

        for i, tab in enumerate(tabs):
            with tab:
                actual_idx = start_idx + i
                render_single_card_editor_unified(processed_cards[actual_idx], actual_idx)


def render_search_editor_unified(processed_cards: List[Dict[str, str]]) -> None:
    """Render search-based card editor using unified UI."""
    ui = get_unified_ui()
    ui.write("**搜索编辑**")

    # Search input
    search_term = ui.text_input(
        "搜索卡片",
        value="",
        key="search_cards",
        placeholder="输入汉字、拼音或英文来搜索卡片",
        help_text="支持模糊搜索，输入任意字段的部分内容即可"
    )

    if search_term.strip():
        # Search for matching cards
        matching_cards = []
        matching_indices = []

        for i, card in enumerate(processed_cards):
            if (search_term.lower() in card['hanzi'].lower() or
                search_term.lower() in card['pinyin'].lower() or
                search_term.lower() in card['english'].lower()):
                matching_cards.append(card)
                matching_indices.append(i)

        if matching_cards:
            ui.success(f"找到 {len(matching_cards)} 张匹配的卡片")

            # Limit displayed cards for performance
            max_search_tabs = 10
            display_indices = matching_indices[:max_search_tabs]

            if len(matching_cards) > max_search_tabs:
                ui.warning(f"显示前 {max_search_tabs} 张匹配的卡片")

            tab_names = [f"卡片 {idx + 1}" for idx in display_indices]
            tabs = ui.tabs(tab_names)

            for i, tab in enumerate(tabs):
                with tab:
                    actual_idx = display_indices[i]
                    render_single_card_editor_unified(processed_cards[actual_idx], actual_idx)

        else:
            ui.info("没有找到匹配的卡片")
    else:
        ui.info("请输入搜索词来查找要编辑的卡片。")


def render_single_card_editor_unified(card: Dict[str, str], actual_idx: int) -> None:
    """Render editor for a single card using unified UI."""
    ui = get_unified_ui()
    col_e1, col_e2, col_e3 = ui.columns(3)

    with col_e1:
        new_hanzi = ui.text_input("汉字", value=card['hanzi'], key=f"edit_hanzi_{actual_idx}")

    with col_e2:
        new_pinyin = ui.text_input("拼音", value=card['pinyin'], key=f"edit_pinyin_{actual_idx}")

    with col_e3:
        new_english = ui.text_input("英文", value=card['english'], key=f"edit_english_{actual_idx}")

    # Update button
    col_btn1, col_btn2, col_btn3 = ui.columns(3)

    with col_btn1:
        if ui.button(f"💾 保存卡片 {actual_idx + 1}", key=f"save_card_{actual_idx}"):
            # Update the card in session state
            processed_cards = state_get('processed_cards', [])
            if actual_idx < len(processed_cards):
                processed_cards[actual_idx] = {
                    'hanzi': new_hanzi.strip(),
                    'pinyin': new_pinyin.strip(),
                    'english': new_english.strip()
                }
                state_set('processed_cards', processed_cards)

                # Clear preview cache to force regeneration
                try:
                    from ui.cache_manager import invalidate_preview_cache
                    invalidate_preview_cache("Card saved", "single_card_editor")
                except ImportError:
                    # Fallback to legacy cache clearing
                    try:
                        from services.cache import clear_preview_cache
                        clear_preview_cache()
                    except ImportError:
                        pass

                if state_get('last_preview_params') is not None:
                    state_delete('last_preview_params')

                ui.success(f"卡片 {actual_idx + 1} 已更新！")
                ui.rerun()

    with col_btn2:
        if ui.button(f"🗑️ 删除卡片 {actual_idx + 1}", key=f"delete_card_{actual_idx}"):
            # Remove the card from session state
            processed_cards = state_get('processed_cards', [])
            if actual_idx < len(processed_cards):
                processed_cards.pop(actual_idx)
                state_set('processed_cards', processed_cards)

                # Clear preview cache to force regeneration
                try:
                    from ui.cache_manager import invalidate_preview_cache
                    invalidate_preview_cache("Card deleted", "single_card_editor")
                except ImportError:
                    # Fallback to legacy cache clearing
                    try:
                        from services.cache import clear_preview_cache
                        clear_preview_cache()
                    except ImportError:
                        pass

                if state_get('last_preview_params') is not None:
                    state_delete('last_preview_params')

                ui.success(f"卡片 {actual_idx + 1} 已删除！")
                ui.rerun()

    with col_btn3:
        if ui.button(f"🔄 重置卡片 {actual_idx + 1}", key=f"reset_card_{actual_idx}"):
            ui.info("请刷新页面以重置卡片内容")


# Export the main function
__all__ = ['render_improved_card_editor_unified']
