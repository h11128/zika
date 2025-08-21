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


def render_input_section() -> List[Dict[str, str]]:
    """Render the input section and return parsed cards."""
    st.header("📝 输入")

    # Input method selection
    input_method = st.radio(
        "选择输入方式",
        ["手动输入", "上传CSV文件"],
        horizontal=True
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
                st.session_state.input_text = auto_segment_text(st.session_state.input_text.strip())
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

        with col_btn:
            st.write("")  # Add some spacing
            st.write("")  # Add some spacing
            if st.button("🔄 智能分词", use_container_width=True, help="对输入文本进行智能分词"):
                st.session_state.apply_segmentation = True
                st.rerun()

        # Parse input text
        text_input = st.session_state.input_text
        if text_input.strip():
            cards = parse_input_text(text_input)

    else:  # CSV upload
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
    st.subheader("⚙️ 选项")
    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        auto_pinyin = st.checkbox("自动生成拼音", value=True)
        auto_translate = st.checkbox("自动生成翻译", value=True)
        translate_order_display = st.selectbox(
            "翻译优先级",
            ["本地优先", "Google优先", "仅本地", "仅Google", "混合模式"],
            index=0,
            key="translate_order_select"
        )
        # Map display text to internal values used by processing layer and store in session
        order_map = {
            "本地优先": "local_first",
            "Google优先": "google_first",
            "仅本地": "local_only",
            "仅Google": "google_only",
            "混合模式": "mixed",
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
        page_size = st.selectbox("页面尺寸", ["A4", "Letter"], index=0)
        card_size = st.slider("卡片大小 (cm)", 4.0, 8.0, 5.5, 0.1, key="card_size")

    return auto_pinyin, auto_translate, page_size, card_size


def render_advanced_options() -> Tuple[float, float, int, int, int, int, str]:
    """Render the advanced options section and return advanced option values."""
    with st.expander("🔧 高级选项"):
        # Layout options
        col_layout1, col_layout2 = st.columns(2)
        with col_layout1:
            gap = st.slider("卡片间距 (cm)", 0.2, 1.0, 0.5, 0.1, key="gap_cm")
            margin = st.slider("页面边距 (cm)", 0.5, 2.0, 1.0, 0.1, key="margin_cm")
            cols = st.number_input("每行卡片数 (列)", min_value=1, max_value=10, value=st.session_state.cols, step=1)
            rows = st.number_input("每列卡片数 (行)", min_value=1, max_value=10, value=st.session_state.rows, step=1)
            auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.auto_fill)

        with col_layout2:
            # Font selection for Chinese characters
            hanzi_font = st.selectbox(
                "汉字字体",
                HANZI_FONT_OPTIONS,
                index=HANZI_FONT_OPTIONS.index(st.session_state.hanzi_font),
                help="选择汉字显示字体，不同字体有不同的视觉效果"
            )

            # Background color selection with visual color palette
            st.write("**卡片背景颜色:**")

            st.caption("快速选择颜色：点击下方色块选择背景色")
            render_color_palette(PRESET_COLORS)

            # Show current & custom color in one row without additional columns nesting
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;'>"
                f"<div style='width:50px;height:30px;background-color:{st.session_state.background_color};"
                f"border:1px solid #ccc;border-radius:4px;'></div>"
                f"<span>当前颜色: {st.session_state.background_color}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )

            # Custom color input
            custom_color = st.color_picker("自定义颜色", value=st.session_state.background_color, key="custom_color_picker")
            if custom_color != st.session_state.background_color:
                st.session_state.background_color = custom_color
                st.rerun()

        # Font size options
        st.write("**字体大小:**")
        col_font1, col_font2, col_font3 = st.columns(3)
        with col_font1:
            font_hanzi = st.slider("汉字", 20, 80, 48, 2, key="font_hanzi")
        with col_font2:
            font_pinyin = st.slider("拼音", 10, 40, 18, 1, key="font_pinyin")
        with col_font3:
            font_english = st.slider("英文", 8, 30, 14, 1, key="font_english")

        # Update session state
        st.session_state.rows = rows
        st.session_state.cols = cols
        st.session_state.auto_fill = auto_fill
        st.session_state.hanzi_font = hanzi_font

    return gap, margin, font_hanzi, font_pinyin, font_english, rows, cols


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

    if processed_cards:
        # Calculate total pages (rows x cols per page)
        cards_per_page = max(1, rows * cols)
        total_pages = max(1, (len(processed_cards) + cards_per_page - 1) // cards_per_page)

        # Check if parameters changed (reset to first page if they did)
        current_params = {
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
            'total_cards': len(processed_cards)
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
            font_hanzi, font_pinyin, font_english,
            page_size, hanzi_font, background_color,
            rows, cols, auto_fill
        )

        # Show card count and page info
        render_page_info(processed_cards, cards_per_page, total_pages)

        # Card editing section
        if len(processed_cards) > 0:
            with st.expander("✏️ 编辑当前页卡片", expanded=False):
                st.write(f"编辑第 {st.session_state.current_page + 1} 页的卡片:")

                # Get cards for current page
                start_idx = st.session_state.current_page * cards_per_page
                end_idx = min(start_idx + cards_per_page, len(processed_cards))
                current_page_cards = processed_cards[start_idx:end_idx]

                if current_page_cards:
                    tabs = st.tabs([f"卡片 {start_idx + i + 1}: {card['hanzi']}" for i, card in enumerate(current_page_cards)])

                    for i, (tab, card) in enumerate(zip(tabs, current_page_cards)):
                        with tab:
                            col_e1, col_e2, col_e3 = st.columns(3)

                            actual_idx = start_idx + i
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
                                # Clear export data when cards are edited
                                st.session_state.export_ready = {}
                                st.session_state.export_data = {}
                                st.rerun()

    else:
        # Show empty state
        from services.cache import create_preview_html
        st.components.v1.html(create_preview_html([]), height=650)

    # Close sticky wrapper for the entire preview column
    st.markdown('</div>', unsafe_allow_html=True)


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
