"""
Options management module for the UI refactor.
Handles processing options, layout settings, and advanced configuration.
Migrated from ui/sections.py
"""

# Option C alias: route through ports.st while preserving module-level st for tests
import ui.ports as ports
st = ports.st
from typing import Tuple, Dict, Any

from core.constants import HANZI_FONT_OPTIONS, PRESET_COLORS

from ui.components import render_color_palette
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel

# Import error boundaries for UI protection
try:
    from ui.error_boundaries import with_error_boundary
    ERROR_BOUNDARIES_AVAILABLE = True
except ImportError:
    ERROR_BOUNDARIES_AVAILABLE = False
    # Fallback decorator that does nothing
    def with_error_boundary(component_name: str, fallback_ui=None):
        def decorator(func):
            return func
        return decorator


@with_error_boundary("options_section")
def render_options_section() -> Tuple[bool, bool, str, float]:
    """Render the options section and return option values. Migrated from sections.py"""

    # Handle auto_fill disable request from button
    if st.session_state.get('_disable_auto_fill_requested', False):
        st.session_state.layout_auto_fill = False
        st.session_state._disable_auto_fill_requested = False
        from services.cache_v2 import clear_preview_cache
        clear_preview_cache()
        if 'last_preview_params' in st.session_state:
            del st.session_state.last_preview_params

    # Use adapter for all options rendering
    return render_options_section_adapted(get_ui_adapter())



@with_error_boundary("advanced_options")
def render_advanced_options() -> Tuple[float, float, int, int, int, int, int]:  # returns (gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, cols)
    """Render the advanced options section and return advanced option values. Migrated from sections.py"""
    # Use adapter for all advanced options rendering
    return render_advanced_options_adapted(get_ui_adapter())


@with_error_boundary("options_section_adapted")
def render_options_section_adapted(adapter: UIAdapter) -> Tuple[bool, bool, str, float]:
    """Render options section using UI adapter."""
    adapter.header("⚙️ 选项")
    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        pinyin_config = ComponentConfig(
            key="auto_pinyin_adapted",
            label="自动添加拼音",
            help_text="自动为汉字添加拼音注音"
        )
        auto_pinyin = adapter.inputs.checkbox(pinyin_config, value=True)

        translate_config = ComponentConfig(
            key="auto_translate_adapted",
            label="自动翻译",
            help_text="自动翻译中文到英文"
        )
        auto_translate = adapter.inputs.checkbox(translate_config, value=True)
    with col2:
        page_config = ComponentConfig(
            key="page_size_adapted",
            label="页面大小",
            help_text="选择页面大小"
        )
        page_size = adapter.inputs.selectbox(
            page_config,
            options=["A4", "A5", "Letter"],
            value="A4"
        )

        card_config = ComponentConfig(
            key="card_size_adapted",
            label="卡片大小 (cm)",
            help_text="设置卡片大小"
        )
        card_size = adapter.inputs.slider(
            card_config,
            min_value=5.0,
            max_value=15.0,
            value=8.0,
            step=0.5
        )
    return auto_pinyin, auto_translate, page_size, card_size


@with_error_boundary("advanced_options_adapted")
def render_advanced_options_adapted(adapter: UIAdapter) -> Tuple[float, float, int, int, int, int, int]:
    """Render advanced options using UI adapter."""
    adapter.header("🎨 高级选项")
    # Layout options
    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        gap_config = ComponentConfig(
            key="gap_cm_adapted",
            label="卡片间距 (cm)",
            help_text="设置卡片之间的间距"
        )
        gap_cm = adapter.inputs.slider(
            gap_config,
            min_value=0.2,
            max_value=1.0,
            value=0.5,
            step=0.1
        )

        margin_config = ComponentConfig(
            key="margin_cm_adapted",
            label="页面边距 (cm)",
            help_text="设置页面边距"
        )
        margin_cm = adapter.inputs.slider(
            margin_config,
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )
    with col2:
        cols_config = ComponentConfig(
            key="layout_cols_adapted",
            label="每行卡片数 (列)",
            help_text="设置每行显示的卡片数量"
        )
        layout_cols = adapter.inputs.number_input(
            cols_config,
            min_value=1,
            max_value=10,
            value=3,
            step=1
        )

        rows_config = ComponentConfig(
            key="layout_rows_adapted",
            label="每列卡片数 (行)",
            help_text="设置每列显示的卡片数量"
        )
        layout_rows = adapter.inputs.number_input(
            rows_config,
            min_value=1,
            max_value=10,
            value=2,
            step=1
        )
    # Font size options
    adapter.subheader("字体大小")
    font_col1, font_col2, font_col3 = adapter.layout.columns([1, 1, 1])

    with font_col1:
        hanzi_font_config = ComponentConfig(
            key="hanzi_font_size_adapted",
            label="汉字字体大小",
            help_text="设置汉字的字体大小"
        )
        hanzi_font_size = adapter.inputs.number_input(
            hanzi_font_config,
            min_value=12,
            max_value=72,
            value=48,
            step=2
        )

    with font_col2:
        pinyin_font_config = ComponentConfig(
            key="pinyin_font_size_adapted",
            label="拼音字体大小",
            help_text="设置拼音的字体大小"
        )
        pinyin_font_size = adapter.inputs.number_input(
            pinyin_font_config,
            min_value=8,
            max_value=36,
            value=18,
            step=1
        )

    with font_col3:
        english_font_config = ComponentConfig(
            key="english_font_size_adapted",
            label="英文字体大小",
            help_text="设置英文的字体大小"
        )
        english_font_size = adapter.inputs.number_input(
            english_font_config,
            min_value=8,
            max_value=36,
            value=14,
            step=1
        )
    return gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols
# Export functions for compatibility
__all__ = [
    'render_options_section',
    'render_advanced_options',
    'render_options_section_adapted',
    'render_advanced_options_adapted'
]







@with_error_boundary("advanced_options")
def render_advanced_options() -> Tuple[float, float, int, int, int, int, int]:  # returns (gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, cols)
    """Render the advanced options section and return advanced option values. Migrated from sections.py"""
    # Use adapter for all advanced options rendering
    return render_advanced_options_adapted(get_ui_adapter())


@with_error_boundary("advanced_options_adapted")
def render_advanced_options_adapted(adapter: UIAdapter) -> Tuple[float, float, int, int, int, int, int]:
    """Render advanced options using UI adapter."""
    adapter.header("🎨 高级选项")

    # Layout options
    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        gap_config = ComponentConfig(
            key="gap_cm_adapted",
            label="卡片间距 (cm)",
            help_text="设置卡片之间的间距"
        )
        gap_cm = adapter.inputs.slider(
            gap_config,
            min_value=0.2,
            max_value=1.0,
            value=0.5,
            step=0.1
        )

        margin_config = ComponentConfig(
            key="margin_cm_adapted",
            label="页面边距 (cm)",
            help_text="设置页面边距"
        )
        margin_cm = adapter.inputs.slider(
            margin_config,
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1
        )

        cols_config = ComponentConfig(
            key="layout_cols_adapted",
            label="每行卡片数 (列)",
            help_text="设置每行显示的卡片数量"
        )
        layout_cols = adapter.inputs.number_input(
            cols_config,
            min_value=1,
            max_value=10,
            value=3,
            step=1
        )
    with col2:
        rows_config = ComponentConfig(
            key="layout_rows_adapted",
            label="每列卡片数 (行)",
            help_text="设置每列显示的卡片数量"
        )
        layout_rows = adapter.inputs.number_input(
            rows_config,
            min_value=1,
            max_value=10,
            value=2,
            step=1
        )

    # Font size options
    adapter.subheader("字体大小")
    font_col1, font_col2, font_col3 = adapter.layout.columns([1, 1, 1])

    with font_col1:
        hanzi_font_config = ComponentConfig(
            key="hanzi_font_size_adapted",
            label="汉字字体大小",
            help_text="设置汉字的字体大小"
        )
        hanzi_font_size = adapter.inputs.number_input(
            hanzi_font_config,
            min_value=12,
            max_value=72,
            value=48,
            step=2
        )

    with font_col2:
        pinyin_font_config = ComponentConfig(
            key="pinyin_font_size_adapted",
            label="拼音字体大小",
            help_text="设置拼音的字体大小"
        )
        pinyin_font_size = adapter.inputs.number_input(
            pinyin_font_config,
            min_value=8,
            max_value=36,
            value=18,
            step=1
        )

    with font_col3:
        english_font_config = ComponentConfig(
            key="english_font_size_adapted",
            label="英文字体大小",
            help_text="设置英文的字体大小"
        )
        english_font_size = adapter.inputs.number_input(
            english_font_config,
            min_value=8,
            max_value=36,
            value=14,
            step=1
        )

    return gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols

















@with_error_boundary("options_section_adapted")
def render_options_section_adapted(adapter: UIAdapter) -> Tuple[bool, bool, str, float, Dict[str, Any]]:
    """Render options section using UI adapter.
    Avoid context managers so simple Mocks work in tests.
    """
    adapter.header("⚙️ 选项")

    # Direct calls without column context managers (play nice with Mock)
    auto_pinyin = st.checkbox(
        "自动添加拼音",
        value=True,
        key="auto_pinyin_adapted",
        help="自动为汉字添加拼音注音"
    )

    auto_translate = st.checkbox(
        "自动翻译",
        value=True,
        key="auto_translate_adapted",
        help="自动翻译中文到英文"
    )

    page_size = st.selectbox(
        "页面大小",
        options=["A4", "Letter"],
        index=0,
        key="page_size_adapted",
        help="选择导出文件的页面大小"
    )

    card_size_cm = st.slider(
        "卡片大小 (cm)",
        min_value=3.0,
        max_value=10.0,
        value=5.5,
        step=0.1,
        key="card_size_adapted",
        help="设置每张卡片的大小"
    )

    layout_info: Dict[str, Any] = {
        'columns': 2,
        'section': 'options'
    }
    return auto_pinyin, auto_translate, page_size, card_size_cm, layout_info


@with_error_boundary("advanced_options_adapted")
def render_advanced_options_adapted(adapter: UIAdapter) -> Tuple[float, float, int, int, int, int, int]:
    """Render advanced options using UI adapter.
    Avoid context managers so simple Mocks work in tests.
    """
    adapter.header("🎨 高级选项")

    # Layout settings (direct calls)
    adapter.subheader("📐 布局设置")
    gap_cm = st.slider(
        "卡片间距 (cm)",
        min_value=0.0,
        max_value=2.0,
        value=0.5,
        step=0.1,
        key="gap_adapted",
        help="卡片之间的间距"
    )

    margin_cm = st.slider(
        "页面边距 (cm)",
        min_value=0.0,
        max_value=3.0,
        value=1.0,
        step=0.1,
        key="margin_adapted",
        help="页面四周的边距"
    )

    # Number inputs: columns then rows ordering
    layout_cols = st.number_input(
        "列数",
        value=3,
        min_value=1,
        max_value=10,
        step=1,
        key="cols_adapted",
        help="每页的列数"
    )

    layout_rows = st.number_input(
        "行数",
        value=2,
        min_value=1,
        max_value=10,
        step=1,
        key="rows_adapted",
        help="每页的行数"
    )

    # Typography settings
    adapter.subheader("🔤 字体设置")
    hanzi_font_size = st.number_input(
        "汉字字体大小",
        value=48,
        min_value=20,
        max_value=100,
        step=2,
        key="font_hanzi_adapted",
        help="汉字的字体大小"
    )

    pinyin_font_size = st.number_input(
        "拼音字体大小",
        value=18,
        min_value=10,
        max_value=40,
        step=1,
        key="font_pinyin_adapted",
        help="拼音的字体大小"
    )

    english_font_size = st.number_input(
        "英文字体大小",
        value=14,
        min_value=8,
        max_value=30,
        step=1,
        key="font_english_adapted",
        help="英文的字体大小"
    )

    # Visual settings
    adapter.subheader("🎨 视觉设置")
    _ = st.selectbox(
        "汉字字体",
        options=HANZI_FONT_OPTIONS,
        index=0,
        key="hanzi_font_adapted",
        help="选择汉字字体"
    )

    _ = st.selectbox(
        "背景颜色",
        options=PRESET_COLORS,
        index=0,
        key="background_color_adapted"
    )

    return gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols


def collect_all_options() -> Dict[str, Any]:
    """Collect all option values into a dictionary."""
    auto_pinyin, auto_translate, page_size, card_size_cm = render_options_section()
    gap, margin, hanzi_font_size, pinyin_font_size, english_font_size, hanzi_font_family, background_color = render_advanced_options()
    
    return {
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size_cm': card_size_cm,
        'gap_cm': gap,
        'margin_cm': margin,
        'hanzi_font_size': hanzi_font_size,
        'pinyin_font_size': pinyin_font_size,
        'english_font_size': english_font_size,
        'hanzi_font_family': hanzi_font_family,
        'background_color': background_color
    }


def collect_all_options_adapted(adapter: UIAdapter) -> Dict[str, Any]:
    """Collect all option values using UI adapter."""
    auto_pinyin, auto_translate, page_size, card_size_cm, _layout_info = render_options_section_adapted(adapter)
    gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = render_advanced_options_adapted(adapter)

    return {
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size_cm': card_size_cm,
        'gap_cm': gap_cm,
        'margin_cm': margin_cm,
        'hanzi_font_size': hanzi_font_size,
        'pinyin_font_size': pinyin_font_size,
        'english_font_size': english_font_size,
        'layout_rows': layout_rows,
        'layout_cols': layout_cols
    }


def use_adapted_options() -> bool:
    """Check if adapted options should be used."""
    return True


# Export the main functions
__all__ = [
    'render_options_section',
    'render_advanced_options',
    'render_options_section_adapted',
    'render_advanced_options_adapted',
    'collect_all_options',
    'collect_all_options_adapted',
    'use_adapted_options'
]
