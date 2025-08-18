#!/usr/bin/env python3
"""
Chinese Character Learning Cards - Web UI
Simple web interface for generating learning cards with real-time preview.
"""

import streamlit as st
import pandas as pd
import tempfile
import os
import sys
import time
import jieba
import re
from io import StringIO
from typing import List, Dict

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="中文学习卡片生成器",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)
# Global CSS for sticky preview in right column
st.markdown(
    """
    <style>
    .preview-sticky { position: sticky; top: 0; z-index: 100; background: #ffffff; max-height: 100vh; overflow-y: auto; align-self: start; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pinyin_utils import hanzi_to_pinyin, contains_chinese
from dict_utils import create_default_dict
from layout_pptx import PPTXCardGenerator
from layout_pdf import PDFCardGenerator

# Initialize session state
if 'dictionary' not in st.session_state:
    st.session_state.dictionary = create_default_dict("data")
if 'export_history' not in st.session_state:
    st.session_state.export_history = []
if 'total_cards_generated' not in st.session_state:
    st.session_state.total_cards_generated = 0
if 'segmented_text' not in st.session_state:
    st.session_state.segmented_text = ""
if 'use_segmented' not in st.session_state:
    st.session_state.use_segmented = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'last_params' not in st.session_state:
    st.session_state.last_params = {}
if 'processed_cards' not in st.session_state:
    st.session_state.processed_cards = []
if 'cards_source' not in st.session_state:
    st.session_state.cards_source = ""
if 'export_ready' not in st.session_state:
    st.session_state.export_ready = {}
if 'export_data' not in st.session_state:
    st.session_state.export_data = {}
if 'hanzi_font' not in st.session_state:
    st.session_state.hanzi_font = "Microsoft YaHei"
if 'background_color' not in st.session_state:
    st.session_state.background_color = "#FFFFFF"
# Ensure background_color is a valid hex string
try:
    _bg = st.session_state.background_color
    if not isinstance(_bg, str) or not re.fullmatch(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})", _bg.strip()):
        st.session_state.background_color = "#FFFFFF"
except Exception:
    st.session_state.background_color = "#FFFFFF"

# Remove URL parameter handling since we're using the component now

# New layout states
if 'rows' not in st.session_state:
    st.session_state.rows = 3
if 'cols' not in st.session_state:
    st.session_state.cols = 2
if 'auto_fill' not in st.session_state:
    st.session_state.auto_fill = True




def parse_input_text(text: str) -> List[Dict[str, str]]:
    """Parse space-separated Chinese characters into card data."""
    if not text.strip():
        return []

    cards = []
    words = [word.strip() for word in text.split() if word.strip()]

    for word in words:
        if contains_chinese(word):
            cards.append({
                'hanzi': word,
                'pinyin': '',
                'english': ''
            })

    return cards

def auto_segment_text(text: str) -> str:
    """Automatically segment Chinese text into words/characters."""
    if not text.strip():
        return ""

    # Remove existing spaces and punctuation
    text = re.sub(r'[^\u4e00-\u9fff]', '', text)

    if not text:
        return ""

    # Use jieba for initial segmentation
    segments = list(jieba.cut(text, cut_all=False))

    # Post-process: split long words and handle single characters
    final_segments = []
    for segment in segments:
        if len(segment) == 1:
            # Single character - keep as is
            final_segments.append(segment)
        elif len(segment) == 2:
            # Two characters - usually a word, keep as is
            final_segments.append(segment)
        elif len(segment) >= 3:
            # Long segment - check if it should be split
            # For learning cards, prefer shorter segments
            if len(segment) <= 4:
                # Keep 3-4 character words
                final_segments.append(segment)
            else:
                # Split longer segments into smaller parts
                # Try to split into 2-character words first
                for i in range(0, len(segment), 2):
                    if i + 1 < len(segment):
                        final_segments.append(segment[i:i+2])
                    else:
                        final_segments.append(segment[i])

    # Remove duplicates while preserving order
    seen = set()
    unique_segments = []
    for segment in final_segments:
        if segment not in seen:
            seen.add(segment)
            unique_segments.append(segment)

    return " ".join(unique_segments)

def generate_missing_data(cards: List[Dict[str, str]], auto_pinyin: bool, auto_translate: bool) -> List[Dict[str, str]]:
    """Generate missing pinyin and translations."""
    processed_cards = []

    for card in cards:
        processed_card = card.copy()

        # Generate pinyin if missing and enabled
        if auto_pinyin and not processed_card['pinyin']:
            pinyin = hanzi_to_pinyin(processed_card['hanzi'])
            processed_card['pinyin'] = pinyin

        # Generate translation if missing and enabled
        if auto_translate and not processed_card['english']:
            translation = st.session_state.dictionary.lookup_translation(processed_card['hanzi'])
            if translation:
                processed_card['english'] = translation

        processed_cards.append(processed_card)

    return processed_cards
@st.cache_data(show_spinner=False)
def cached_create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = "Microsoft YaHei",
                           background_color: str = "#FFFFFF",
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    return create_page_preview_html(cards, page_num, card_size, gap, margin,
                                   font_hanzi, font_pinyin, font_english,
                                   page_size, hanzi_font, background_color,
                                   rows, cols, auto_fill)


def create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = "Microsoft YaHei",
                           background_color: str = "#FFFFFF",
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    """Create HTML preview of a specific page with realistic layout.

    Supports adjustable rows/columns and an auto-fill mode that adjusts card size
    to fit within page margins.
    """
    # Safety guards
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    cards_per_page = rows * cols
    start_idx = page_num * cards_per_page
    end_idx = min(start_idx + cards_per_page, len(cards))
    page_cards = cards[start_idx:end_idx]

    if not page_cards and page_num > 0:
        return "<div style='text-align: center; color: #666; padding: 50px;'>页面不存在</div>"

    # Calculate dimensions based on page size
    if page_size == "A4":
        page_width_mm, page_height_mm = 210, 297
    else:  # Letter
        page_width_mm, page_height_mm = 216, 279

    # Convert to pixels (assuming 96 DPI for web display)
    mm_to_px = 3.78  # 96 DPI conversion factor
    page_width_px = page_width_mm * mm_to_px
    page_height_px = page_height_mm * mm_to_px

    # Convert cm to pixels
    gap_px = gap * 10 * mm_to_px
    margin_px = margin * 10 * mm_to_px

    # Available area inside margins
    avail_w = max(0, page_width_px - 2 * margin_px)
    avail_h = max(0, page_height_px - 2 * margin_px)

    # Determine card size in px
    if auto_fill:
        # Compute the maximum square size that fits rows x cols with given gaps
        if cols > 0:
            size_w = (avail_w - (cols - 1) * gap_px) / cols
        else:
            size_w = 0
        if rows > 0:
            size_h = (avail_h - (rows - 1) * gap_px) / rows
        else:
            size_h = 0
        card_size_px = max(0, min(size_w, size_h))
    else:
        card_size_px = card_size * 10 * mm_to_px  # cm to mm to px

    # Calculate grid dimensions
    grid_width = cols * card_size_px + max(0, cols - 1) * gap_px
    grid_height = rows * card_size_px + max(0, rows - 1) * gap_px

    # Calculate starting position (centered within margins)
    start_x = margin_px + max(0, (avail_w - grid_width) / 2)
    start_y = margin_px + max(0, (avail_h - grid_height) / 2)

    # Scale factor for web display (make it fit in reasonable space)
    scale_factor = min(600 / page_width_px, 800 / page_height_px, 1.0)

    html = f"""
    <style>
    .page-container {{
        width: {page_width_px * scale_factor}px;
        height: {page_height_px * scale_factor}px;
        background: white;
        border: 1px solid #ccc;
        margin: 0 auto;
        position: relative;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform-origin: top center;
        overflow: hidden;
    }}
    .page-grid {{
        position: absolute;
        left: {start_x * scale_factor}px;
        top: {start_y * scale_factor}px;
        width: {grid_width * scale_factor}px;
        height: {grid_height * scale_factor}px;
        display: grid;
        grid-template-columns: repeat({cols}, {card_size_px * scale_factor}px);
        grid-template-rows: repeat({rows}, {card_size_px * scale_factor}px);
        gap: {gap_px * scale_factor}px;
    }}
    .page-card {{
        border: 2px solid #333;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: {background_color};
        font-family: '{hanzi_font}', 'Microsoft YaHei', 'SimSun', sans-serif;
        padding: {max(5, card_size_px * 0.1) * scale_factor}px;
        box-sizing: border-box;
    }}
    .page-card.empty {{
        border-style: dashed;
        opacity: 0.3;
    }}
    .page-hanzi {{
        font-size: {font_hanzi * scale_factor * 0.8}px;
        font-weight: bold;
        margin-bottom: {max(2, font_hanzi * 0.1) * scale_factor}px;
        color: #000;
        text-align: center;
        line-height: 1.1;
    }}
    .page-pinyin {{
        font-size: {font_pinyin * scale_factor * 0.8}px;
        font-style: italic;
        margin-bottom: {max(2, font_pinyin * 0.1) * scale_factor}px;
        color: #333;
        text-align: center;
        line-height: 1.2;
    }}
    .page-english {{
        font-size: {font_english * scale_factor * 0.8}px;
        text-align: center;
        color: #555;
        line-height: 1.2;
        word-wrap: break-word;
        overflow-wrap: break-word;
    }}
    .page-info {{
        position: absolute;
        bottom: 10px;
        right: 15px;
        font-size: 12px;
        color: #999;
        font-family: Arial, sans-serif;
    }}
    </style>
    <div class="page-container">
        <div class="page-grid">
    """

    # Add cards to grid
    for i in range(cards_per_page):
        if i < len(page_cards):
            card = page_cards[i]
            html += f"""
            <div class="page-card">
                <div class="page-hanzi">{card['hanzi']}</div>
                <div class="page-pinyin">{card['pinyin']}</div>
                <div class="page-english">{card['english']}</div>
            </div>
            """
        else:
            # Empty card slot
            html += '<div class="page-card empty"></div>'

    html += f"""
        </div>
        <div class="page-info">第 {page_num + 1} 页</div>
    </div>
    """

    return html

def create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = "Microsoft YaHei",
                           background_color: str = "#FFFFFF",
                           rows: int = 3, cols: int = 3) -> str:
    """Create simple HTML preview of cards in rows x cols grid with custom styling."""
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    simple_html = f"""
    <style>
    .simple-grid {{
        display: grid;
        grid-template-columns: repeat({cols}, 1fr);
        gap: 15px;
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }}
    .simple-card {{
        border: 2px solid #333;
        aspect-ratio: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 15px;
        background: {background_color};
        font-family: '{hanzi_font}', 'Microsoft YaHei', 'SimSun', sans-serif;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .simple-card.empty {{
        border-style: dashed;
        opacity: 0.3;
    }}
    .simple-hanzi {{
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 8px;
        color: #000;
    }}
    .simple-pinyin {{
        font-size: 1.2em;
        font-style: italic;
        margin-bottom: 8px;
        color: #333;
    }}
    .simple-english {{
        font-size: 1em;
        text-align: center;
        color: #555;
        line-height: 1.3;
    }}
    </style>
    <div class="simple-grid">
    """

    cards_per_page = rows * cols
    for i in range(cards_per_page):
        if i < len(cards):
            card = cards[i]
            simple_html += f"""
            <div class="simple-card">
                <div class="simple-hanzi">{card['hanzi']}</div>
                <div class="simple-pinyin">{card['pinyin']}</div>
                <div class="simple-english">{card['english']}</div>
            </div>
            """
        else:
            simple_html += '<div class="simple-card empty"></div>'

    simple_html += "</div>"
    return simple_html
@st.cache_data(show_spinner=False)
def cached_create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = "Microsoft YaHei",
                           background_color: str = "#FFFFFF", rows: int = 3, cols: int = 3) -> str:
    return create_simple_grid_html(cards, hanzi_font, background_color, rows, cols)

def debug_component_import():
    """No-op in production: previously used for debugging component import."""
    return

def render_color_palette(preset_colors: List[str]) -> None:
    """Render color palette using working component."""
    current = st.session_state.background_color or "#FFFFFF"

    try:
        from components.color_palette import color_palette
        selected = color_palette(
            preset_colors=preset_colors,
            value=current,
            key="main_color_palette",
        )

        if isinstance(selected, str) and selected and selected != current:
            st.session_state.background_color = selected
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
            st.rerun()


def render_preview_section(processed_cards: List[Dict[str, str]], preview_mode: str,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str, hanzi_font: str, background_color: str,
                           rows: int, cols: int, auto_fill: bool) -> None:
    """Render the preview area with caching and a stable placeholder."""
    cards_per_page = max(1, rows * cols)
    preview_placeholder = st.empty()
    if preview_mode == "📄 完整页面":
        html = cached_create_page_preview_html(
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
        html = cached_create_simple_grid_html(current_page_cards, hanzi_font, background_color, rows, cols)
        with preview_placeholder.container():
            st.components.v1.html(html, height=650)


def create_preview_html(cards: List[Dict[str, str]], max_cards: int = 9) -> str:
    """Create simple HTML preview of cards in 3x3 grid (legacy function)."""
    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    # Use the new page preview function for first page with defaults
    return create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, 48, 18, 14, "A4", "Microsoft YaHei", "#FFFFFF", 3, 3, True)

def export_cards(cards: List[Dict[str, str]], format_type: str, **options) -> bytes:
    """Export cards to specified format and return file content."""
    with tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False) as tmp_file:
        try:
            if format_type == 'pptx':
                generator = PPTXCardGenerator(
                    page_size=options.get('page_size', 'A4'),
                    card_size_cm=options.get('card_size', 5.5),
                    gap_cm=options.get('gap', 0.5),
                    margin_cm=options.get('margin', 1.0),
                    rows=options.get('rows', 3),
                    cols=options.get('cols', 3),
                    auto_fill=options.get('auto_fill', True)
                )
                success = generator.generate_pptx(
                    cards, tmp_file.name,
                    font_hanzi=options.get('font_hanzi', 48),
                    font_pinyin=options.get('font_pinyin', 18),
                    font_english=options.get('font_english', 14),
                    hanzi_font=options.get('hanzi_font', 'Microsoft YaHei'),
                    background_color=options.get('background_color', '#FFFFFF')
                )
            elif format_type == 'pdf':
                generator = PDFCardGenerator(
                    page_size=options.get('page_size', 'A4'),
                    card_size_cm=options.get('card_size', 5.5),
                    gap_cm=options.get('gap', 0.5),
                    margin_cm=options.get('margin', 1.0),
                    rows=options.get('rows', 3),
                    cols=options.get('cols', 3),
                    auto_fill=options.get('auto_fill', True)
                )
                success = generator.generate_pdf(
                    cards, tmp_file.name,
                    font_hanzi=options.get('font_hanzi', 48),
                    font_pinyin=options.get('font_pinyin', 18),
                    font_english=options.get('font_english', 14)
                )
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            if success:
                with open(tmp_file.name, 'rb') as f:
                    return f.read()
            else:
                raise Exception(f"Failed to generate {format_type.upper()}")

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file.name)
            except:
                pass

# Sidebar
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

    st.markdown("---")
    st.markdown("### 🔗 快速链接")
    st.markdown("- [项目文档](https://github.com)")
    st.markdown("- [问题反馈](https://github.com)")
    st.markdown("- [使用教程](https://github.com)")

# Main UI
st.title("🀄 Chinese Learning Cards Generator")
st.markdown("输入汉字，自动生成拼音和翻译，制作学习卡片")
st.markdown("💡 **新功能**: 支持空格分隔输入和智能自动分词")

# Create two columns
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 输入")

    # Input method selection
    input_method = st.radio(
        "选择输入方式",
        ["手动输入", "上传CSV文件"],
        horizontal=True
    )

    if input_method == "手动输入":
        # Template selection
        templates = {
            "自定义": "",
            "基础汉字": "爱 家 朋友 水 火 山 月 日 木",
            "数字": "一 二 三 四 五 六 七 八 九 十",
            "颜色": "红 黄 蓝 绿 黑 白 灰 粉 紫 橙",
            "家庭": "爸爸 妈妈 哥哥 姐姐 弟弟 妹妹 爷爷 奶奶 外公",
            "身体部位": "头 眼 耳 鼻 嘴 手 脚 心 身体",
            "动物": "猫 狗 鸟 鱼 马 牛 羊 猪 鸡",
            "食物": "米 面 肉 鱼 蛋 奶 茶 水 糖"
        }

        selected_template = st.selectbox("选择模板", list(templates.keys()))

        # Input text area
        default_text = templates[selected_template]

        # Check if we should use segmented text
        if st.session_state.use_segmented and st.session_state.segmented_text:
            current_text = st.session_state.segmented_text
            st.session_state.use_segmented = False  # Reset flag
        else:
            current_text = default_text

        # Create columns for text area and button
        col_text, col_btn = st.columns([4, 1])

        with col_text:
            input_text = st.text_area(
                "输入汉字（用空格分隔）",
                value=current_text,
                placeholder="例如：爱 家 朋友 水 火 山 月 日 木",
                height=120,
                help="输入中文字符，用空格分隔。每个词将生成一张卡片。"
            )

        with col_btn:
            st.write("")  # Add some spacing
            st.write("")  # Add some spacing
            if st.button("🔤 自动分隔", help="自动将当前文本框中的连续汉字分隔成词语", use_container_width=True):
                if input_text.strip():
                    segmented_text = auto_segment_text(input_text)
                    st.session_state.segmented_text = segmented_text
                    st.session_state.use_segmented = True
                    st.rerun()

        # Additional input for unsegmented text
        st.caption("或者输入连续汉字，点击自动分隔：")
        unsegmented_input = st.text_input(
            "连续汉字输入",
            placeholder="例如：我爱我的家人朋友们",
            help="输入连续的汉字，系统将自动分词"
        )

        if unsegmented_input.strip():
            segmented_preview = auto_segment_text(unsegmented_input)
            if st.button("✅ 应用分词", use_container_width=True):
                st.session_state.segmented_text = segmented_preview
                st.session_state.use_segmented = True
                st.rerun()

        cards = parse_input_text(input_text)

    else:
        # File upload
        uploaded_file = st.file_uploader(
            "上传CSV文件",
            type=['csv'],
            help="CSV文件应包含hanzi列，可选pinyin和english列。支持中英文列名。"
        )

        if uploaded_file is not None:
            try:
                # Read CSV file
                df = pd.read_csv(uploaded_file)

                # Show preview of uploaded data
                st.write("📄 文件预览:")
                st.dataframe(df.head(), use_container_width=True)

                # Convert to cards format
                cards = []
                for _, row in df.iterrows():
                    hanzi = str(row.get('hanzi', row.get('chinese', row.get('word', ''))))
                    if hanzi and hanzi != 'nan' and contains_chinese(hanzi):
                        cards.append({
                            'hanzi': hanzi,
                            'pinyin': str(row.get('pinyin', row.get('pronunciation', ''))),
                            'english': str(row.get('english', row.get('translation', row.get('meaning', ''))))
                        })

                st.success(f"成功导入 {len(cards)} 张卡片")

            except Exception as e:
                st.error(f"文件读取失败: {e}")
                cards = []
        else:
            st.info("请上传CSV文件")
            cards = []

    # Options
    st.subheader("⚙️ 选项")
    col_opt1, col_opt2 = st.columns(2)

    with col_opt1:
        auto_pinyin = st.checkbox("自动生成拼音", value=True)
        auto_translate = st.checkbox("自动生成翻译", value=True)

    with col_opt2:
        page_size = st.selectbox("页面尺寸", ["A4", "Letter"], index=0)
        card_size = st.slider("卡片大小 (cm)", 4.0, 8.0, 5.5, 0.1, key="card_size")

    # Advanced options in expander
    with st.expander("🔧 高级选项"):
        # Layout options
        col_layout1, col_layout2 = st.columns(2)
        with col_layout1:
            gap = st.slider("卡片间距 (cm)", 0.2, 1.0, 0.5, 0.1, key="gap_cm")
            margin = st.slider("页面边距 (cm)", 0.5, 2.0, 1.0, 0.1, key="margin_cm")
            cols = st.number_input("每行卡片数 (列)", min_value=1, max_value=8, value=st.session_state.cols, step=1)
            rows = st.number_input("每列卡片数 (行)", min_value=1, max_value=10, value=st.session_state.rows, step=1)
            auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.auto_fill)

        with col_layout2:
            # Font selection for Chinese characters
            hanzi_font_options = [
                "Microsoft YaHei",
                "SimSun",
                "SimHei",
                "KaiTi",
                "FangSong",
                "STSong",
                "STKaiti",
                "STHeiti",
                "PingFang SC",
                "Hiragino Sans GB"
            ]
            hanzi_font = st.selectbox(
                "汉字字体",
                hanzi_font_options,
                index=hanzi_font_options.index(st.session_state.hanzi_font),
                help="选择汉字显示字体，不同字体有不同的视觉效果"
            )

            # Background color selection with visual color palette
            st.write("**卡片背景颜色:**")

            # Define preset colors similar to the image you showed
            preset_colors = [
                # Row 1: Dark colors
                "#000000", "#333333", "#FF4444", "#FF8800", "#FFDD00",
                "#44FF44", "#00DDDD", "#4488FF", "#8844FF", "#FF44FF",
                # Row 2: Light colors
                "#FFFFFF", "#CCCCCC", "#FFB3B3", "#FFCC99", "#FFEE99",
                "#B3FFB3", "#99FFFF", "#B3CCFF", "#CCB3FF", "#FFB3FF"
            ]

            st.caption("快速选择颜色：点击下方色块选择背景色")
            render_color_palette(preset_colors)

            # Show current & custom color in one row without additional columns nesting
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:12px;'>"
                f"<div style='width:50px;height:30px;background-color:{st.session_state.background_color};"
                f"border:2px solid #333;border-radius:4px;'></div>"
                f"<span style='font-family:monospace'>{st.session_state.background_color}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            custom_color = st.color_picker(
                "自定义颜色",
                value=st.session_state.background_color,
                key="custom_color_picker",
                help="选择自定义颜色（关闭选择器后生效）",
            )
            background_color = custom_color if custom_color != st.session_state.background_color else st.session_state.background_color



        # Update session state
        if hanzi_font != st.session_state.hanzi_font:
            st.session_state.hanzi_font = hanzi_font
        if background_color != st.session_state.background_color:
            st.session_state.background_color = background_color
        if rows != st.session_state.rows:
            st.session_state.rows = int(rows)
        if cols != st.session_state.cols:
            st.session_state.cols = int(cols)
        if auto_fill != st.session_state.auto_fill:
            st.session_state.auto_fill = bool(auto_fill)

        st.write("字体大小:")

        col_font1, col_font2, col_font3 = st.columns(3)
        with col_font1:
            font_hanzi = st.slider("汉字", 24, 72, 48, 2, key="font_hanzi")
        with col_font2:
            font_pinyin = st.slider("拼音", 12, 36, 18, 2, key="font_pinyin")
        with col_font3:
            font_english = st.slider("英文", 8, 24, 14, 2, key="font_english")



        # Sticky wrapper for preview is added only within preview column below


with col2:
    st.markdown('<div class="preview-sticky">', unsafe_allow_html=True)

    st.header("👀 预览")


    # Preview mode selection
    preview_mode = st.radio(
        "预览模式",
        ["📄 完整页面", "🔲 简单网格"],
        horizontal=True,
        help="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
    )

    # Determine current cards source for comparison
    if input_method == "手动输入":
        current_source = f"manual:{input_text}"
    else:
        current_source = f"csv:{uploaded_file.name if uploaded_file else 'none'}"

    # Check if we need to reprocess cards
    need_reprocess = (
        st.session_state.cards_source != current_source or
        len(st.session_state.processed_cards) != len(cards) or
        not st.session_state.processed_cards
    )

    # Clear export data if cards changed
    if need_reprocess:
        st.session_state.export_ready = {}
        st.session_state.export_data = {}

    if cards:
        # Generate missing data only if needed
        if need_reprocess:
            st.session_state.processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate)
            st.session_state.cards_source = current_source

        processed_cards = st.session_state.processed_cards

        # Calculate total pages (rows x cols per page)
        cards_per_page = max(1, st.session_state.rows * st.session_state.cols)
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
            'rows': st.session_state.rows,
            'cols': st.session_state.cols,
            'auto_fill': st.session_state.auto_fill,
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
        if total_pages > 1:
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

        # 渲染预览（封装函数，缓存+占位符，降低其它UI重绘）
        render_preview_section(
            processed_cards, preview_mode,
            card_size, gap, margin,
            font_hanzi, font_pinyin, font_english,
            page_size, hanzi_font, background_color,
            st.session_state.rows, st.session_state.cols, st.session_state.auto_fill
        )

        # Show card count and page info
        cards_on_current_page = min(cards_per_page, len(processed_cards) - st.session_state.current_page * cards_per_page)
        st.info(f"📊 总计 {len(processed_cards)} 张卡片，共 {total_pages} 页 | 当前第 {st.session_state.current_page + 1} 页，显示 {cards_on_current_page} 张卡片")

        # 调试信息块已移除，保持界面简洁


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
        if st.session_state.processed_cards:
            st.session_state.processed_cards = []
            st.session_state.cards_source = ""
        st.components.v1.html(create_preview_html([]), height=650)
    # Close sticky wrapper for the entire preview column
    st.markdown('</div>', unsafe_allow_html=True)


# Export buttons - use processed_cards from session state
if st.session_state.processed_cards:
    st.header("📥 导出")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    # Get current processed cards
    current_processed_cards = st.session_state.processed_cards

    # Prepare export options
    export_options = {
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'hanzi_font': hanzi_font,
        'background_color': background_color,
        'rows': st.session_state.rows,
        'cols': st.session_state.cols,
        'auto_fill': st.session_state.auto_fill
    }

    with col_btn1:
        # Check if PPTX is ready for download
        if 'pptx' in st.session_state.export_ready and st.session_state.export_ready['pptx']:
            # Show download button
            st.download_button(
                label="⬇️ 下载 PPTX",
                data=st.session_state.export_data['pptx']['content'],
                file_name=st.session_state.export_data['pptx']['filename'],
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                use_container_width=True,
                key="download_pptx"
            )
            # Add a button to generate new PPTX
            if st.button("🔄 重新生成 PPTX", use_container_width=True, key="regenerate_pptx"):
                st.session_state.export_ready['pptx'] = False
                st.rerun()
        else:
            # Show generate button
            if st.button("📄 导出 PPTX", type="primary", use_container_width=True, key="generate_pptx"):
                try:
                    with st.spinner("正在生成 PPTX..."):
                        file_content = export_cards(current_processed_cards, 'pptx', **export_options)

                    # Store export data in session state
                    st.session_state.export_data['pptx'] = {
                        'content': file_content,
                        'filename': f"chinese_cards_{len(current_processed_cards)}.pptx"
                    }
                    st.session_state.export_ready['pptx'] = True

                    # Record export history
                    import datetime
                    st.session_state.export_history.append({
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'format': 'pptx',
                        'cards': len(current_processed_cards)
                    })
                    st.session_state.total_cards_generated += len(current_processed_cards)

                    st.success("PPTX 生成成功！点击下载按钮下载文件。")
                    st.rerun()

                except Exception as e:
                    st.error(f"生成 PPTX 失败: {e}")

    with col_btn2:
        # Check if PDF is ready for download
        if 'pdf' in st.session_state.export_ready and st.session_state.export_ready['pdf']:
            # Show download button
            st.download_button(
                label="⬇️ 下载 PDF",
                data=st.session_state.export_data['pdf']['content'],
                file_name=st.session_state.export_data['pdf']['filename'],
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf"
            )
            # Add a button to generate new PDF
            if st.button("🔄 重新生成 PDF", use_container_width=True, key="regenerate_pdf"):
                st.session_state.export_ready['pdf'] = False
                st.rerun()
        else:
            # Show generate button
            if st.button("📑 导出 PDF", type="secondary", use_container_width=True, key="generate_pdf"):
                try:
                    with st.spinner("正在生成 PDF..."):
                        file_content = export_cards(current_processed_cards, 'pdf', **export_options)

                    # Store export data in session state
                    st.session_state.export_data['pdf'] = {
                        'content': file_content,
                        'filename': f"chinese_cards_{len(current_processed_cards)}.pdf"
                    }
                    st.session_state.export_ready['pdf'] = True

                    # Record export history
                    import datetime
                    st.session_state.export_history.append({
                        'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'format': 'pdf',
                        'cards': len(current_processed_cards)
                    })
                    st.session_state.total_cards_generated += len(current_processed_cards)

                    st.success("PDF 生成成功！点击下载按钮下载文件。")
                    st.rerun()

                except Exception as e:
                    st.error(f"生成 PDF 失败: {e}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 0.9em;'>
    🀄 Chinese Learning Cards Generator |
    支持自动拼音生成和英文翻译 |
    可导出为 PPTX 或 PDF 格式
    </div>
    """,
    unsafe_allow_html=True
)
