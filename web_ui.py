#!/usr/bin/env python3
"""
Chinese Character Learning Cards - Web UI
Simple web interface for generating learning cards with real-time preview.
"""

import streamlit as st
import os
import sys
from typing import List, Dict

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="中文学习卡片生成器",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pinyin_utils import hanzi_to_pinyin, contains_chinese
from dict_utils import create_default_dict
from layout_pptx import PPTXCardGenerator
from layout_pdf import PDFCardGenerator

# Import constants and cache functions
from core.constants import (
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR, HANZI_FONT_OPTIONS,
    PRESET_COLORS, DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL,
    DEFAULT_FONT_HANZI, DEFAULT_FONT_PINYIN, DEFAULT_FONT_ENGLISH,
    DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN
)
from services.cache import cached_create_page_preview_html, cached_create_simple_grid_html, create_preview_html
from services.export import export_cards
from services.processing import parse_input_text, auto_segment_text, generate_missing_data
from core.state import (
    initialize_session_state, get_processed_cards, get_current_page, get_layout_settings,
    get_ui_preferences, set_processed_cards, set_current_page, clear_export_data,
    update_last_params, check_params_changed, clear_processed_cards, get_dictionary
)
from ui.components import render_color_palette, render_page_navigation, render_preview_section, render_page_info
from ui.sections import (
    render_sidebar, render_input_section, render_options_section,
    render_advanced_options, render_preview_section_wrapper, render_export_section
)
from ui.styles import apply_global_styles, render_sticky_wrapper_end

# Apply global styles
apply_global_styles()

# Initialize session state
initialize_session_state()







# Sidebar
render_sidebar()

# Main UI
st.title("🀄 Chinese Learning Cards Generator")
st.markdown("输入汉字，自动生成拼音和翻译，制作学习卡片")
st.markdown("💡 **新功能**: 支持空格分隔输入和智能自动分词")

# Create two columns
col1, col2 = st.columns([1, 1])

with col1:
    # Input section
    cards = render_input_section()

    # Options
    auto_pinyin, auto_translate, page_size, card_size = render_options_section()

    # Advanced options
    gap, margin, font_hanzi, font_pinyin, font_english, rows, cols = render_advanced_options()


with col2:
    # UI preferences and preview mode
    prefs = get_ui_preferences()
    hanzi_font = prefs['hanzi_font']
    background_color = prefs['background_color']

    preview_mode = st.radio(
        "预览模式",
        ["📄 完整页面", "🔲 简单网格"],
        horizontal=True,
        help="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
    )

    # Process cards and generate missing data
    if cards:
        # Determine current cards source for comparison
        current_source = f"cards:{len(cards)}:{hash(str(cards))}"

        # Check if we need to reprocess cards
        processed_cards = get_processed_cards()
        need_reprocess = (
            st.session_state.cards_source != current_source or
            len(processed_cards) != len(cards) or
            not processed_cards
        )

        # Clear export data if cards changed
        if need_reprocess:
            clear_export_data()

        # Generate missing data only if needed
        if need_reprocess:
            processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate, get_dictionary())
            set_processed_cards(processed_cards, current_source)
    else:
        processed_cards = get_processed_cards()

    if cards:

        # Calculate total pages (rows x cols per page)
        layout = get_layout_settings()
        cards_per_page = max(1, layout['rows'] * layout['cols'])
        total_pages = max(1, (len(processed_cards) + cards_per_page - 1) // cards_per_page)

        # Check if parameters changed (reset to first page if they did)
        current_params = {
            'card_size': card_size,
            'gap': gap,
            'margin': margin,
            'page_size': page_size,
            'font_hanzi': font_hanzi,
            'font_pinyin': font_pinyin,
            'font_english': font_english,
            'hanzi_font': hanzi_font,
            'background_color': background_color,
            'rows': layout['rows'],
            'cols': layout['cols'],
            'auto_fill': layout['auto_fill'],
            'total_cards': len(processed_cards)
        }

        if check_params_changed(current_params):
            set_current_page(0)
            update_last_params(current_params)
            # Clear export data when parameters change
            clear_export_data()

        # Reset current page if it's out of range
        current_page = get_current_page()
        if current_page >= total_pages:
            set_current_page(0)

        # Page navigation
        render_page_navigation(total_pages)

        # 渲染预览（封装函数，缓存+占位符，降低其它UI重绘）
        render_preview_section(
            processed_cards, preview_mode,
            card_size, gap, margin,
            font_hanzi, font_pinyin, font_english,
            page_size, hanzi_font, background_color,
            layout['rows'], layout['cols'], layout['auto_fill']
        )

        # Show card count and page info
        render_page_info(processed_cards, cards_per_page, total_pages)

        # 调试信息块已移除，保持界面简洁


        # Card editing section
        if len(processed_cards) > 0:
            with st.expander("✏️ 编辑当前页卡片", expanded=False):
                current_page = get_current_page()
                st.write(f"编辑第 {current_page + 1} 页的卡片:")

                # Get cards for current page
                start_idx = current_page * cards_per_page
                end_idx = min(start_idx + cards_per_page, len(processed_cards))
                current_page_cards = processed_cards[start_idx:end_idx]

                if current_page_cards:
                    tabs = st.tabs([f"卡片 {start_idx + i + 1}: {card['hanzi']}" for i, card in enumerate(current_page_cards)])

                    for i, (tab, card) in enumerate(zip(tabs, current_page_cards)):
                        with tab:
                            col_e1, col_e2, col_e3 = st.columns(3)

                            actual_idx = start_idx + i
                            with col_e1:
                                new_hanzi = st.text_input(f"汉字", value=card['hanzi'], key=f"hanzi_{actual_idx}")
                            with col_e2:
                                new_pinyin = st.text_input(f"拼音", value=card['pinyin'], key=f"pinyin_{actual_idx}")
                            with col_e3:
                                new_english = st.text_input(f"英文", value=card['english'], key=f"english_{actual_idx}")

                            # Update the card if values changed
                            if new_hanzi != card['hanzi'] or new_pinyin != card['pinyin'] or new_english != card['english']:
                                processed_cards[actual_idx] = {
                                    'hanzi': new_hanzi,
                                    'pinyin': new_pinyin,
                                    'english': new_english
                                }

    else:
        # Clear processed cards if no input
        if get_processed_cards():
            clear_processed_cards()
        st.components.v1.html(create_preview_html([]), height=650)
    # Close sticky wrapper for the entire preview column
    render_sticky_wrapper_end()


# Export section
render_export_section(get_processed_cards())


