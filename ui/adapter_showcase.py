"""
UI Adapter Showcase - Demonstration of adapter pattern usage.
Shows how to use UI adapters for framework-agnostic components.
"""

from typing import Tuple, Dict, Any
from ui.ports import (
    UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
)
from core.feature_flags import get_feature_flag
from ui.error_boundaries import with_error_boundary


@with_error_boundary("layout_section_adapted")
def render_layout_section_adapted(adapter: UIAdapter) -> Tuple[float, float, int, int]:
    """
    Render layout section using UI adapter.
    Demonstrates framework-agnostic component usage.
    """
    adapter.subheader("📐 布局设置 (适配器版本)")
    
    # Create column layout
    col1, col2 = adapter.layout.columns([1, 1])
    
    # Gap setting
    with col1:
        gap_config = ComponentConfig(
            key="gap_adapted",
            label="卡片间距 (cm)",
            help_text="卡片之间的间距"
        )
        gap_cm = adapter.inputs.slider(
            gap_config, value=0.5, min_value=0.0, max_value=2.0, step=0.1
        )
        
        # Rows setting
        rows_config = ComponentConfig(
            key="rows_adapted",
            label="行数"
        )
        layout_rows = adapter.inputs.number_input(
            rows_config, value=2, min_value=1, max_value=10, step=1
        )
    
    # Margin setting
    with col2:
        margin_config = ComponentConfig(
            key="margin_adapted",
            label="页面边距 (cm)",
            help_text="页面四周的边距"
        )
        margin_cm = adapter.inputs.slider(
            margin_config, value=1.0, min_value=0.0, max_value=3.0, step=0.1
        )
        
        # Cols setting
        cols_config = ComponentConfig(
            key="cols_adapted",
            label="列数"
        )
        layout_cols = adapter.inputs.number_input(
            cols_config, value=3, min_value=1, max_value=10, step=1
        )
    
    # Show notification if values changed
    if gap != 0.5 or margin != 1.0 or rows != 2 or cols != 3:
        adapter.notifications.show_message(
            f"布局已更新: {rows}x{cols}, 间距={gap}cm, 边距={margin}cm",
            NotificationLevel.INFO
        )
    
    return gap, margin, layout_rows, cols


@with_error_boundary("typography_section_adapted")
def render_typography_section_adapted(adapter: UIAdapter) -> Tuple[int, int, int, str]:
    """
    Render typography section using UI adapter.
    """
    adapter.subheader("🔤 字体设置 (适配器版本)")
    
    col1, col2 = adapter.layout.columns([1, 1])
    
    with col1:
        # Hanzi font size
        hanzi_config = ComponentConfig(
            key="font_hanzi_adapted",
            label="汉字字体大小"
        )
        hanzi_font_size = adapter.inputs.slider(
            hanzi_config, value=48, min_value=20, max_value=100, step=2
        )
        
        # Pinyin font size
        pinyin_config = ComponentConfig(
            key="font_pinyin_adapted",
            label="拼音字体大小"
        )
        pinyin_font_size = adapter.inputs.slider(
            pinyin_config, value=18, min_value=10, max_value=40, step=1
        )
    
    with col2:
        # English font size
        english_config = ComponentConfig(
            key="font_english_adapted",
            label="英文字体大小"
        )
        english_font_size = adapter.inputs.slider(
            english_config, value=14, min_value=8, max_value=30, step=1
        )
        
        # Hanzi font family
        font_options = ['SimHei', 'Microsoft YaHei', 'KaiTi', 'FangSong']
        font_config = ComponentConfig(
            key="hanzi_font_adapted",
            label="汉字字体"
        )
        hanzi_font_family = adapter.inputs.selectbox(
            font_config, options=font_options, index=0
        )
    
    return hanzi_font_size, pinyin_font_size, english_font_size, hanzi_font_family


@with_error_boundary("options_section_adapted")
def render_options_section_adapted(adapter: UIAdapter) -> Tuple[bool, bool, str]:
    """
    Render options section using UI adapter.
    """
    adapter.subheader("⚙️ 选项 (适配器版本)")
    
    col1, col2 = adapter.layout.columns([1, 1])
    
    with col1:
        # Auto pinyin checkbox
        pinyin_config = ComponentConfig(
            key="auto_pinyin_adapted",
            label="自动添加拼音",
            help_text="自动为汉字添加拼音注音"
        )
        auto_pinyin = adapter.inputs.checkbox(pinyin_config, value=True)
        
        # Auto translate checkbox
        translate_config = ComponentConfig(
            key="auto_translate_adapted",
            label="自动翻译",
            help_text="自动翻译中文到英文"
        )
        auto_translate = adapter.inputs.checkbox(translate_config, value=True)
    
    with col2:
        # Page size selection
        page_sizes = ['A4', 'Letter', 'A3', 'A5']
        page_config = ComponentConfig(
            key="page_size_adapted",
            label="页面大小"
        )
        page_size = adapter.inputs.selectbox(page_config, options=page_sizes, index=0)
        
        # Preview mode radio
        preview_modes = ['📄 完整页面', '🔲 简单网格']
        preview_config = ComponentConfig(
            key="preview_mode_adapted",
            label="预览模式"
        )
        preview_mode = adapter.inputs.radio(
            preview_config, options=preview_modes, index=0, horizontal=True
        )
    
    return auto_pinyin, auto_translate, page_size


@with_error_boundary("input_section_adapted")
def render_input_section_adapted(adapter: UIAdapter) -> str:
    """
    Render input section using UI adapter.
    """
    adapter.subheader("📝 输入文本 (适配器版本)")
    
    # Text area for input
    input_config = ComponentConfig(
        key="input_text_adapted",
        label="输入中文文本",
        help_text="输入要制作卡片的中文文本，每行一个词或短语"
    )
    input_text = adapter.inputs.text_area(
        input_config, value="", height_cm=200
    )
    
    # Buttons row
    col1, col2, col3 = adapter.layout.columns([2, 1, 1])
    
    with col2:
        segment_config = ComponentConfig(
            key="segment_btn_adapted",
            label="🔄 重新分词"
        )
        if adapter.inputs.button(segment_config):
            adapter.notifications.show_message(
                "文本分词已触发", NotificationLevel.SUCCESS
            )
    
    with col3:
        clear_config = ComponentConfig(
            key="clear_btn_adapted",
            label="🗑️ 清空"
        )
        if adapter.inputs.button(clear_config):
            adapter.notifications.show_message(
                "文本已清空", NotificationLevel.INFO
            )
            input_text = ""
    
    return input_text


@with_error_boundary("preview_section_adapted")
def render_preview_section_adapted(adapter: UIAdapter, html_content: str) -> None:
    """
    Render preview section using UI adapter.
    """
    adapter.subheader("👀 预览 (适配器版本)")
    
    # Preview mode selection
    preview_modes = ['📄 完整页面', '🔲 简单网格']
    mode_config = ComponentConfig(
        key="preview_mode_selector_adapted",
        label="预览模式"
    )
    preview_mode = adapter.inputs.radio(
        mode_config, options=preview_modes, index=0, horizontal=True
    )
    
    # Preview content
    if html_content:
        height_cm = 850 if preview_mode == '📄 完整页面' else 650
        adapter.preview.html_component(html_content, height_cm=height)
    else:
        adapter.notifications.show_message(
            "没有可预览的内容", NotificationLevel.INFO
        )


def showcase_adapter_usage() -> Dict[str, Any]:
    """
    Showcase the UI adapter pattern usage.
    Returns collected values for testing.
    """
    if not get_feature_flag('ui_adapter_showcase', False):
        return {}
    
    adapter = get_ui_adapter()
    
    # Show adapter info
    adapter_type = type(adapter).__name__
    adapter.markdown(f"**当前适配器**: {adapter_type}")
    
    # Render sections using adapter
    results = {}
    
    # Layout section
    gap, margin, layout_rows, layout_cols = render_layout_section_adapted(adapter)
    results['layout'] = {'gap_cm': gap, 'margin_cm': margin, 'layout_rows': layout_rows, 'layout_cols': cols}
    
    # Typography section
    hanzi_font_size, pinyin_font_size, english_font_size, hanzi_font_family = render_typography_section_adapted(adapter)
    results['typography'] = {
        'hanzi_font_size': hanzi_font_size, 'pinyin_font_size': pinyin_font_size,
        'english_font_size': english_font_size, 'hanzi_font_family': hanzi_font_family
    }
    
    # Options section
    auto_pinyin, auto_translate, page_size = render_options_section_adapted(adapter)
    results['options'] = {
        'auto_pinyin': auto_pinyin, 'auto_translate': auto_translate,
        'page_size': page_size
    }
    
    # Input section
    input_text = render_input_section_adapted(adapter)
    results['input'] = {'text': input_text}
    
    # Preview section (with dummy content)
    dummy_html = "<div>预览内容示例</div>"
    render_preview_section_adapted(adapter, dummy_html)
    
    return results


def use_ui_adapter() -> bool:
    """Check if UI adapter should be used."""
    return True
