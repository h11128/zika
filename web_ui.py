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
import jieba
import re
from io import StringIO
from typing import List, Dict

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pinyin_utils import hanzi_to_pinyin, contains_chinese
from dict_utils import create_default_dict
from layout_pptx import PPTXCardGenerator
from layout_pdf import PDFCardGenerator

# Page configuration
st.set_page_config(
    page_title="Chinese Learning Cards Generator",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def create_preview_html(cards: List[Dict[str, str]], max_cards: int = 9) -> str:
    """Create HTML preview of cards in 3x3 grid."""
    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    # Limit to first 9 cards for preview
    preview_cards = cards[:max_cards]

    html = """
    <style>
    .card-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
        max-width: 600px;
        margin: 0 auto;
    }
    .card {
        border: 2px solid #333;
        aspect-ratio: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 10px;
        background: white;
        font-family: 'Microsoft YaHei', 'SimSun', sans-serif;
    }
    .hanzi {
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 8px;
        color: #000;
    }
    .pinyin {
        font-size: 1.2em;
        font-style: italic;
        margin-bottom: 8px;
        color: #333;
    }
    .english {
        font-size: 1em;
        text-align: center;
        color: #555;
    }
    </style>
    <div class="card-grid">
    """

    # Add cards
    for i in range(9):  # Always show 9 slots
        if i < len(preview_cards):
            card = preview_cards[i]
            html += f"""
            <div class="card">
                <div class="hanzi">{card['hanzi']}</div>
                <div class="pinyin">{card['pinyin']}</div>
                <div class="english">{card['english']}</div>
            </div>
            """
        else:
            # Empty card slot
            html += '<div class="card" style="border-style: dashed; opacity: 0.3;"></div>'

    html += "</div>"

    if len(cards) > max_cards:
        html += f"<p style='text-align: center; margin-top: 10px; color: #666;'>显示前9张卡片，共{len(cards)}张</p>"

    return html

def export_cards(cards: List[Dict[str, str]], format_type: str, **options) -> bytes:
    """Export cards to specified format and return file content."""
    with tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False) as tmp_file:
        try:
            if format_type == 'pptx':
                generator = PPTXCardGenerator(
                    page_size=options.get('page_size', 'A4'),
                    card_size_cm=options.get('card_size', 5.5),
                    gap_cm=options.get('gap', 0.5),
                    margin_cm=options.get('margin', 1.0)
                )
                success = generator.generate_pptx(
                    cards, tmp_file.name,
                    font_hanzi=options.get('font_hanzi', 48),
                    font_pinyin=options.get('font_pinyin', 18),
                    font_english=options.get('font_english', 14)
                )
            elif format_type == 'pdf':
                generator = PDFCardGenerator(
                    page_size=options.get('page_size', 'A4'),
                    card_size_cm=options.get('card_size', 5.5),
                    gap_cm=options.get('gap', 0.5),
                    margin_cm=options.get('margin', 1.0)
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
        st.write("**或者输入连续汉字，点击自动分隔：**")
        unsegmented_input = st.text_input(
            "连续汉字输入",
            placeholder="例如：我爱我的家人朋友们",
            help="输入连续的汉字，系统将自动分词"
        )

        if unsegmented_input.strip():
            col_preview, col_apply = st.columns([3, 1])
            with col_preview:
                segmented_preview = auto_segment_text(unsegmented_input)
                st.write(f"**分词预览**: {segmented_preview}")
            with col_apply:
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
        card_size = st.slider("卡片大小 (cm)", 4.0, 8.0, 5.5, 0.1)

    # Advanced options in expander
    with st.expander("🔧 高级选项"):
        gap = st.slider("卡片间距 (cm)", 0.2, 1.0, 0.5, 0.1)
        margin = st.slider("页面边距 (cm)", 0.5, 2.0, 1.0, 0.1)

        st.write("字体大小:")
        font_hanzi = st.slider("汉字", 24, 72, 48, 2)
        font_pinyin = st.slider("拼音", 12, 36, 18, 2)
        font_english = st.slider("英文", 8, 24, 14, 2)

with col2:
    st.header("👀 预览")

    if cards:
        # Generate missing data
        processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate)

        # Show preview
        preview_html = create_preview_html(processed_cards)
        st.components.v1.html(preview_html, height=650)

        # Show card count
        st.info(f"共 {len(processed_cards)} 张卡片，将生成 {(len(processed_cards) + 8) // 9} 页")

        # Card editing section
        if len(processed_cards) > 0:
            with st.expander("✏️ 编辑卡片内容", expanded=False):
                st.write("选择要编辑的卡片:")

                # Create tabs for each card (limit to first 9 for UI performance)
                edit_cards = processed_cards[:9]
                if len(edit_cards) > 0:
                    tabs = st.tabs([f"卡片 {i+1}: {card['hanzi']}" for i, card in enumerate(edit_cards)])

                    for i, (tab, card) in enumerate(zip(tabs, edit_cards)):
                        with tab:
                            col_e1, col_e2, col_e3 = st.columns(3)

                            with col_e1:
                                new_hanzi = st.text_input(f"汉字", value=card['hanzi'], key=f"hanzi_{i}")
                            with col_e2:
                                new_pinyin = st.text_input(f"拼音", value=card['pinyin'], key=f"pinyin_{i}")
                            with col_e3:
                                new_english = st.text_input(f"英文", value=card['english'], key=f"english_{i}")

                            # Update the card if values changed
                            if new_hanzi != card['hanzi'] or new_pinyin != card['pinyin'] or new_english != card['english']:
                                processed_cards[i] = {
                                    'hanzi': new_hanzi,
                                    'pinyin': new_pinyin,
                                    'english': new_english
                                }

    else:
        st.components.v1.html(create_preview_html([]), height=650)

# Export buttons
if cards:
    st.header("📥 导出")

    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])

    # Prepare export options
    export_options = {
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english
    }

    with col_btn1:
        if st.button("📄 导出 PPTX", type="primary", use_container_width=True):
            try:
                with st.spinner("正在生成 PPTX..."):
                    processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate)
                    file_content = export_cards(processed_cards, 'pptx', **export_options)

                # Record export history
                import datetime
                st.session_state.export_history.append({
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'format': 'pptx',
                    'cards': len(processed_cards)
                })
                st.session_state.total_cards_generated += len(processed_cards)

                st.download_button(
                    label="⬇️ 下载 PPTX",
                    data=file_content,
                    file_name=f"chinese_cards_{len(processed_cards)}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )
                st.success("PPTX 生成成功！")

            except Exception as e:
                st.error(f"生成 PPTX 失败: {e}")

    with col_btn2:
        if st.button("📑 导出 PDF", type="secondary", use_container_width=True):
            try:
                with st.spinner("正在生成 PDF..."):
                    processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate)
                    file_content = export_cards(processed_cards, 'pdf', **export_options)

                # Record export history
                import datetime
                st.session_state.export_history.append({
                    'time': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    'format': 'pdf',
                    'cards': len(processed_cards)
                })
                st.session_state.total_cards_generated += len(processed_cards)

                st.download_button(
                    label="⬇️ 下载 PDF",
                    data=file_content,
                    file_name=f"chinese_cards_{len(processed_cards)}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("PDF 生成成功！")

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
