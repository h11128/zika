"""
UI Sections for the Chinese Character Learning Cards application.
Major page sections: sidebar, input, options, preview, and export.
"""

import streamlit as st
import pandas as pd
import time
from typing import List, Dict, Tuple, Any
from core.config import UIConfig, LayoutConfig, AppConfig
from io import StringIO

from core.constants import (
    HANZI_FONT_OPTIONS, PRESET_COLORS, DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL
)
from core.state import get_ui_preferences, get_layout_settings, get_current_page, set_current_page
from services.processing import parse_input_text, auto_segment_text
from services.cache import create_preview_html
from ui.components import render_color_palette, render_page_navigation, render_preview_section, render_page_info

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

    def safe_call(func, *args, component_name: str = "unknown", **kwargs):
        return func(*args, **kwargs)


def render_sidebar() -> None:
    """Render the sidebar with statistics, export history, and quick links."""
    with st.sidebar:
        st.header("📊 使用统计")

        # Dictionary stats
        dict_stats = st.session_state.dictionary.get_statistics()
        st.metric("内置词典", f"{dict_stats['mini_dict_entries']} 词")
        st.metric("累计生成卡片", st.session_state.total_cards_generated)

        # Export history
        if st.session_state.export_history:
            st.subheader("📥 导出历史")
            for i, record in enumerate(reversed(st.session_state.export_history[-5:])):  # Show last 5
                with st.expander(f"{record['format'].upper()} - {record['cards']}张"):
                    st.write(f"时间: {record['time']}")
                    st.write(f"卡片: {record['cards']}张")
                    st.write(f"格式: {record['format'].upper()}")

        # Quick links
        st.markdown("### 🔗 快速链接")
        st.markdown("- [项目文档](https://github.com)")
        st.markdown("- [问题反馈](https://github.com)")
        st.markdown("- [使用教程](https://github.com)")


@with_error_boundary("input_section")
def render_input_section() -> List[Dict[str, str]]:
    """Render the input section and return parsed cards."""
    st.header("📝 输入")

    # Input method selection
    input_method = st.radio(
        "选择输入方式",
        ["手动输入", "上传CSV文件"],
        horizontal=True,
        key="input_method"
    )

    cards = []

    if input_method == "手动输入":
        # Template selection
        templates = {
            "自定义": "",
            "数字": "一 二 三 四 五 六 七 八 九 十",
            "颜色": "红 橙 黄 绿 蓝 紫 黑 白 灰 粉",
            "家庭": "爸爸 妈妈 哥哥 姐姐 弟弟 妹妹 爷爷 奶奶",
            "食物": "米 面 肉 鱼 蛋 奶 茶 水 糖"
        }

        selected_template = st.selectbox("选择模板", list(templates.keys()), key="template_select")
        st.markdown('<span data-testid="select-template" style="display:none"></span>', unsafe_allow_html=True)

        # Determine default text from template selection
        default_text = templates[st.session_state.template_select]

        # Initialize persistent input state
        if 'last_template' not in st.session_state:
            st.session_state.last_template = st.session_state.template_select
        if 'input_text' not in st.session_state:
            st.session_state.input_text = default_text

        # If user changed template, update input to that template's default
        if st.session_state.template_select != st.session_state.last_template:
            st.session_state.input_text = templates[st.session_state.template_select]
            st.session_state.last_template = st.session_state.template_select

        # Apply pending segmentation BEFORE widget instantiation
        if st.session_state.get('apply_segmentation', False):
            if st.session_state.input_text.strip():
                # Use click-time snapshot (do NOT persist it to checkbox state).
                # Snapshot should only influence this computation call.
                preserve_snapshot = st.session_state.pop('pending_preserve_duplicates', st.session_state.get('preserve_duplicates', False))
                preserve_duplicates = bool(preserve_snapshot)
                original_text = st.session_state.input_text.strip()
                new_text = auto_segment_text(original_text, preserve_duplicates=preserve_duplicates)
                # Only update preview-related caches if the text actually changed
                if new_text != original_text:
                    # Use state service for centralized state management
                    try:
                        from core.feature_flags import use_state_service
                        from ui.state import set_option, invalidate_preview_cache

                        if use_state_service():
                            set_option('input_text', new_text)
                            invalidate_preview_cache("segmentation applied")
                        else:
                            # Fallback to legacy approach
                            st.session_state.input_text = new_text
                            try:
                                from services.cache import clear_preview_cache
                                clear_preview_cache()
                            except Exception:
                                pass
                            if 'last_preview_params' in st.session_state:
                                del st.session_state.last_preview_params
                    except ImportError:
                        # Fallback if new modules not available
                        st.session_state.input_text = new_text
                        try:
                            from services.cache import clear_preview_cache
                            clear_preview_cache()
                        except Exception:
                            pass
                        if 'last_preview_params' in st.session_state:
                            del st.session_state.last_preview_params
                else:
                    # No change: keep caches/params intact to avoid unnecessary preview refresh
                    st.session_state.input_text = original_text
            st.session_state.apply_segmentation = False

        # Create columns for text area and button
        col_text, col_btn = st.columns([4, 1])

        with col_text:
            st.text_area(
                "输入汉字（空格分隔）",
                key="input_text",
                height=150,
                placeholder="例如：你好 世界 学习 中文",
                help="输入汉字，用空格分隔。支持单字、词语和短句。"
            )
            st.markdown('<span data-testid="input-hanzi" style="display:none"></span>', unsafe_allow_html=True)

            # 智能分词选项（提前渲染，确保在按钮触发的 rerun 前就完成状态绑定）
            preserve_duplicates = st.checkbox(
                "保留重复词",
                key="preserve_duplicates",
                help="勾选后智能分词将保留重复的词汇，不勾选则自动去重"
            )
            # Debug marker to observe state in E2E without affecting layout
            st.markdown(
                f'<span data-testid="dbg-preserve-duplicates" style="display:none">{int(st.session_state.get("preserve_duplicates", False))}</span>',
                unsafe_allow_html=True
            )

        with col_btn:
            st.write("")  # Add some spacing
            st.write("")  # Add some spacing

            if st.button("🔄 智能分词", use_container_width=True, help="对输入文本进行智能分词"):
                # Capture checkbox state at click time to avoid race conditions
                st.session_state.pending_preserve_duplicates = st.session_state.get('preserve_duplicates', False)
                # Trigger apply on next run; the apply step will read and persist the snapshot
                st.session_state.apply_segmentation = True
                st.rerun()

        # Parse input text
        text_input = st.session_state.input_text
        if text_input.strip():
            cards = parse_input_text(text_input)

    else:  # CSV upload
        st.markdown('<span data-testid="csv-upload" style="display:none"></span>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("选择CSV文件", type=['csv'])
        if uploaded_file is not None:
            try:
                # Read CSV
                stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
                df = pd.read_csv(stringio)

                # Validate columns
                required_cols = ['hanzi']
                if not all(col in df.columns for col in required_cols):
                    st.error(f"CSV文件必须包含以下列: {', '.join(required_cols)}")
                    return []

                # Convert to cards format
                for _, row in df.iterrows():
                    cards.append({
                        'hanzi': str(row['hanzi']),
                        'pinyin': str(row.get('pinyin', '')),
                        'english': str(row.get('english', ''))
                    })

                st.success(f"成功读取 {len(cards)} 张卡片")

            except Exception as e:
                st.error(f"读取CSV文件时出错: {e}")
                return []
        else:
            st.info("请上传CSV文件")

    return cards


def render_options_section() -> Tuple[bool, bool, str, float]:
    """Render the options section and return option values."""

    # Handle auto_fill disable request from button
    if st.session_state.get('_disable_auto_fill_requested', False):
        st.session_state.auto_fill = False
        st.session_state._disable_auto_fill_requested = False
        from services.cache import clear_preview_cache
        clear_preview_cache()
        if 'last_preview_params' in st.session_state:
            del st.session_state.last_preview_params

    st.subheader("⚙️ 选项")
    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        auto_pinyin = st.checkbox("自动生成拼音", value=True)
        st.markdown('<span data-testid="toggle-auto-pinyin" style="display:none"></span>', unsafe_allow_html=True)
        auto_translate = st.checkbox("自动生成翻译", value=True)
        st.markdown('<span data-testid="toggle-auto-translate" style="display:none"></span>', unsafe_allow_html=True)
        translate_order_display = st.selectbox(
            "翻译优先级",
            ["本地优先", "Google优先", "仅本地", "仅Google", "混合模式", "词典混合"],
            index=0,
            key="translate_order_select"
        )
        st.markdown('<span data-testid="select-translate-priority" style="display:none"></span>', unsafe_allow_html=True)
        # Map display text to internal values used by processing layer and store in session
        order_map = {
            "本地优先": "local_first",
            "Google优先": "google_first",
            "仅本地": "local_only",
            "仅Google": "google_only",
            "混合模式": "mixed",
            "词典混合": "dict_mixed",
        }
        new_order = order_map.get(translate_order_display, "local_first")

        # Force reprocessing if order changed
        if getattr(st.session_state, 'translate_order', 'local_first') != new_order:
            if hasattr(st.session_state, 'cards_source'):
                st.session_state.cards_source = None  # Force reprocessing

        st.session_state.translate_order = new_order

        # Debug info
        if new_order != 'local_first':
            st.caption(f"🔄 当前模式: {translate_order_display}")

    with col_opt2:
        # Store previous page size for change detection
        prev_page_size = st.session_state.get('_prev_page_size', 'A4')
        page_size = st.selectbox("页面尺寸", ["A4", "Letter"], index=0)

        # Determine whether auto_fill is enabled (from session state)
        is_auto_fill = bool(st.session_state.get('auto_fill', True))

        # Helper to compute auto card size in cm based on current layout
        def _compute_auto_card_size_cm(page_size_val: str) -> float:
            if page_size_val == "A4":
                page_w_cm, page_h_cm = 21.0, 29.7
            else:  # Letter
                page_w_cm, page_h_cm = 21.59, 27.94
            margin_cm = float(st.session_state.get('margin_cm', 1.0))
            gap_cm = float(st.session_state.get('gap_cm', 0.5))
            rows = int(st.session_state.get('rows', 2))
            cols = int(st.session_state.get('cols', 3))
            avail_w = max(0.0, page_w_cm - 2 * margin_cm)
            avail_h = max(0.0, page_h_cm - 2 * margin_cm)
            size_w = (avail_w - max(0, cols - 1) * gap_cm) / max(1, cols)
            size_h = (avail_h - max(0, rows - 1) * gap_cm) / max(1, rows)
            return max(0.0, min(size_w, size_h))

        if is_auto_fill:
            # Auto-fill: show computed size and provide a toggle to switch to manual
            auto_size_cm = _compute_auto_card_size_cm(page_size)
            st.caption(f"自动填充已开启：卡片大小由布局计算 ≈ {auto_size_cm:.1f} cm")
            if st.button("关闭自动填充以手动调整大小", key="disable_auto_fill_for_manual"):
                # Use a flag to indicate the change, avoid direct session state modification
                st.session_state._disable_auto_fill_requested = True
                st.rerun()
            card_size = auto_size_cm
        else:
            # Manual mode: show slider and auto-disable auto_fill when user adjusts
            prev_card_size = float(st.session_state.get('_prev_card_size', st.session_state.get('card_size', 5.5)))
            card_size = st.slider("卡片大小 (cm)", 4.0, 8.0, float(st.session_state.get('card_size', 5.5)), 0.1, key="card_size_slider")
            # Store the card size for other parts of the app to use
            if 'card_size' not in st.session_state or st.session_state.card_size != card_size:
                st.session_state.card_size = card_size
            if card_size != prev_card_size:
                # Clear cache when card size changes
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                st.session_state._prev_card_size = card_size
                # Note: Don't modify auto_fill here to avoid session state conflicts
                # The auto_fill state should only be changed by the checkbox/button widgets

        # Clear cache if page size changed
        if page_size != prev_page_size:
            from services.cache import clear_preview_cache
            clear_preview_cache()
            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params
            st.session_state._prev_page_size = page_size

    return auto_pinyin, auto_translate, page_size, card_size


def render_improved_card_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render an improved card editor that can handle large numbers of cards."""
    total_cards = len(processed_cards)

    # Initialize edit page state
    if 'edit_page' not in st.session_state:
        st.session_state.edit_page = 0

    # Configuration for editing
    max_tabs_per_page = 8  # Reasonable number of tabs per page
    total_edit_pages = (total_cards + max_tabs_per_page - 1) // max_tabs_per_page

    # Edit mode selection
    st.write("**编辑模式选择:**")
    edit_mode = st.radio(
        "选择编辑方式",
        ["分页编辑", "搜索编辑"],
        horizontal=True,
        help="分页编辑：按页编辑卡片；搜索编辑：搜索特定卡片进行编辑"
    )

    if edit_mode == "分页编辑":
        render_paginated_editor(processed_cards, max_tabs_per_page, total_edit_pages)
    else:
        render_search_editor(processed_cards)


def render_paginated_editor(processed_cards: List[Dict[str, str]], max_tabs_per_page: int, total_edit_pages: int) -> None:
    """Render paginated card editor."""
    total_cards = len(processed_cards)

    # Edit page navigation
    if total_edit_pages > 1:
        st.write(f"**编辑分页导航** (总计 {total_cards} 张卡片，分为 {total_edit_pages} 页)")

        col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 2, 1, 1])

        with col_nav1:
            if st.button("⏮️ 首页", disabled=st.session_state.edit_page <= 0, use_container_width=True, key="edit_first"):
                st.session_state.edit_page = 0
                st.rerun()

        with col_nav2:
            if st.button("◀️ 上页", disabled=st.session_state.edit_page <= 0, use_container_width=True, key="edit_prev"):
                st.session_state.edit_page = max(0, st.session_state.edit_page - 1)
                st.rerun()

        with col_nav3:
            new_edit_page = st.selectbox(
                "编辑页码",
                options=list(range(total_edit_pages)),
                index=st.session_state.edit_page,
                format_func=lambda x: f"第 {x+1} 页 / 共 {total_edit_pages} 页",
                key="edit_page_selector"
            )
            if new_edit_page != st.session_state.edit_page:
                st.session_state.edit_page = new_edit_page
                st.rerun()

        with col_nav4:
            if st.button("▶️ 下页", disabled=st.session_state.edit_page >= total_edit_pages - 1, use_container_width=True, key="edit_next"):
                st.session_state.edit_page = min(total_edit_pages - 1, st.session_state.edit_page + 1)
                st.rerun()

        with col_nav5:
            if st.button("⏭️ 末页", disabled=st.session_state.edit_page >= total_edit_pages - 1, use_container_width=True, key="edit_last"):
                st.session_state.edit_page = total_edit_pages - 1
                st.rerun()

    # Get cards for current edit page
    start_idx = st.session_state.edit_page * max_tabs_per_page
    end_idx = min(start_idx + max_tabs_per_page, total_cards)
    current_edit_cards = processed_cards[start_idx:end_idx]

    st.write(f"**编辑第 {st.session_state.edit_page + 1} 页卡片** (卡片 {start_idx + 1} - {end_idx})")

    if current_edit_cards:
        tabs = st.tabs([f"卡片 {start_idx + i + 1}: {card['hanzi']}" for i, card in enumerate(current_edit_cards)])

        for i, (tab, card) in enumerate(zip(tabs, current_edit_cards)):
            with tab:
                actual_idx = start_idx + i
                render_single_card_editor(card, actual_idx)


def render_search_editor(processed_cards: List[Dict[str, str]]) -> None:
    """Render search-based card editor."""
    st.write("**搜索编辑**")

    # Search input
    search_term = st.text_input(
        "搜索卡片",
        placeholder="输入汉字、拼音或英文来搜索卡片",
        help="支持模糊搜索，输入任意内容来查找匹配的卡片"
    )

    if search_term:
        # Find matching cards
        matching_cards = []
        for i, card in enumerate(processed_cards):
            if (search_term.lower() in card['hanzi'].lower() or
                search_term.lower() in card['pinyin'].lower() or
                search_term.lower() in card['english'].lower()):
                matching_cards.append((i, card))

        if matching_cards:
            st.write(f"找到 {len(matching_cards)} 张匹配的卡片:")

            # Limit search results to avoid too many tabs
            max_search_results = 10
            displayed_cards = matching_cards[:max_search_results]

            if len(matching_cards) > max_search_results:
                st.warning(f"搜索结果过多，只显示前 {max_search_results} 张卡片。请使用更具体的搜索词。")

            tabs = st.tabs([f"卡片 {idx + 1}: {card['hanzi']}" for idx, card in displayed_cards])

            for tab, (actual_idx, card) in zip(tabs, displayed_cards):
                with tab:
                    render_single_card_editor(card, actual_idx)
        else:
            st.info("没有找到匹配的卡片，请尝试其他搜索词。")
    else:
        st.info("请输入搜索词来查找要编辑的卡片。")



def render_single_card_editor(card: Dict[str, str], actual_idx: int) -> None:
    """Render editor for a single card."""
    col_e1, col_e2, col_e3 = st.columns(3)

    with col_e1:
        new_hanzi = st.text_input("汉字", value=card['hanzi'], key=f"edit_hanzi_{actual_idx}")
    with col_e2:
        new_pinyin = st.text_input("拼音", value=card['pinyin'], key=f"edit_pinyin_{actual_idx}")
    with col_e3:
        new_english = st.text_input("英文", value=card['english'], key=f"edit_english_{actual_idx}")

    # Update button for this card
    if st.button(f"更新卡片 {actual_idx + 1}", key=f"update_card_{actual_idx}"):
        st.session_state.processed_cards[actual_idx] = {
            'hanzi': new_hanzi,
            'pinyin': new_pinyin,
            'english': new_english
        }

        # Use state service for centralized invalidation
        try:
            from core.feature_flags import use_state_service
            from ui.state import invalidate_preview_cache

            if use_state_service():
                invalidate_preview_cache("card edited")
            else:
                # Fallback to legacy approach
                st.session_state.export_ready = {}
                st.session_state.export_data = {}
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
        except ImportError:
            # Fallback if new modules not available
            st.session_state.export_ready = {}
            st.session_state.export_data = {}
            from services.cache import clear_preview_cache
            clear_preview_cache()
            if 'last_preview_params' in st.session_state:
                del st.session_state.last_preview_params

        st.success(f"卡片 {actual_idx + 1} 已更新！")
        st.rerun()


def render_advanced_options() -> Tuple[float, float, int, int, int, int, int]: # returns (gap, margin, font_hanzi, font_pinyin, font_english, rows, cols)
    """Render the advanced options section and return advanced option values."""
    with st.expander("🔧 高级选项"):
        # Layout options
        col_layout1, col_layout2 = st.columns(2)
        with col_layout1:
            # Store previous values for change detection (use different keys to avoid conflict)
            prev_gap = st.session_state.get('_prev_gap', 0.5)
            prev_margin = st.session_state.get('_prev_margin', 1.0)
            prev_cols = st.session_state.get('_prev_cols', st.session_state.cols)
            prev_rows = st.session_state.get('_prev_rows', st.session_state.rows)
            prev_auto_fill = st.session_state.get('_prev_auto_fill', st.session_state.auto_fill)

            gap = st.slider("卡片间距 (cm)", 0.2, 1.0, 0.5, 0.1, key="gap_cm")
            margin = st.slider("页面边距 (cm)", 0.5, 2.0, 1.0, 0.1, key="margin_cm")
            cols = st.number_input("每行卡片数 (列)", min_value=1, max_value=10, value=st.session_state.cols, step=1)
            rows = st.number_input("每列卡片数 (行)", min_value=1, max_value=10, value=st.session_state.rows, step=1)
            # Some unit tests patch st.checkbox without supporting **kwargs like key; be resilient
            try:
                auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.auto_fill, key="auto_fill_advanced")
            except TypeError:
                auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.auto_fill)

            # Clear cache if any layout parameter changed
            if (gap != prev_gap or margin != prev_margin or
                cols != prev_cols or rows != prev_rows or auto_fill != prev_auto_fill):
                from services.cache import clear_preview_cache
                clear_preview_cache()
                # Force preview parameter reset
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                # Update the previous values for next comparison
                st.session_state._prev_gap = gap
                st.session_state._prev_margin = margin
                st.session_state._prev_cols = cols
                st.session_state._prev_rows = rows
                st.session_state._prev_auto_fill = auto_fill

                # If auto_fill state changed, trigger a rerun to update the main options UI
                if auto_fill != prev_auto_fill:
                    st.session_state.auto_fill = auto_fill
                    st.rerun()

        with col_layout2:
            # Font selection for Chinese characters
            prev_hanzi_font = st.session_state.get('_prev_hanzi_font', st.session_state.hanzi_font)
            hanzi_font = st.selectbox(
                "汉字字体",
                HANZI_FONT_OPTIONS,
                index=HANZI_FONT_OPTIONS.index(st.session_state.hanzi_font),
                help="选择汉字显示字体，不同字体有不同的视觉效果"
            )

            # Clear cache if font changed
            if hanzi_font != prev_hanzi_font:
                from services.cache import clear_preview_cache
                clear_preview_cache()
                # Force preview parameter reset
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                # Update the previous value for next comparison
                st.session_state._prev_hanzi_font = hanzi_font

            # Background color selection with visual color palette
            st.write("**卡片背景颜色:**")

            st.caption("快速选择颜色：点击下方色块选择背景色")
            render_color_palette(PRESET_COLORS)

            # Custom color input - standard Streamlit color picker
            st.write("**自定义颜色:**")
            # Add a container to make the color picker more visible
            with st.container():
                custom_color = st.color_picker(
                    label="选择颜色",
                    value=st.session_state.background_color,
                    key="custom_color_picker",
                    help="点击选择自定义背景颜色",
                    label_visibility="visible",
                )
                # Visible anchors for test stability and backward compatibility
                st.markdown('<div data-testid="custom-color-picker" style="margin-top: 5px;"></div>', unsafe_allow_html=True)
                st.markdown('<div data-testid="color-picker-anchor" style="display:block"></div>', unsafe_allow_html=True)


            # 允许直接输入十六进制颜色值，便于精确测试与高级用户输入
            hex_input = st.text_input(
                "自定义颜色代码",
                value=st.session_state.background_color,
                key="custom_color_hex",
                help="输入 #RRGGBB 或 #RGB 手动设置背景颜色"
            )
            if isinstance(hex_input, str) and hex_input.startswith('#') and len(hex_input) in (4, 7) \
                and hex_input != st.session_state.background_color:
                st.session_state.background_color = hex_input
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                st.rerun()

            # Show current color below the picker
            st.write("当前颜色:")
            st.markdown(
                f"<div style='width:100px;height:40px;background-color:{st.session_state.background_color};"
                f"border:2px solid #ccc;border-radius:4px;display:flex;align-items:center;justify-content:center;'>"
                f"<span style='color:white;text-shadow:1px 1px 2px black;font-weight:bold;font-size:12px;'>"
                f"{st.session_state.background_color}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Detect color change and update after display so picker is mounted this run
            if custom_color != st.session_state.background_color:
                st.session_state.background_color = custom_color
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                st.rerun()

    # Font size options (moved outside the expander to avoid triple nesting)
    st.write("**字体大小:**")
    col_font1, col_font2, col_font3 = st.columns(3)
    with col_font1:
        font_hanzi = st.slider("汉字", 20, 80, 48, 2, key="font_hanzi")
    with col_font2:
        font_pinyin = st.slider("拼音", 10, 40, 18, 1, key="font_pinyin")
    with col_font3:
        font_english = st.slider("英文", 8, 30, 14, 1, key="font_english")

        # Update session state and clear cache if values changed
        layout_changed = (
            st.session_state.get('rows') != rows or
            st.session_state.get('cols') != cols or
            st.session_state.get('auto_fill') != auto_fill
        )

        font_changed = (
            st.session_state.get('font_hanzi') != font_hanzi or
            st.session_state.get('font_pinyin') != font_pinyin or
            st.session_state.get('font_english') != font_english
        )

        # Use state service for batch updates
        try:
            from core.feature_flags import use_state_service
            from ui.state import set_options_batch, invalidate_preview_cache

            if use_state_service():
                changes = {
                    'rows': rows,
                    'cols': cols,
                    'auto_fill': auto_fill,
                    'hanzi_font': hanzi_font
                }
                changeset = set_options_batch(changes)

                # Invalidate if layout or style changed
                if changeset.affects_layout or changeset.affects_style:
                    invalidate_preview_cache("layout/font changed")
            else:
                # Fallback to legacy approach
                st.session_state.rows = rows
                st.session_state.cols = cols
                st.session_state.auto_fill = auto_fill
                st.session_state.hanzi_font = hanzi_font

                # Clear preview cache if layout or font parameters changed
                if layout_changed or font_changed:
                    from services.cache import clear_preview_cache
                    clear_preview_cache()
                    # Force preview parameter reset
                    if 'last_preview_params' in st.session_state:
                        del st.session_state.last_preview_params
        except ImportError:
            # Fallback if new modules not available
            st.session_state.rows = rows
            st.session_state.cols = cols
            st.session_state.auto_fill = auto_fill
            st.session_state.hanzi_font = hanzi_font

            if layout_changed or font_changed:
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params

    return gap, margin, font_hanzi, font_pinyin, font_english, rows, cols



def _effective_preview_params_from_state(passed: dict) -> dict:
    """Return effective preview params using session_state as source of truth.
    Any value missing in session_state falls back to the passed value.
    """
    ss = st.session_state
    return {
        'card_size': ss.get('card_size', passed.get('card_size')),
        'gap': ss.get('gap_cm', passed.get('gap')),
        'margin': ss.get('margin_cm', passed.get('margin')),
        'font_hanzi': ss.get('font_hanzi', passed.get('font_hanzi')),
        'font_pinyin': ss.get('font_pinyin', passed.get('font_pinyin')),
        'font_english': ss.get('font_english', passed.get('font_english')),
        'page_size': ss.get('page_size', passed.get('page_size')),
        'hanzi_font': ss.get('hanzi_font', passed.get('hanzi_font')),
        'background_color': ss.get('background_color', passed.get('background_color')),
        'rows': ss.get('rows', passed.get('rows')),
        'cols': ss.get('cols', passed.get('cols')),
        'auto_fill': ss.get('auto_fill', passed.get('auto_fill')),
    }


@with_error_boundary("preview_section")
def render_preview_section_wrapper(processed_cards: List[Dict[str, str]],
                                 card_size: float, gap: float, margin: float,
                                 font_hanzi: int, font_pinyin: int, font_english: int,
                                 page_size: str, hanzi_font: str, background_color: str,
                                 rows: int, cols: int, auto_fill: bool) -> None:
    """Render the complete preview section with mode selection and navigation."""
    st.markdown('<div class="preview-sticky">', unsafe_allow_html=True)
    st.header("👀 预览")

    # Preview mode selection
    preview_mode = st.radio(
        "预览模式",
        ["📄 完整页面", "🔲 简单网格"],
        horizontal=True,
        help="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
    )
    # Persist preview mode in session for consistent param tracking
    st.session_state.preview_mode = preview_mode

    # Build effective params using session_state as the source of truth
    passed = {
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'page_size': page_size,
        'hanzi_font': hanzi_font,
        'background_color': background_color,
        'rows': rows,
        'cols': cols,
        'auto_fill': auto_fill,
    }
    eff = _effective_preview_params_from_state(passed)
    card_size, gap, margin = eff['card_size'], eff['gap'], eff['margin']
    font_hanzi, font_pinyin, font_english = eff['font_hanzi'], eff['font_pinyin'], eff['font_english']
    page_size, hanzi_font, background_color = eff['page_size'], eff['hanzi_font'], eff['background_color']
    rows, cols, auto_fill = eff['rows'], eff['cols'], eff['auto_fill']

    if processed_cards:
        # Calculate total pages (rows x cols per page)
        cards_per_page = max(1, rows * cols)
        total_pages = max(1, (len(processed_cards) + cards_per_page - 1) // cards_per_page)

        # Use session_state values as source of truth for fonts to avoid accidental resets
        effective_font_hanzi = st.session_state.get('font_hanzi', font_hanzi)
        effective_font_pinyin = st.session_state.get('font_pinyin', font_pinyin)
        effective_font_english = st.session_state.get('font_english', font_english)

        # Check if parameters changed (reset to first page if they did)
        current_params = {
            'card_size': card_size,
            'gap': gap,
            'margin': margin,
            'font_hanzi': effective_font_hanzi,
            'font_pinyin': effective_font_pinyin,
            'font_english': effective_font_english,
            'page_size': page_size,
            'hanzi_font': hanzi_font,
            'background_color': background_color,
            'rows': rows,
            'cols': cols,
            'auto_fill': auto_fill,
            'total_cards': len(processed_cards),
            # Include preview mode to ensure state resets and cache invalidation on mode change
            'preview_mode': preview_mode,
        }

        if st.session_state.last_params != current_params:
            st.session_state.current_page = 0
            st.session_state.last_params = current_params
            # Clear export data when parameters change
            st.session_state.export_ready = {}
            st.session_state.export_data = {}

        # Reset current page if it's out of range
        if st.session_state.current_page >= total_pages:
            st.session_state.current_page = 0

        # Page navigation
        render_page_navigation(total_pages)

        # 渲染预览（封装函数，缓存+占位符，降低其它UI重绘）
        render_preview_section(
            processed_cards, preview_mode,
            card_size, gap, margin,
            effective_font_hanzi, effective_font_pinyin, effective_font_english,
            page_size, hanzi_font, background_color,
            rows, cols, auto_fill
        )

        # Show card count and page info
        render_page_info(processed_cards, cards_per_page, total_pages)

        # Card editing section
        if len(processed_cards) > 0:
            with st.expander("✏️ 编辑卡片", expanded=False):
                render_improved_card_editor(processed_cards)

    else:
        # Show empty state
        from services.cache import create_preview_html
        st.components.v1.html(create_preview_html([]), height=650)

    # Close sticky wrapper for the entire preview column
    st.markdown('</div>', unsafe_allow_html=True)


@with_error_boundary("export_section")
def render_export_section(processed_cards: List[Dict[str, str]]) -> None:
    """Render the export section with download buttons."""
    if not processed_cards:
        return

    st.header("📥 导出")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    # Get current processed cards
    current_processed_cards = processed_cards

    # Export parameters from session state
    export_params = {
        'card_size': st.session_state.get('card_size', 5.5),
        'gap': st.session_state.get('gap_cm', 0.5),
        'margin': st.session_state.get('margin_cm', 1.0),
        'font_hanzi': st.session_state.get('font_hanzi', 48),
        'font_pinyin': st.session_state.get('font_pinyin', 18),
        'font_english': st.session_state.get('font_english', 14),
        'page_size': st.session_state.get('page_size', 'A4'),
        'hanzi_font': st.session_state.hanzi_font,
        'background_color': st.session_state.background_color,
        'rows': st.session_state.rows,
        'cols': st.session_state.cols,
        'auto_fill': st.session_state.auto_fill
    }

    # Create export key for caching
    export_key = f"{len(current_processed_cards)}_{hash(str(export_params))}"

    with col_btn1:
        if st.button("📄 导出 PowerPoint", use_container_width=True):
            if export_key not in st.session_state.export_ready or st.session_state.export_ready[export_key] != 'pptx':
                with st.spinner("正在生成 PowerPoint 文件..."):
                    try:
                        from services.export import export_cards
                        file_content = export_cards(current_processed_cards, 'pptx', **export_params)
                        st.session_state.export_data[export_key] = file_content
                        st.session_state.export_ready[export_key] = 'pptx'

                        # Add to export history
                        st.session_state.export_history.append({
                            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'format': 'pptx',
                            'cards': len(current_processed_cards)
                        })
                        st.session_state.total_cards_generated += len(current_processed_cards)

                    except Exception as e:
                        st.error(f"导出失败: {e}")
                        return

            if export_key in st.session_state.export_data:
                st.download_button(
                    label="⬇️ 下载 PPTX",
                    data=st.session_state.export_data[export_key],
                    file_name=f"cards_{len(current_processed_cards)}_{time.strftime('%Y%m%d_%H%M%S')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )

    with col_btn2:
        if st.button("📑 导出 PDF", use_container_width=True):
            if export_key not in st.session_state.export_ready or st.session_state.export_ready[export_key] != 'pdf':
                with st.spinner("正在生成 PDF 文件..."):
                    try:
                        from services.export import export_cards
                        file_content = export_cards(current_processed_cards, 'pdf', **export_params)
                        st.session_state.export_data[export_key] = file_content
                        st.session_state.export_ready[export_key] = 'pdf'

                        # Add to export history
                        st.session_state.export_history.append({
                            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'format': 'pdf',
                            'cards': len(current_processed_cards)
                        })
                        st.session_state.total_cards_generated += len(current_processed_cards)

                    except Exception as e:
                        st.error(f"导出失败: {e}")
                        return

            if export_key in st.session_state.export_data:
                st.download_button(
                    label="⬇️ 下载 PDF",
                    data=st.session_state.export_data[export_key],
                    file_name=f"cards_{len(current_processed_cards)}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    with col_btn3:
        st.info(f"💡 将导出 {len(current_processed_cards)} 张卡片")
        if len(current_processed_cards) > 50:
            st.warning("⚠️ 卡片数量较多，导出可能需要一些时间")


# High-level rendering functions for better organization
def render_left_column():
    """Render the left column with input and options, return all parameters."""
    cards = render_input_section()
    auto_pinyin, auto_translate, page_size, card_size = render_options_section()
    gap, margin, font_hanzi, font_pinyin, font_english, _, _ = render_advanced_options()

    return {
        'cards': cards,
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'translate_order': getattr(st.session_state, 'translate_order', 'local_first'),
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english
    }


def render_preview_column_header():
    """Render the preview column header with mode selection."""
    # Get UI preferences
    prefs = get_ui_preferences()
    hanzi_font, background_color = prefs['hanzi_font'], prefs['background_color']

    # Preview mode selection
    preview_mode = st.radio(
        "预览模式",
        ["📄 完整页面", "🔲 简单网格"],
        horizontal=True,
        help="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
    )
    # Persist preview mode for parameter tracking across components
    st.session_state.preview_mode = preview_mode

    return {
        'hanzi_font': hanzi_font,
        'background_color': background_color,
        'preview_mode': preview_mode
    }


def _validate_preview_inputs(processed_cards: List[Dict[str, str]],
                           config: AppConfig) -> Tuple[List[Dict[str, str]], AppConfig]:
    """Validate and sanitize input parameters for preview rendering."""
    if not isinstance(processed_cards, list):
        processed_cards = []
    if not isinstance(config, AppConfig):
        config = AppConfig.default()

    return processed_cards, config


def _calculate_pagination(processed_cards: List[Dict[str, str]]) -> Tuple[int, int]:
    """Calculate pagination information for cards."""
    layout = get_layout_settings()
    cards_per_page = max(1, layout['rows'] * layout['cols'])
    total_pages = max(1, (len(processed_cards) + cards_per_page - 1) // cards_per_page)
    return cards_per_page, total_pages


def _manage_page_state(total_pages: int) -> None:
    """Manage current page state and reset if out of range."""
    current_page = get_current_page()
    if current_page >= total_pages:
        set_current_page(0)


def _render_preview_ui(processed_cards: List[Dict[str, str]],
                      config: AppConfig,
                      cards_per_page: int,
                      total_pages: int) -> None:
    """Render the preview UI components."""
    render_page_navigation(total_pages)
    render_preview_section(
        processed_cards, config.ui.preview_mode,
        config.layout.card_size, config.layout.gap, config.layout.margin,
        config.layout.font_hanzi, config.layout.font_pinyin, config.layout.font_english,
        config.layout.page_size, config.ui.hanzi_font, config.ui.background_color,
        config.layout.rows, config.layout.cols, config.layout.auto_fill
    )
    render_page_info(processed_cards, cards_per_page, total_pages)


def _render_empty_preview() -> None:
    """Render preview for empty cards case."""
    try:
        st.components.v1.html(create_preview_html([]), height=650)
    except Exception as e:
        st.error(f"预览渲染错误: {e}")


@with_error_boundary("preview_content")
def render_preview_content(processed_cards: List[Dict[str, str]],
                          config: AppConfig) -> Tuple[int, int]:
    """
    Render the preview content area with navigation and editing.

    Args:
        processed_cards: List of card dictionaries with hanzi, pinyin, english
        config: Application configuration object containing UI and layout settings

    Returns:
        Tuple[int, int]: (cards_per_page, total_pages)
    """
    # Validate inputs
    processed_cards, config = _validate_preview_inputs(processed_cards, config)

    if processed_cards:
        # Calculate pagination
        cards_per_page, total_pages = _calculate_pagination(processed_cards)

        # Manage page state
        _manage_page_state(total_pages)

        # Render UI components
        _render_preview_ui(processed_cards, config, cards_per_page, total_pages)

        return cards_per_page, total_pages
    else:
        # Handle empty cards case
        _render_empty_preview()
        return 0, 1  # 0 cards per page, but at least 1 page for empty state


# Legacy function for backward compatibility
def render_preview_content_legacy(processed_cards: List[Dict[str, str]],
                                 preview_params: Dict[str, str],
                                 layout_params: Dict[str, Any]) -> Tuple[int, int]:
    """Legacy function that converts dict parameters to config objects."""
    from core.config import create_config_from_params

    # Extract layout settings from current state
    layout_settings = get_layout_settings()

    config = create_config_from_params(
        card_size=layout_params.get('card_size', 5.5),
        gap=layout_params.get('gap', 0.5),
        margin=layout_params.get('margin', 1.0),
        page_size=layout_params.get('page_size', 'A4'),
        font_hanzi=layout_params.get('font_hanzi', 48),
        font_pinyin=layout_params.get('font_pinyin', 18),
        font_english=layout_params.get('font_english', 14),
        hanzi_font=preview_params.get('hanzi_font', 'SimHei'),
        background_color=preview_params.get('background_color', '#ffffff'),
        preview_mode=preview_params.get('preview_mode', '📄 完整页面'),
        rows=layout_settings.get('rows', 2),
        cols=layout_settings.get('cols', 3),
        auto_fill=layout_settings.get('auto_fill', True)
    )

    return render_preview_content(processed_cards, config)
