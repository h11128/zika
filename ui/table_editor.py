"""
Framework-agnostic table editor for card editing.
Replaces st.tabs with data_editor table interface with diff tracking and apply flow.
Implements conflict resolution with latest-edit-wins policy and single preview invalidation.
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
import streamlit as st

from core.feature_flags import get_feature_flag
from services.card_models import Card, CardCollection, use_stable_card_ids
from services.merge_service import (
    MergeService, ChangeRecord, ChangeType, ConflictResolutionPolicy,
    get_merge_service, create_change_record
)
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
# from ui.debounce import debounce_form_input, form_context  # Not needed for basic functionality


@dataclass
class TableEditorConfig:
    """Configuration for table editor."""
    page_size: int = 15
    show_search: bool = True
    show_pagination: bool = True
    show_add_button: bool = True
    show_delete_button: bool = True
    editable: bool = True
    enable_apply_flow: bool = True


@dataclass
class CardEdit:
    """Represents a single card edit operation."""
    card_id: str
    field: str
    old_value: str
    new_value: str


@dataclass
class EditSession:
    """Tracks all edits in the current session for apply flow with conflict resolution."""
    edits: Dict[str, Dict[str, CardEdit]]
    deleted_cards: set
    added_cards: List[Card]
    change_records: List[ChangeRecord]

    def __init__(self):
        self.edits = {}
        self.deleted_cards = set()
        self.added_cards = []
        self.change_records = []

    def record_edit(self, card_id: str, field: str, old_value: str, new_value: str) -> None:
        """Record a field edit with change tracking."""
        if card_id not in self.edits:
            self.edits[card_id] = {}

        self.edits[card_id][field] = CardEdit(
            card_id=card_id,
            field=field,
            old_value=old_value,
            new_value=new_value
        )

        # Create change record for merge service
        change_record = create_change_record(
            change_type=ChangeType.FIELD_EDIT,
            card_id=card_id,
            field=field,
            old_value=old_value,
            new_value=new_value
        )
        self.change_records.append(change_record)

    def record_deletion(self, card_id: str) -> None:
        """Record a card deletion with change tracking."""
        self.deleted_cards.add(card_id)
        # Remove any pending edits for deleted card
        if card_id in self.edits:
            del self.edits[card_id]

        # Create change record for merge service
        change_record = create_change_record(
            change_type=ChangeType.CARD_DELETION,
            card_id=card_id
        )
        self.change_records.append(change_record)

    def record_addition(self, card: Card) -> None:
        """Record a new card addition with change tracking."""
        self.added_cards.append(card)

        # Create change record for merge service
        change_record = ChangeRecord(
            change_type=ChangeType.CARD_ADDITION,
            card_id=card.id,
            new_value=card  # Store the card object
        )
        self.change_records.append(change_record)

    def has_changes(self) -> bool:
        """Check if there are any pending changes."""
        return bool(self.edits or self.deleted_cards or self.added_cards)

    def get_change_summary(self) -> str:
        """Get a summary of pending changes."""
        edit_count = sum(len(fields) for fields in self.edits.values())
        delete_count = len(self.deleted_cards)
        add_count = len(self.added_cards)

        parts = []
        if edit_count > 0:
            parts.append(f"{edit_count} 个字段编辑")
        if delete_count > 0:
            parts.append(f"{delete_count} 个卡片删除")
        if add_count > 0:
            parts.append(f"{add_count} 个卡片添加")

        return "、".join(parts) if parts else "无更改"

    def clear(self) -> None:
        """Clear all pending changes."""
        self.edits.clear()
        self.deleted_cards.clear()
        self.added_cards.clear()
        self.change_records.clear()
    editable: bool = True


@dataclass
class EditOperation:
    """Represents an edit operation on a card."""
    card_id: str
    field: str
    old_value: str
    new_value: str


class TableEditor:
    """Framework-agnostic table editor for cards with apply flow."""

    def __init__(self, adapter: UIAdapter, config: TableEditorConfig = None):
        self.adapter = adapter
        self.config = config or TableEditorConfig()

        # Initialize edit session for apply flow
        if not hasattr(st.session_state, 'table_editor_session'):
            st.session_state.table_editor_session = EditSession()
        self.edit_session = st.session_state.table_editor_session

        self.search_term: str = ""
        self.current_page: int = 0
    
    def render(self, cards: CardCollection) -> Tuple[CardCollection, bool]:
        """
        Render framework-agnostic table editor with apply flow.

        Returns:
            Tuple[CardCollection, bool]: (updated_cards, needs_refresh)
        """
        if not use_stable_card_ids():
            # Fallback to legacy editor
            return self._render_legacy_fallback(cards)

        # Render apply flow controls if enabled
        if self.config.enable_apply_flow:
            needs_refresh = self._render_apply_controls(cards)
            if needs_refresh:
                return cards, True

        # Render search if enabled
        if self.config.show_search:
            self._render_search()

        # Filter cards based on search
        filtered_cards = self._filter_cards(cards)

        # Render pagination if enabled
        total_pages = math.ceil(len(filtered_cards) / self.config.page_size)
        if self.config.show_pagination and total_pages > 1:
            self._render_pagination(total_pages)
        
        # Get current page cards
        start_idx = self.current_page * self.config.page_size
        end_idx = min(start_idx + self.config.page_size, len(filtered_cards))
        page_cards = filtered_cards[start_idx:end_idx]
        
        # Render table
        self._render_table_header()
        updated_cards = self._render_table_rows(page_cards, cards)
        
        # Render action buttons
        needs_refresh = self._render_action_buttons(updated_cards)
        
        return updated_cards, needs_refresh

    def _render_apply_controls(self, cards: CardCollection) -> bool:
        """Render apply flow controls and handle apply action."""
        if not self.edit_session.has_changes():
            return False

        # Show pending changes summary
        self.adapter.markdown("### 📝 待应用的更改")
        change_summary = self.edit_session.get_change_summary()
        self.adapter.markdown(f"**更改摘要:** {change_summary}")

        # Apply and cancel buttons
        col1, col2, col3 = self.adapter.layout.columns([1, 1, 2])

        with col1:
            apply_config = ComponentConfig(
                key="apply_changes",
                label="✅ 应用更改"
            )
            if self.adapter.inputs.button(apply_config):
                # Apply all changes using merge service
                merge_result = self._apply_all_changes_with_merge(cards)

                if merge_result.success:
                    self.edit_session.clear()

                    # Update session state
                    st.session_state.processed_cards = merge_result.merged_collection.to_legacy_format()

                    # Trigger single preview invalidation
                    from ui.state import invalidate_preview_cache
                    invalidate_preview_cache("cards_updated")

                    # Show success message with conflict info
                    success_msg = f"已应用更改: {change_summary}"
                    if merge_result.has_conflicts:
                        success_msg += f" (解决了 {len(merge_result.conflicts_resolved)} 个冲突)"

                    self.adapter.notifications.show_message(
                        success_msg,
                        NotificationLevel.SUCCESS
                    )
                    return True
                else:
                    self.adapter.notifications.show_message(
                        f"应用更改失败: {merge_result.error_message}",
                        NotificationLevel.ERROR
                    )
                    return False

        with col2:
            cancel_config = ComponentConfig(
                key="cancel_changes",
                label="❌ 取消更改"
            )
            if self.adapter.inputs.button(cancel_config):
                self.edit_session.clear()
                self.adapter.notifications.show_message(
                    "已取消所有更改",
                    NotificationLevel.INFO
                )
                return True

        with col3:
            self.adapter.markdown("*更改将在点击'应用更改'后生效*")

        self.adapter.markdown("---")
        return False

    def _apply_all_changes_with_merge(self, cards: CardCollection):
        """Apply all pending changes using merge service with conflict resolution."""
        merge_service = get_merge_service()

        # Use merge service to apply changes with conflict resolution
        merge_result = merge_service.merge_changes(
            base_collection=cards,
            changes=self.edit_session.change_records,
            preserve_order=True
        )

        return merge_result

    def _apply_all_changes(self, cards: CardCollection) -> CardCollection:
        """Legacy apply method - kept for backward compatibility."""
        merge_result = self._apply_all_changes_with_merge(cards)
        return merge_result.merged_collection if merge_result.success else cards

        # Apply deletions
        for card_id in self.edit_session.deleted_cards:
            updated_cards.remove_card(card_id)

        # Apply additions
        for new_card in self.edit_session.added_cards:
            updated_cards.add_card(new_card)

        return updated_cards

    def _render_add_card_controls(self) -> None:
        """Render controls for adding new cards."""
        self.adapter.markdown("### ➕ 添加新卡片")

        col1, col2, col3, col4 = self.adapter.layout.columns([3, 3, 4, 2])

        with col1:
            hanzi_config = ComponentConfig(
                key="new_card_hanzi",
                label="汉字",
                placeholder="输入汉字..."
            )
            new_hanzi = self.adapter.inputs.text_input(hanzi_config)

        with col2:
            pinyin_config = ComponentConfig(
                key="new_card_pinyin",
                label="拼音",
                placeholder="输入拼音..."
            )
            new_pinyin = self.adapter.inputs.text_input(pinyin_config)

        with col3:
            english_config = ComponentConfig(
                key="new_card_english",
                label="英文",
                placeholder="输入英文..."
            )
            new_english = self.adapter.inputs.text_input(english_config)

        with col4:
            add_config = ComponentConfig(
                key="add_new_card",
                label="添加卡片"
            )
            if self.adapter.inputs.button(add_config):
                if new_hanzi.strip():
                    new_card = Card.create_new(
                        hanzi=new_hanzi.strip(),
                        pinyin=new_pinyin.strip(),
                        english=new_english.strip()
                    )
                    self.edit_session.record_addition(new_card)

                    # Clear input fields
                    st.session_state.new_card_hanzi = ""
                    st.session_state.new_card_pinyin = ""
                    st.session_state.new_card_english = ""

                    self.adapter.notifications.show_message(
                        f"已添加新卡片: {new_hanzi}",
                        NotificationLevel.SUCCESS
                    )
                else:
                    self.adapter.notifications.show_message(
                        "请至少输入汉字",
                        NotificationLevel.WARNING
                    )

    def _record_edit(self, card_id: str, field: str, old_value: str, new_value: str) -> None:
        """Record an edit operation for apply flow."""
        if old_value != new_value:
            self.edit_session.record_edit(card_id, field, old_value, new_value)

    def _render_search(self) -> None:
        """Render search input."""
        search_config = ComponentConfig(
            key="table_editor_search",
            label="搜索卡片",
            help_text="输入汉字、拼音或英文来搜索卡片"
        )
        
        new_search = self.adapter.inputs.text_input(
            search_config, value=self.search_term, placeholder="搜索..."
        )
        
        if new_search != self.search_term:
            self.search_term = new_search
            self.current_page = 0  # Reset to first page
            debounce_form_input("table_search", new_search)
    
    def _render_pagination(self, total_pages: int) -> None:
        """Render pagination controls."""
        if total_pages <= 1:
            return
        
        col1, col2, col3, col4, col5 = self.adapter.layout.columns([1, 1, 2, 1, 1])
        
        with col1:
            first_config = ComponentConfig(
                key="table_first_page",
                label="⏮️ 首页",
                disabled=self.current_page <= 0
            )
            if self.adapter.inputs.button(first_config):
                self.current_page = 0
        
        with col2:
            prev_config = ComponentConfig(
                key="table_prev_page",
                label="◀️ 上页",
                disabled=self.current_page <= 0
            )
            if self.adapter.inputs.button(prev_config):
                self.current_page = max(0, self.current_page - 1)
        
        with col3:
            self.adapter.markdown(
                f"**第 {self.current_page + 1} 页，共 {total_pages} 页**"
            )
        
        with col4:
            next_config = ComponentConfig(
                key="table_next_page",
                label="▶️ 下页",
                disabled=self.current_page >= total_pages - 1
            )
            if self.adapter.inputs.button(next_config):
                self.current_page = min(total_pages - 1, self.current_page + 1)
        
        with col5:
            last_config = ComponentConfig(
                key="table_last_page",
                label="⏭️ 末页",
                disabled=self.current_page >= total_pages - 1
            )
            if self.adapter.inputs.button(last_config):
                self.current_page = total_pages - 1
    
    def _filter_cards(self, cards: CardCollection) -> List[Card]:
        """Filter cards based on search term."""
        if not self.search_term:
            return list(cards)
        
        search_lower = self.search_term.lower()
        filtered = []
        
        for card in cards:
            if (search_lower in card.hanzi.lower() or
                search_lower in card.pinyin.lower() or
                search_lower in card.english.lower()):
                filtered.append(card)
        
        return filtered
    
    def _render_table_header(self) -> None:
        """Render table header."""
        self.adapter.markdown("### 📝 卡片编辑器")
        
        # Table header
        col1, col2, col3, col4 = self.adapter.layout.columns([3, 3, 4, 1])
        with col1:
            self.adapter.markdown("**汉字**")
        with col2:
            self.adapter.markdown("**拼音**")
        with col3:
            self.adapter.markdown("**英文**")
        with col4:
            self.adapter.markdown("**操作**")
    
    def _render_table_rows(self, page_cards: List[Card],
                          all_cards: CardCollection) -> CardCollection:
        """Render table rows with framework-agnostic interface and edit tracking."""
        updated_cards = CardCollection(list(all_cards))

        for i, card in enumerate(page_cards):
            # Show pending edits for this card
            pending_edits = self.edit_session.edits.get(card.id, {})
            is_deleted = card.id in self.edit_session.deleted_cards

            # Apply visual styling for pending changes
            if pending_edits or is_deleted:
                style_class = "deleted" if is_deleted else "edited"
                self.adapter.markdown(f'<div class="card-row {style_class}">', unsafe_allow_html=True)

            col1, col2, col3, col4 = self.adapter.layout.columns([3, 3, 4, 1])

            with col1:
                # Show current value or pending edit
                current_hanzi = pending_edits.get('hanzi', CardEdit('', '', '', card.hanzi)).new_value if 'hanzi' in pending_edits else card.hanzi

                hanzi_config = ComponentConfig(
                    key=f"hanzi_{card.id}",
                    label="",
                    disabled=not self.config.editable or is_deleted
                )
                new_hanzi = self.adapter.inputs.text_input(
                    hanzi_config, value=current_hanzi
                )
                if new_hanzi != card.hanzi and not is_deleted:
                    self._record_edit(card.id, 'hanzi', card.hanzi, new_hanzi)

            with col2:
                # Show current value or pending edit
                current_pinyin = pending_edits.get('pinyin', CardEdit('', '', '', card.pinyin)).new_value if 'pinyin' in pending_edits else card.pinyin

                pinyin_config = ComponentConfig(
                    key=f"pinyin_{card.id}",
                    label="",
                    disabled=not self.config.editable or is_deleted
                )
                new_pinyin = self.adapter.inputs.text_input(
                    pinyin_config, value=current_pinyin
                )
                if new_pinyin != card.pinyin and not is_deleted:
                    self._record_edit(card.id, 'pinyin', card.pinyin, new_pinyin)

            with col3:
                # Show current value or pending edit
                current_english = pending_edits.get('english', CardEdit('', '', '', card.english)).new_value if 'english' in pending_edits else card.english

                english_config = ComponentConfig(
                    key=f"english_{card.id}",
                    label="",
                    disabled=not self.config.editable or is_deleted
                )
                new_english = self.adapter.inputs.text_input(
                    english_config, value=current_english
                )
                if new_english != card.english and not is_deleted:
                    self._record_edit(card.id, 'english', card.english, new_english)

            with col4:
                if self.config.show_delete_button and not is_deleted:
                    delete_config = ComponentConfig(
                        key=f"delete_{card.id}",
                        label="🗑️",
                        help_text="删除此卡片"
                    )
                    if self.adapter.inputs.button(delete_config):
                        self.edit_session.record_deletion(card.id)
                        self.adapter.notifications.show_message(
                            f"已标记删除卡片: {card.hanzi}",
                            NotificationLevel.INFO
                        )
                elif is_deleted:
                    # Show restore button for deleted cards
                    restore_config = ComponentConfig(
                        key=f"restore_{card.id}",
                        label="↩️",
                        help_text="恢复此卡片"
                    )
                    if self.adapter.inputs.button(restore_config):
                        self.edit_session.deleted_cards.discard(card.id)
                        self.adapter.notifications.show_message(
                            f"已恢复卡片: {card.hanzi}",
                            NotificationLevel.INFO
                        )

            # Close styling div if needed
            if pending_edits or is_deleted:
                self.adapter.markdown('</div>', unsafe_allow_html=True)

        return updated_cards
    
    def _record_edit(self, card_id: str, field: str, old_value: str, new_value: str) -> None:
        """Record an edit operation for apply flow."""
        if old_value != new_value:
            self.edit_session.record_edit(card_id, field, old_value, new_value)
    
    def _render_action_buttons(self, cards: CardCollection) -> bool:
        """Render action buttons and return refresh flag."""
        needs_refresh = False
        
        col1, col2, col3, col4 = self.adapter.layout.columns([1, 1, 1, 1])
        
        with col1:
            if self.config.show_add_button:
                add_config = ComponentConfig(
                    key="add_card_btn",
                    label="➕ 添加卡片"
                )
                if self.adapter.inputs.button(add_config):
                    new_card = Card.create_new("", "", "")
                    cards.add_card(new_card)
                    self.adapter.notifications.show_message(
                        "已添加新卡片", NotificationLevel.SUCCESS
                    )
                    needs_refresh = True
        
        with col2:
            apply_config = ComponentConfig(
                key="apply_edits_btn",
                label="✅ 应用更改"
            )
            if self.adapter.inputs.button(apply_config):
                applied_count = self._apply_pending_edits(cards)
                if applied_count > 0:
                    self.adapter.notifications.show_message(
                        f"已应用 {applied_count} 个更改",
                        NotificationLevel.SUCCESS
                    )
                    needs_refresh = True
                else:
                    self.adapter.notifications.show_message(
                        "没有待应用的更改", NotificationLevel.INFO
                    )
        
        with col3:
            cancel_config = ComponentConfig(
                key="cancel_edits_btn",
                label="❌ 取消更改"
            )
            if self.adapter.inputs.button(cancel_config):
                self.edit_session.clear()
                self.adapter.notifications.show_message(
                    "已取消所有更改", NotificationLevel.INFO
                )
                needs_refresh = True

        with col4:
            if self.edit_session.has_changes():
                change_summary = self.edit_session.get_change_summary()
                self.adapter.markdown(f"**待更改:** {change_summary}")
            else:
                self.adapter.markdown("**无待更改**")

        return needs_refresh
    
    def _apply_pending_edits(self, cards: CardCollection) -> int:
        """Apply pending edits to cards using edit session."""
        if not self.edit_session.has_changes():
            return 0

        # Count total changes
        edit_count = sum(len(fields) for fields in self.edit_session.edits.values())
        delete_count = len(self.edit_session.deleted_cards)
        add_count = len(self.edit_session.added_cards)
        total_changes = edit_count + delete_count + add_count

        # Apply all changes through the edit session
        updated_cards = self._apply_all_changes(cards)

        # Clear the session
        self.edit_session.clear()

        return total_changes
    
    def _render_legacy_fallback(self, cards: CardCollection) -> Tuple[CardCollection, bool]:
        """Fallback to legacy editor when stable IDs are disabled."""
        self.adapter.notifications.show_message(
            "使用传统编辑器 (稳定ID功能未启用)",
            NotificationLevel.INFO
        )
        
        # Convert to legacy format and render simple editor
        legacy_cards = cards.to_legacy_format()
        
        # Simple legacy editor
        self.adapter.subheader("卡片编辑")
        for i, card_dict in enumerate(legacy_cards):
            col1, col2, col3 = self.adapter.layout.columns([1, 1, 1])
            
            with col1:
                hanzi_config = ComponentConfig(
                    key=f"legacy_hanzi_{i}",
                    label=f"汉字 {i+1}"
                )
                card_dict['hanzi'] = self.adapter.inputs.text_input(
                    hanzi_config, value=card_dict['hanzi']
                )
            
            with col2:
                pinyin_config = ComponentConfig(
                    key=f"legacy_pinyin_{i}",
                    label=f"拼音 {i+1}"
                )
                card_dict['pinyin'] = self.adapter.inputs.text_input(
                    pinyin_config, value=card_dict['pinyin']
                )
            
            with col3:
                english_config = ComponentConfig(
                    key=f"legacy_english_{i}",
                    label=f"英文 {i+1}"
                )
                card_dict['english'] = self.adapter.inputs.text_input(
                    english_config, value=card_dict['english']
                )
        
        # Convert back to CardCollection
        updated_cards = CardCollection.from_legacy_format(legacy_cards)
        return updated_cards, False


def render_table_editor(cards: CardCollection, 
                       config: TableEditorConfig = None) -> Tuple[CardCollection, bool]:
    """
    Render table editor using current UI adapter.
    
    Args:
        cards: CardCollection to edit
        config: Editor configuration
        
    Returns:
        Tuple[CardCollection, bool]: (updated_cards, needs_refresh)
    """
    adapter = get_ui_adapter()
    editor = TableEditor(adapter, config)
    return editor.render(cards)


def use_table_editor() -> bool:
    """Check if table editor should be used."""
    return get_feature_flag('table_editor', False)
