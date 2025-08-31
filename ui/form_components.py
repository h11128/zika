"""
Form-semantic UI components with atomic commits and debouncing.
Removes side effects from UI components and provides clean state management.
"""

import streamlit as st
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass

from core.feature_flags import get_feature_flag
from ui.debounce import (
    debounce_immediate, debounce_form_input, form_context,
    get_pending_value, flush_debounced_changes
)
from ui.state import set_option, invalidate_preview_cache


@dataclass
class ComponentResult:
    """Result from a form component interaction."""
    value: Any
    changed: bool
    needs_refresh: bool = False


class FormSection:
    """A section of form components with atomic commit semantics."""
    
    def __init__(self, name: str, auto_commit: bool = True):
        self.name = name
        self.auto_commit = auto_commit
        self.changes: Dict[str, Any] = {}
        self.needs_refresh = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.auto_commit and self.changes:
            self.commit()
    
    def add_change(self, key: str, value: Any, immediate: bool = False) -> None:
        """Add a change to this form section."""
        self.changes[key] = value
        
        if immediate:
            # Apply immediately for interactive components
            debounce_immediate(key, value)
        else:
            # Batch for form inputs
            debounce_form_input(key, value)
    
    def commit(self) -> bool:
        """Commit all changes in this section."""
        if not self.changes:
            return False
        
        try:
            # Flush debounced changes
            changeset = flush_debounced_changes()
            
            # Check if refresh needed
            self.needs_refresh = (
                changeset.affects_layout or 
                changeset.affects_style or 
                changeset.affects_processing
            )
            
            self.changes.clear()
            return True
        except Exception:
            return False


def layout_options_section() -> Tuple[float, float, int, int, bool]:
    """
    Render layout options with form semantics.
    Returns: (gap, margin, layout_rows, layout_cols, auto_fill)
    """
    with FormSection("layout_options") as form:
        st.subheader("📐 布局设置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gap setting with debouncing
            current_gap = get_pending_value('gap_cm', 0.5)
            gap_cm = st.slider(
                "卡片间距 (cm)",
                min_value=0.0, max_value=2.0, value=current_gap, step=0.1,
                key="gap_slider",
                help="卡片之间的间距"
            )
            if gap != current_gap:
                form.add_change('gap_cm', gap, immediate=True)
            
            # Rows setting
            current_rows = get_pending_value('layout_rows', 2)
            layout_rows = st.number_input(
                "行数", min_value=1, max_value=10, value=current_rows,
                key="rows_input"
            )
            if rows != current_rows:
                form.add_change('layout_rows', rows)
        
        with col2:
            # Margin setting with debouncing
            current_margin = get_pending_value('margin_cm', 1.0)
            margin_cm = st.slider(
                "页面边距 (cm)",
                min_value=0.0, max_value=3.0, value=current_margin, step=0.1,
                key="margin_slider",
                help="页面四周的边距"
            )
            if margin != current_margin:
                form.add_change('margin_cm', margin, immediate=True)
            
            # Cols setting
            current_cols = get_pending_value('layout_cols', 3)
            layout_cols = st.number_input(
                "列数", min_value=1, max_value=10, value=current_cols,
                key="cols_input"
            )
            if cols != current_cols:
                form.add_change('layout_cols', cols)
        
        # Auto fill setting
        current_auto_fill = get_pending_value('layout_auto_fill', True)
        layout_auto_fill = st.checkbox(
            "自动填充页面",
            value=current_auto_fill,
            key="auto_fill_checkbox",
            help="自动调整卡片大小以填充页面"
        )
        if auto_fill != current_auto_fill:
            form.add_change('layout_auto_fill', layout_auto_fill, immediate=True)
    
    return gap, margin, layout_rows, layout_cols, auto_fill


def typography_section() -> Tuple[int, int, int, str]:
    """
    Render typography options with form semantics.
    Returns: (hanzi_font_size, pinyin_font_size, english_font_size, hanzi_font_family)
    """
    with FormSection("typography") as form:
        st.subheader("🔤 字体设置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Hanzi font size
            current_hanzi = get_pending_value('hanzi_font_size', 48)
            hanzi_font_size = st.slider(
                "汉字字体大小",
                min_value=20, max_value=100, value=current_hanzi, step=2,
                key="font_hanzi_slider"
            )
            if hanzi_font_size != current_hanzi:
                form.add_change('hanzi_font_size', hanzi_font_size, immediate=True)
            
            # Pinyin font size
            current_pinyin = get_pending_value('pinyin_font_size', 18)
            pinyin_font_size = st.slider(
                "拼音字体大小",
                min_value=10, max_value=40, value=current_pinyin, step=1,
                key="font_pinyin_slider"
            )
            if pinyin_font_size != current_pinyin:
                form.add_change('pinyin_font_size', pinyin_font_size, immediate=True)
        
        with col2:
            # English font size
            current_english = get_pending_value('english_font_size', 14)
            english_font_size = st.slider(
                "英文字体大小",
                min_value=8, max_value=30, value=current_english, step=1,
                key="font_english_slider"
            )
            if english_font_size != current_english:
                form.add_change('english_font_size', english_font_size, immediate=True)
            
            # Hanzi font family
            from core.constants import HANZI_FONT_OPTIONS
            current_font = get_pending_value('hanzi_font_family', 'SimHei')
            try:
                font_index = HANZI_FONT_OPTIONS.index(current_font)
            except ValueError:
                font_index = 0
            
            hanzi_font_family = st.selectbox(
                "汉字字体",
                options=HANZI_FONT_OPTIONS,
                index=font_index,
                key="hanzi_font_select"
            )
            if hanzi_font_family != current_font:
                form.add_change('hanzi_font_family', hanzi_font_family, immediate=True)
    
    return hanzi_font_size, pinyin_font_size, english_font_size, hanzi_font_family


def visual_options_section() -> Tuple[str, str]:
    """
    Render visual options with form semantics.
    Returns: (background_color, page_size)
    """
    with FormSection("visual_options") as form:
        st.subheader("🎨 视觉设置")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Background color without side effects
            current_color = get_pending_value('background_color', '#ffffff')
            background_color = render_color_palette_clean(current_color)
            if background_color != current_color:
                form.add_change('background_color', background_color, immediate=True)
        
        with col2:
            # Page size
            page_sizes = ['A4', 'Letter', 'A3', 'A5']
            current_page_size = get_pending_value('page_size', 'A4')
            try:
                page_index = page_sizes.index(current_page_size)
            except ValueError:
                page_index = 0
            
            page_size = st.selectbox(
                "页面大小",
                options=page_sizes,
                index=page_index,
                key="page_size_select"
            )
            if page_size != current_page_size:
                form.add_change('page_size', page_size)
    
    return background_color, page_size


def render_color_palette_clean(current_color: str) -> str:
    """
    Render color palette without side effects.
    Returns the selected color without triggering cache invalidation.
    """
    from core.constants import PRESET_COLORS
    
    try:
        current_index = PRESET_COLORS.index(current_color)
    except ValueError:
        current_index = 0
    
    return st.selectbox(
        "选择背景色",
        options=PRESET_COLORS,
        index=current_index,
        key="color_selector_clean"
    )

def input_section_clean() -> str:
    """
    Render input section without side effects.
    Returns the input text without triggering segmentation.
    """
    st.subheader("📝 输入文本")
    
    current_text = get_pending_value('input_text', '')
    
    # Text area without auto-segmentation side effects
    new_text = st.text_area(
        "输入中文文本（每行一个词或短语）",
        value=current_text,
        height_cm=200,
        key="input_text_clean",
        help="输入要制作卡片的中文文本，每行一个词或短语"
    )
    
    # Only update if significantly different (avoid constant updates)
    if new_text != current_text and len(new_text.strip()) != len(current_text.strip()):
        debounce_form_input('input_text', new_text)
    
    # Manual segmentation button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 重新分词", key="manual_segment_btn"):
            # Trigger segmentation explicitly
            try:
                from core.feature_flags import use_state_service
                if use_state_service():
                    set_option('input_text', new_text)
                    invalidate_preview_cache("manual segmentation")
                else:
                    st.session_state.input_text = new_text
                    from services.cache_v2 import clear_preview_cache
                    clear_preview_cache()
                st.rerun()
            except Exception:
                st.session_state.input_text = new_text
                st.rerun()
    
    return new_text


def options_section_clean() -> Tuple[bool, bool, str, float]:
    """
    Render options section without side effects.
    Returns: (auto_pinyin, auto_translate, page_size, card_size)
    """
    with FormSection("options") as form:
        st.subheader("⚙️ 选项")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Auto pinyin
            current_auto_pinyin = get_pending_value('auto_pinyin', True)
            auto_pinyin = st.checkbox(
                "自动添加拼音",
                value=current_auto_pinyin,
                key="auto_pinyin_clean"
            )
            if auto_pinyin != current_auto_pinyin:
                form.add_change('auto_pinyin', auto_pinyin, immediate=True)
            
            # Auto translate
            current_auto_translate = get_pending_value('auto_translate', True)
            auto_translate = st.checkbox(
                "自动翻译",
                value=current_auto_translate,
                key="auto_translate_clean"
            )
            if auto_translate != current_auto_translate:
                form.add_change('auto_translate', auto_translate, immediate=True)
        
        with col2:
            # Page size
            page_sizes = ['A4', 'Letter', 'A3', 'A5']
            current_page_size = get_pending_value('page_size', 'A4')
            try:
                page_index = page_sizes.index(current_page_size)
            except ValueError:
                page_index = 0
            
            page_size = st.selectbox(
                "页面大小",
                options=page_sizes,
                index=page_index,
                key="page_size_clean"
            )
            if page_size != current_page_size:
                form.add_change('page_size', page_size)
            
            # Card size
            current_card_size = get_pending_value('card_size_cm', 5.5)
            card_size_cm = st.slider(
                "卡片大小 (cm)",
                min_value=3.0, max_value=10.0, value=current_card_size, step=0.1,
                key="card_size_clean"
            )
            if card_size != current_card_size:
                form.add_change('card_size_cm', card_size, immediate=True)
    
    return auto_pinyin, auto_translate, page_size, card_size


# Feature flag integration
def use_clean_components() -> bool:
    """Check if clean components should be used."""
    return False
