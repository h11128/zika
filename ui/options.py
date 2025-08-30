"""
Options management module for the UI refactor.
Handles processing options, layout settings, and advanced configuration.
Migrated from ui/sections.py
"""

import streamlit as st
from typing import Tuple, Dict, Any

from core.constants import HANZI_FONT_OPTIONS, PRESET_COLORS
from core.feature_flags import get_feature_flag
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
        st.session_state.auto_fill = False
        st.session_state._disable_auto_fill_requested = False
        from services.cache import clear_preview_cache
        clear_preview_cache()
        if 'last_preview_params' in st.session_state:
            del st.session_state.last_preview_params

    # Check if we should use adapter
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_options', False):
        return render_options_section_adapted(get_ui_adapter())

    # Check if we should use form semantics
    if get_feature_flag('form_semantics', False):
        from ui.forms import form_context, add_form_field, validate_positive_number

        def on_options_submit(form_data: Dict[str, Any]) -> None:
            """Handle options form submission with batch update."""
            # Use debounced batch update if available
            if get_feature_flag('debouncing', False):
                from ui.debounce import debounce_batch_update
                debounce_batch_update(form_data, delay_ms=250)
            else:
                # Direct batch update to session state
                for key, value in form_data.items():
                    st.session_state[key] = value

                # Clear preview cache when options change
                try:
                    from services.cache import clear_preview_cache
                    clear_preview_cache()
                    if 'last_preview_params' in st.session_state:
                        del st.session_state.last_preview_params
                except Exception:
                    pass

        with form_context("options_form", on_options_submit):
            st.subheader("⚙️ 选项")
            col_opt1, col_opt2 = st.columns(2)

            with col_opt1:
                auto_pinyin = st.checkbox("自动生成拼音", value=True)
                st.markdown('<span data-testid="toggle-auto-pinyin" style="display:none"></span>', unsafe_allow_html=True)
                auto_translate = st.checkbox("自动生成翻译", value=True)

                # Add to form context with validation
                add_form_field("auto_pinyin", auto_pinyin)
                add_form_field("auto_translate", auto_translate)

                # Add page size and card size with validation
                add_form_field("page_size", page_size)
                add_form_field("card_size", card_size, validate_positive_number, "卡片大小必须为正数")
    else:
        # Legacy implementation
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

            # Use debouncing for card size changes
            from core.feature_flags import get_feature_flag
            if get_feature_flag('debouncing', False) and card_size != prev_card_size:
                from ui.debounce import debounce_state_update
                debounce_state_update('card_size', card_size, delay_ms=200)
            else:
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


@with_error_boundary("advanced_options")
def render_advanced_options() -> Tuple[float, float, int, int, int, int, int]:  # returns (gap, margin, font_hanzi, font_pinyin, font_english, rows, cols)
    """Render the advanced options section and return advanced option values. Migrated from sections.py"""
    # Check if we should use adapter
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_options', False):
        return render_advanced_options_adapted(get_ui_adapter())

    # Legacy implementation
    with st.expander("🔧 高级选项"):
        # Layout options
        col_layout1, col_layout2 = st.columns(2)
        with col_layout1:
            # Store previous values for change detection (use different keys to avoid conflict)
            prev_gap = st.session_state.get('_prev_gap', 0.5)
            prev_margin = st.session_state.get('_prev_margin', 1.0)
            prev_cols = st.session_state.get('_prev_cols', st.session_state.get('cols', 3))
            prev_rows = st.session_state.get('_prev_rows', st.session_state.get('rows', 2))
            prev_auto_fill = st.session_state.get('_prev_auto_fill', st.session_state.get('auto_fill', True))

            gap = st.slider("卡片间距 (cm)", 0.2, 1.0, 0.5, 0.1, key="gap_cm")
            margin = st.slider("页面边距 (cm)", 0.5, 2.0, 1.0, 0.1, key="margin_cm")
            cols = st.number_input("每行卡片数 (列)", min_value=1, max_value=10, value=st.session_state.get('cols', 3), step=1)
            rows = st.number_input("每列卡片数 (行)", min_value=1, max_value=10, value=st.session_state.get('rows', 2), step=1)
            # Some unit tests patch st.checkbox without supporting **kwargs like key; be resilient
            try:
                auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.get('auto_fill', True), key="auto_fill_advanced")
            except TypeError:
                auto_fill = st.checkbox("自动填充（按边距与间距自动计算卡片大小）", value=st.session_state.get('auto_fill', True))

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
            prev_hanzi_font = st.session_state.get('_prev_hanzi_font', st.session_state.get('hanzi_font', 'SimHei'))
            hanzi_font = st.selectbox(
                "汉字字体",
                HANZI_FONT_OPTIONS,
                index=HANZI_FONT_OPTIONS.index(st.session_state.get('hanzi_font', 'SimHei')),
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
                    value=st.session_state.get('background_color', '#ffffff'),
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
                value=st.session_state.get('background_color', '#ffffff'),
                key="custom_color_hex",
                help="输入 #RRGGBB 或 #RGB 手动设置背景颜色"
            )
            if isinstance(hex_input, str) and hex_input.startswith('#') and len(hex_input) in (4, 7) \
                and hex_input != st.session_state.get('background_color', '#ffffff'):
                st.session_state.background_color = hex_input
                from services.cache import clear_preview_cache
                clear_preview_cache()
                if 'last_preview_params' in st.session_state:
                    del st.session_state.last_preview_params
                st.rerun()

            # Show current color below the picker
            st.write("当前颜色:")
            current_bg = st.session_state.get('background_color', '#ffffff')
            st.markdown(
                f"<div style='width:100px;height:40px;background-color:{current_bg};"
                f"border:2px solid #ccc;border-radius:4px;display:flex;align-items:center;justify-content:center;'>"
                f"<span style='color:white;text-shadow:1px 1px 2px black;font-weight:bold;font-size:12px;'>"
                f"{current_bg}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

            # Detect color change and update after display so picker is mounted this run
            if custom_color != st.session_state.get('background_color', '#ffffff'):
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
            help_text="选择导出文件的页面大小"
        )
        page_size = adapter.inputs.selectbox(
            page_config, options=["A4", "Letter"], index=0
        )

        size_config = ComponentConfig(
            key="card_size_adapted",
            label="卡片大小 (cm)",
            help_text="设置每张卡片的大小"
        )
        card_size = adapter.inputs.slider(
            size_config, value=5.5, min_value=3.0, max_value=10.0, step=0.1
        )

    return auto_pinyin, auto_translate, page_size, card_size


@with_error_boundary("advanced_options_adapted")
def render_advanced_options_adapted(adapter: UIAdapter) -> Tuple[float, float, int, int, int, str, str]:
    """Render advanced options using UI adapter."""
    adapter.header("🎨 高级选项")

    # Layout settings
    adapter.subheader("📐 布局设置")
    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        gap_config = ComponentConfig(
            key="gap_adapted",
            label="卡片间距 (cm)",
            help_text="卡片之间的间距"
        )
        gap = adapter.inputs.slider(
            gap_config, value=0.5, min_value=0.0, max_value=2.0, step=0.1
        )

        rows_config = ComponentConfig(
            key="rows_adapted",
            label="行数",
            help_text="每页的行数"
        )
        rows = adapter.inputs.number_input(
            rows_config, value=2, min_value=1, max_value=10, step=1
        )

    with col2:
        margin_config = ComponentConfig(
            key="margin_adapted",
            label="页面边距 (cm)",
            help_text="页面四周的边距"
        )
        margin = adapter.inputs.slider(
            margin_config, value=1.0, min_value=0.0, max_value=3.0, step=0.1
        )

        cols_config = ComponentConfig(
            key="cols_adapted",
            label="列数",
            help_text="每页的列数"
        )
        cols = adapter.inputs.number_input(
            cols_config, value=3, min_value=1, max_value=10, step=1
        )

    # Typography settings
    adapter.subheader("🔤 字体设置")
    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        hanzi_config = ComponentConfig(
            key="font_hanzi_adapted",
            label="汉字字体大小",
            help_text="汉字的字体大小"
        )
        font_hanzi = adapter.inputs.slider(
            hanzi_config, value=48, min_value=20, max_value=100, step=2
        )

        pinyin_config = ComponentConfig(
            key="font_pinyin_adapted",
            label="拼音字体大小",
            help_text="拼音的字体大小"
        )
        font_pinyin = adapter.inputs.slider(
            pinyin_config, value=18, min_value=10, max_value=40, step=1
        )

    with col2:
        english_config = ComponentConfig(
            key="font_english_adapted",
            label="英文字体大小",
            help_text="英文的字体大小"
        )
        font_english = adapter.inputs.slider(
            english_config, value=14, min_value=8, max_value=30, step=1
        )

        font_config = ComponentConfig(
            key="hanzi_font_adapted",
            label="汉字字体",
            help_text="选择汉字字体"
        )
        hanzi_font = adapter.inputs.selectbox(
            font_config, options=HANZI_FONT_OPTIONS, index=0
        )

    # Visual settings
    adapter.subheader("🎨 视觉设置")
    
    # Color palette (simplified for adapter)
    color_config = ComponentConfig(
        key="background_color_adapted",
        label="背景颜色"
    )
    background_color = adapter.inputs.selectbox(
        color_config, options=PRESET_COLORS, index=0
    )

    return gap, margin, font_hanzi, font_pinyin, font_english, hanzi_font, background_color


def collect_all_options() -> Dict[str, Any]:
    """Collect all option values into a dictionary."""
    auto_pinyin, auto_translate, page_size, card_size = render_options_section()
    gap, margin, font_hanzi, font_pinyin, font_english, hanzi_font, background_color = render_advanced_options()
    
    return {
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'hanzi_font': hanzi_font,
        'background_color': background_color
    }


def collect_all_options_adapted(adapter: UIAdapter) -> Dict[str, Any]:
    """Collect all option values using UI adapter."""
    auto_pinyin, auto_translate, page_size, card_size = render_options_section_adapted(adapter)
    gap, margin, font_hanzi, font_pinyin, font_english, hanzi_font, background_color = render_advanced_options_adapted(adapter)
    
    return {
        'auto_pinyin': auto_pinyin,
        'auto_translate': auto_translate,
        'page_size': page_size,
        'card_size': card_size,
        'gap': gap,
        'margin': margin,
        'font_hanzi': font_hanzi,
        'font_pinyin': font_pinyin,
        'font_english': font_english,
        'hanzi_font': hanzi_font,
        'background_color': background_color
    }


def use_adapted_options() -> bool:
    """Check if adapted options should be used."""
    return get_feature_flag('adapted_options', False)


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
