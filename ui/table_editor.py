"""
Scalable table editor for card management.
Replaces tabbed editor with framework-agnostic table interface.
"""

import math
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
import streamlit as st

from core.feature_flags import get_feature_flag
from services.card_models import Card, CardCollection, use_stable_card_ids
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
from ui.debounce import debounce_form_input, form_context


@dataclass
class TableEditorConfig:
    """Configuration for table editor."""
    page_size: int = 10
    show_search: bool = True
    show_pagination: bool = True
    show_add_button: bool = True
    show_delete_button: bool = True
    editable: bool = True


@dataclass
class EditOperation:
    """Represents an edit operation on a card."""
    card_id: str
    field: str
    old_value: str
    new_value: str


class TableEditor:
    """Framework-agnostic table editor for cards."""
    
    def __init__(self, adapter: UIAdapter, config: TableEditorConfig = None):
        self.adapter = adapter
        self.config = config or TableEditorConfig()
        self.pending_edits: Dict[str, Dict[str, str]] = {}
        self.search_term: str = ""
        self.current_page: int = 0
    
    def render(self, cards: CardCollection) -> Tuple[CardCollection, bool]:
        """
        Render table editor and return updated cards and refresh flag.
        
        Returns:
            Tuple[CardCollection, bool]: (updated_cards, needs_refresh)
        """
        if not use_stable_card_ids():
            # Fallback to legacy editor
            return self._render_legacy_fallback(cards)
        
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
        """Render table rows and collect edits."""
        updated_cards = CardCollection(list(all_cards))
        
        for i, card in enumerate(page_cards):
            row_key = f"row_{card.id}"
            
            col1, col2, col3, col4 = self.adapter.layout.columns([3, 3, 4, 1])
            
            with col1:
                hanzi_config = ComponentConfig(
                    key=f"hanzi_{card.id}",
                    label="",
                    disabled=not self.config.editable
                )
                new_hanzi = self.adapter.inputs.text_input(
                    hanzi_config, value=card.hanzi
                )
                if new_hanzi != card.hanzi:
                    self._record_edit(card.id, 'hanzi', card.hanzi, new_hanzi)
            
            with col2:
                pinyin_config = ComponentConfig(
                    key=f"pinyin_{card.id}",
                    label="",
                    disabled=not self.config.editable
                )
                new_pinyin = self.adapter.inputs.text_input(
                    pinyin_config, value=card.pinyin
                )
                if new_pinyin != card.pinyin:
                    self._record_edit(card.id, 'pinyin', card.pinyin, new_pinyin)
            
            with col3:
                english_config = ComponentConfig(
                    key=f"english_{card.id}",
                    label="",
                    disabled=not self.config.editable
                )
                new_english = self.adapter.inputs.text_input(
                    english_config, value=card.english
                )
                if new_english != card.english:
                    self._record_edit(card.id, 'english', card.english, new_english)
            
            with col4:
                if self.config.show_delete_button:
                    delete_config = ComponentConfig(
                        key=f"delete_{card.id}",
                        label="🗑️"
                    )
                    if self.adapter.inputs.button(delete_config):
                        updated_cards.remove_card(card.id)
                        self.adapter.notifications.show_message(
                            f"已删除卡片: {card.hanzi}",
                            NotificationLevel.INFO
                        )
        
        return updated_cards
    
    def _record_edit(self, card_id: str, field: str, old_value: str, new_value: str) -> None:
        """Record an edit operation."""
        if card_id not in self.pending_edits:
            self.pending_edits[card_id] = {}
        
        self.pending_edits[card_id][field] = new_value
        debounce_form_input(f"edit_{card_id}_{field}", new_value)
    
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
                self.pending_edits.clear()
                self.adapter.notifications.show_message(
                    "已取消所有更改", NotificationLevel.INFO
                )
                needs_refresh = True
        
        with col4:
            if self.pending_edits:
                self.adapter.markdown(f"**待应用: {len(self.pending_edits)} 个更改**")
        
        return needs_refresh
    
    def _apply_pending_edits(self, cards: CardCollection) -> int:
        """Apply pending edits to cards."""
        applied_count = 0
        
        for card_id, edits in self.pending_edits.items():
            if cards.update_card(
                card_id,
                hanzi=edits.get('hanzi'),
                pinyin=edits.get('pinyin'),
                english=edits.get('english')
            ):
                applied_count += 1
        
        self.pending_edits.clear()
        return applied_count
    
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
