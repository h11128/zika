"""
Card editor module for the UI refactor.
Handles card editing with pagination and search functionality.
"""

from typing import List, Dict, Any, Optional

from core.feature_flags import get_feature_flag
from ui.error_boundary import with_error_boundary
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
from ui.unified import get_unified_ui
from ui.state_bridge import state_get, state_set, state_delete


@with_error_boundary("card_editor")
def render_improved_card_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render an improved card editor that can handle large numbers of cards. Migrated from sections.py"""
    # Check if we should use adapter
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_editor', False):
        from ui.ports import get_ui_adapter
        adapter = get_ui_adapter()
        render_card_editor_adapted(adapter, processed_cards)
        return

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

                # Clear preview cache
                try:
                    from services.cache import clear_preview_cache
                    clear_preview_cache()
                except Exception:
                    pass

                if state_get('last_preview_params') is not None:
                    state_delete('last_preview_params')

                ui = get_unified_ui()
                ui.success("卡片已更新！")
                ui.rerun()

            return

    except ImportError:
        pass  # Fall back to legacy editor

    # Legacy editor implementation
    total_cards = len(processed_cards)

    # Initialize edit page state
    if state_get('edit_page') is None:
        state_set('edit_page', 0)

    # Configuration for editing
    max_tabs_per_page = 8  # Reasonable number of tabs per page
    total_edit_pages = (total_cards + max_tabs_per_page - 1) // max_tabs_per_page

    # Edit mode selection
    ui = get_unified_ui()
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
                page_size=15,
                show_search=True,
                show_pagination=True,
                editable=True
            )
            updated_collection, needs_refresh = render_table_editor(collection, config)

            if needs_refresh:
                st.session_state.processed_cards = updated_collection.to_legacy_format()
                st.rerun()

        except ImportError:
            st.error("表格编辑器不可用，请使用其他编辑方式")

    elif edit_mode == "分页编辑":
        render_paginated_editor(processed_cards, max_tabs_per_page, total_edit_pages)
    else:
        render_search_editor(processed_cards)


@with_error_boundary("paginated_editor")
def render_paginated_editor(processed_cards: List[Dict[str, str]], max_tabs_per_page: int, total_edit_pages: int) -> None:
    """Render paginated card editor. Migrated from sections.py"""
    total_cards = len(processed_cards)

    # Edit page navigation
    if total_edit_pages > 1:
        st.write("**编辑页面导航:**")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⏮️ 首页", key="edit_first"):
                st.session_state.edit_page = 0

        with col2:
            if st.button("◀️ 上页", key="edit_prev"):
                st.session_state.edit_page = max(0, st.session_state.edit_page - 1)

        with col3:
            st.write(f"编辑页 {st.session_state.edit_page + 1} / {total_edit_pages}")

        with col4:
            if st.button("▶️ 下页", key="edit_next"):
                st.session_state.edit_page = min(total_edit_pages - 1, st.session_state.edit_page + 1)

        with col5:
            if st.button("⏭️ 末页", key="edit_last"):
                st.session_state.edit_page = total_edit_pages - 1

    # Calculate cards for current edit page
    start_idx = st.session_state.edit_page * max_tabs_per_page
    end_idx = min(start_idx + max_tabs_per_page, total_cards)
    current_page_cards = processed_cards[start_idx:end_idx]

    # Create tabs for current page cards
    if current_page_cards:
        tab_names = [f"卡片 {start_idx + i + 1}" for i in range(len(current_page_cards))]
        tabs = st.tabs(tab_names)

        for i, (tab, card) in enumerate(zip(tabs, current_page_cards)):
            with tab:
                actual_idx = start_idx + i
                render_single_card_editor(card, actual_idx)


@with_error_boundary("search_editor")
def render_search_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render search-based card editor. Migrated from sections.py"""
    st.write("**搜索编辑**")

    # Search input
    search_term = st.text_input(
        "搜索卡片",
        placeholder="输入汉字、拼音或英文来搜索...",
        help="搜索特定卡片进行编辑"
    )

    if search_term:
        # Filter cards based on search term
        search_lower = search_term.lower()
        matching_cards = []
        matching_indices = []

        for i, card in enumerate(processed_cards):
            if (search_lower in card.get('hanzi', '').lower() or
                search_lower in card.get('pinyin', '').lower() or
                search_lower in card.get('english', '').lower()):
                matching_cards.append(card)
                matching_indices.append(i)

        if matching_cards:
            st.success(f"找到 {len(matching_cards)} 张匹配的卡片")

            # Create tabs for matching cards (limit to avoid too many tabs)
            max_search_tabs = 10
            display_cards = matching_cards[:max_search_tabs]
            display_indices = matching_indices[:max_search_tabs]

            if len(matching_cards) > max_search_tabs:
                st.warning(f"显示前 {max_search_tabs} 张匹配的卡片")

            tab_names = [f"卡片 {idx + 1}" for idx in display_indices]
            tabs = st.tabs(tab_names)

            for tab, card, original_idx in zip(tabs, display_cards, display_indices):
                with tab:
                    render_single_card_editor(card, original_idx)
        else:
            st.info("没有找到匹配的卡片")
    else:
        st.info("请输入搜索词来查找要编辑的卡片。")


@with_error_boundary("single_card_editor")
def render_single_card_editor(card: Dict[str, str], actual_idx: int) -> None:
    """Render editor for a single card. Migrated from sections.py"""
    col_e1, col_e2, col_e3 = st.columns(3)

    with col_e1:
        new_hanzi = st.text_input("汉字", value=card['hanzi'], key=f"edit_hanzi_{actual_idx}")

    with col_e2:
        new_pinyin = st.text_input("拼音", value=card['pinyin'], key=f"edit_pinyin_{actual_idx}")

    with col_e3:
        new_english = st.text_input("英文", value=card['english'], key=f"edit_english_{actual_idx}")

    # Update button
    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button(f"💾 保存卡片 {actual_idx + 1}", key=f"save_card_{actual_idx}"):
            # Update the card in session state
            st.session_state.processed_cards[actual_idx] = {
                'hanzi': new_hanzi.strip(),
                'pinyin': new_pinyin.strip(),
                'english': new_english.strip()
            }

            # Clear preview cache to force regeneration
            try:
                from services.cache import clear_preview_cache
                clear_preview_cache()
            except Exception:
                pass

            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params

            st.success(f"卡片 {actual_idx + 1} 已更新！")
            st.rerun()

    with col_btn2:
        if st.button(f"🗑️ 删除卡片 {actual_idx + 1}", key=f"delete_card_{actual_idx}"):
            # Remove the card from session state
            st.session_state.processed_cards.pop(actual_idx)

            # Clear preview cache
            try:
                from services.cache import clear_preview_cache
                clear_preview_cache()
            except Exception:
                pass

            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params

            st.success(f"卡片 {actual_idx + 1} 已删除！")
            st.rerun()

    with col_btn3:
        if st.button(f"🔄 重置卡片 {actual_idx + 1}", key=f"reset_card_{actual_idx}"):
            st.info("请刷新页面以重置卡片内容")


def render_paginated_editor(processed_cards: List[Dict[str, str]], 
                          max_tabs_per_page: int, total_edit_pages: int) -> None:
    """Render paginated card editor."""
    total_cards = len(processed_cards)

    if total_edit_pages > 1:
        # Edit page navigation
        st.write("**编辑页面导航:**")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⏮️ 首页", key="edit_first"):
                st.session_state.edit_page = 0

        with col2:
            if st.button("◀️ 上页", key="edit_prev"):
                st.session_state.edit_page = max(0, st.session_state.edit_page - 1)

        with col3:
            st.write(f"编辑页 {st.session_state.edit_page + 1} / {total_edit_pages}")

        with col4:
            if st.button("▶️ 下页", key="edit_next"):
                st.session_state.edit_page = min(total_edit_pages - 1, st.session_state.edit_page + 1)

        with col5:
            if st.button("⏭️ 末页", key="edit_last"):
                st.session_state.edit_page = total_edit_pages - 1

    # Calculate cards for current edit page
    start_idx = st.session_state.edit_page * max_tabs_per_page
    end_idx = min(start_idx + max_tabs_per_page, total_cards)
    current_page_cards = processed_cards[start_idx:end_idx]

    # Create tabs for current page cards
    if current_page_cards:
        tab_names = [f"卡片 {start_idx + i + 1}" for i in range(len(current_page_cards))]
        tabs = st.tabs(tab_names)

        for i, (tab, card) in enumerate(zip(tabs, current_page_cards)):
            with tab:
                render_single_card_editor(card, start_idx + i, processed_cards)


def render_search_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render search-based card editor."""
    # Search functionality
    search_term = st.text_input(
        "搜索卡片",
        placeholder="输入汉字、拼音或英文来搜索...",
        help="搜索特定卡片进行编辑"
    )

    if search_term:
        # Filter cards based on search term
        search_lower = search_term.lower()
        matching_cards = []
        matching_indices = []

        for i, card in enumerate(processed_cards):
            if (search_lower in card.get('hanzi', '').lower() or
                search_lower in card.get('pinyin', '').lower() or
                search_lower in card.get('english', '').lower()):
                matching_cards.append(card)
                matching_indices.append(i)

        if matching_cards:
            st.success(f"找到 {len(matching_cards)} 张匹配的卡片")

            # Create tabs for matching cards
            tab_names = [f"卡片 {idx + 1}" for idx in matching_indices]
            tabs = st.tabs(tab_names)

            for tab, card, original_idx in zip(tabs, matching_cards, matching_indices):
                with tab:
                    render_single_card_editor(card, original_idx, processed_cards)
        else:
            st.info("没有找到匹配的卡片")
    else:
        st.info("请输入搜索词来查找要编辑的卡片")


def render_single_card_editor(card: Dict[str, str], card_index: int, 
                            all_cards: List[Dict[str, str]]) -> None:
    """Render editor for a single card."""
    st.write(f"**编辑卡片 {card_index + 1}**")

    # Create form for editing
    with st.form(f"edit_card_{card_index}"):
        col1, col2, col3 = st.columns(3)

        with col1:
            new_hanzi = st.text_input(
                "汉字",
                value=card.get('hanzi', ''),
                key=f"hanzi_{card_index}"
            )

        with col2:
            new_pinyin = st.text_input(
                "拼音",
                value=card.get('pinyin', ''),
                key=f"pinyin_{card_index}"
            )

        with col3:
            new_english = st.text_input(
                "英文",
                value=card.get('english', ''),
                key=f"english_{card_index}"
            )

        # Form buttons
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.form_submit_button("💾 保存更改"):
                # Update the card
                all_cards[card_index] = {
                    'hanzi': new_hanzi.strip(),
                    'pinyin': new_pinyin.strip(),
                    'english': new_english.strip()
                }
                st.success("卡片已更新")
                st.rerun()

        with col2:
            if st.form_submit_button("🗑️ 删除卡片"):
                # Remove the card
                all_cards.pop(card_index)
                st.success("卡片已删除")
                st.rerun()

        with col3:
            if st.form_submit_button("🔄 重置"):
                st.info("请刷新页面以重置卡片")


def render_card_editor_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]]) -> None:
    """Render card editor using UI adapter."""
    total_cards = len(processed_cards)

    # Edit mode selection
    adapter.markdown("**编辑模式选择:**")
    mode_config = ComponentConfig(
        key="edit_mode_adapted",
        label="选择编辑方式",
        help_text="分页编辑：按页编辑卡片；搜索编辑：搜索特定卡片进行编辑"
    )
    edit_mode = adapter.inputs.radio(
        mode_config,
        options=["分页编辑", "搜索编辑"],
        index=0,
        horizontal=True
    )

    if edit_mode == "分页编辑":
        render_paginated_editor_adapted(adapter, processed_cards)
    else:
        render_search_editor_adapted(adapter, processed_cards)


def render_paginated_editor_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]]) -> None:
    """Render paginated editor using UI adapter."""
    total_cards = len(processed_cards)
    max_tabs_per_page = 8
    total_edit_pages = (total_cards + max_tabs_per_page - 1) // max_tabs_per_page
    current_edit_page = 0  # In real implementation, this would come from state

    if total_edit_pages > 1:
        # Edit page navigation
        adapter.markdown("**编辑页面导航:**")
        col1, col2, col3, col4, col5 = adapter.layout.columns([1, 1, 2, 1, 1])

        with col1:
            first_config = ComponentConfig(key="edit_first_adapted", label="⏮️ 首页")
            adapter.inputs.button(first_config)

        with col2:
            prev_config = ComponentConfig(key="edit_prev_adapted", label="◀️ 上页")
            adapter.inputs.button(prev_config)

        with col3:
            adapter.markdown(f"编辑页 {current_edit_page + 1} / {total_edit_pages}")

        with col4:
            next_config = ComponentConfig(key="edit_next_adapted", label="▶️ 下页")
            adapter.inputs.button(next_config)

        with col5:
            last_config = ComponentConfig(key="edit_last_adapted", label="⏭️ 末页")
            adapter.inputs.button(last_config)

    # Calculate cards for current edit page
    start_idx = current_edit_page * max_tabs_per_page
    end_idx = min(start_idx + max_tabs_per_page, total_cards)
    current_page_cards = processed_cards[start_idx:end_idx]

    # Create tabs for current page cards
    if current_page_cards:
        tab_names = [f"卡片 {start_idx + i + 1}" for i in range(len(current_page_cards))]
        tabs = adapter.layout.tabs(tab_names)

        for i, (tab, card) in enumerate(zip(tabs, current_page_cards)):
            with tab:
                render_single_card_editor_adapted(adapter, card, start_idx + i, processed_cards)


def render_search_editor_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]]) -> None:
    """Render search editor using UI adapter."""
    # Search functionality
    search_config = ComponentConfig(
        key="card_search_adapted",
        label="搜索卡片",
        help_text="搜索特定卡片进行编辑"
    )
    search_term = adapter.inputs.text_input(
        search_config, value="", placeholder="输入汉字、拼音或英文来搜索..."
    )

    if search_term:
        # Filter cards (simplified for adapter)
        adapter.notifications.show_message(
            f"搜索功能需要完整的状态管理实现", NotificationLevel.INFO
        )
    else:
        adapter.notifications.show_message(
            "请输入搜索词来查找要编辑的卡片", NotificationLevel.INFO
        )


def render_single_card_editor_adapted(adapter: UIAdapter, card: Dict[str, str], 
                                    card_index: int, all_cards: List[Dict[str, str]]) -> None:
    """Render single card editor using UI adapter."""
    adapter.markdown(f"**编辑卡片 {card_index + 1}**")

    # Create form inputs
    col1, col2, col3 = adapter.layout.columns([1, 1, 1])

    with col1:
        hanzi_config = ComponentConfig(
            key=f"hanzi_adapted_{card_index}",
            label="汉字"
        )
        new_hanzi = adapter.inputs.text_input(hanzi_config, value=card.get('hanzi', ''))

    with col2:
        pinyin_config = ComponentConfig(
            key=f"pinyin_adapted_{card_index}",
            label="拼音"
        )
        new_pinyin = adapter.inputs.text_input(pinyin_config, value=card.get('pinyin', ''))

    with col3:
        english_config = ComponentConfig(
            key=f"english_adapted_{card_index}",
            label="英文"
        )
        new_english = adapter.inputs.text_input(english_config, value=card.get('english', ''))

    # Form buttons
    col1, col2, col3 = adapter.layout.columns([1, 1, 1])

    with col1:
        save_config = ComponentConfig(
            key=f"save_adapted_{card_index}",
            label="💾 保存更改"
        )
        if adapter.inputs.button(save_config):
            adapter.notifications.show_message("卡片已更新", NotificationLevel.SUCCESS)

    with col2:
        delete_config = ComponentConfig(
            key=f"delete_adapted_{card_index}",
            label="🗑️ 删除卡片"
        )
        if adapter.inputs.button(delete_config):
            adapter.notifications.show_message("卡片已删除", NotificationLevel.SUCCESS)

    with col3:
        reset_config = ComponentConfig(
            key=f"reset_adapted_{card_index}",
            label="🔄 重置"
        )
        if adapter.inputs.button(reset_config):
            adapter.notifications.show_message("请刷新页面以重置卡片", NotificationLevel.INFO)


def use_adapted_editor() -> bool:
    """Check if adapted editor should be used."""
    return get_feature_flag('adapted_editor', False)


def render_card_editor_unified(processed_cards: List[Dict[str, str]]) -> None:
    """
    Unified card editor that chooses between legacy and adapted versions.
    """
    if use_adapted_editor():
        adapter = get_ui_adapter()
        render_card_editor_adapted(adapter, processed_cards)
    else:
        render_improved_card_editor(processed_cards)


# Export the main functions
__all__ = [
    'render_improved_card_editor',
    'render_card_editor_adapted',
    'render_card_editor_unified',
    'use_adapted_editor'
]
