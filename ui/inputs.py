"""
Input handling module for the UI refactor.
Handles text input, CSV upload, and input processing.
Migrated from ui/sections.py
"""

import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from io import StringIO

from services.processing import parse_input_text, auto_segment_text
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


@with_error_boundary("input_section")
@with_error_boundary("input_section")
def render_input_section() -> List[Dict[str, str]]:
    """Render the input section and return parsed cards. Migrated from sections.py"""
    # Check if we should use adapter
    from core.feature_flags import get_feature_flag

    # Always use adapter (feature flag enabled by default)
    from ui.ports import get_ui_adapter, ComponentConfig
    adapter = get_ui_adapter()

    adapter.header("📝 输入")

    # Input method selection using adapter
    method_config = ComponentConfig(
        key="input_method",
        label="选择输入方式"
    )
    input_method = adapter.inputs.radio(
        method_config,
        options=["手动输入", "上传CSV文件"],
        index=0,
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

        # Use adapter for template selection (always enabled)
        template_config = ComponentConfig(
            key="template_select",
            label="选择模板",
            help_text="选择预设模板或自定义输入"
        )
        selected_template = adapter.inputs.selectbox(
            template_config,
            options=list(templates.keys()),
            index=0
        )
        adapter.markdown('<span data-testid="select-template" style="display:none"></span>', unsafe_allow_html=True)

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
                                from services.cache_v2 import clear_preview_cache
                                clear_preview_cache()
                            except Exception:
                                pass
                            if 'last_preview_params' in st.session_state:
                                del st.session_state.last_preview_params
                    except ImportError:
                        # Fallback if new modules not available
                        st.session_state.input_text = new_text
                        try:
                            from services.cache_v2 import clear_preview_cache
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
        col_text, col_btn = adapter.layout.columns([4, 1])

        with col_text:
            # Use adapter for text area
            text_config = ComponentConfig(
                key="input_text",
                label="输入汉字（空格分隔）",
                help_text="输入汉字，用空格分隔。支持单字、词语和短句。"
            )
            # Note: adapter text_area might need additional parameters
            text_value = adapter.inputs.text_area(
                text_config,
                value=st.session_state.get('input_text', ''),
                height_cm=150,
                placeholder="例如：你好 世界 学习 中文"
            )
            # Update session state with new value
            st.session_state.input_text = text_value

            adapter.markdown('<span data-testid="input-hanzi" style="display:none"></span>', unsafe_allow_html=True)

            # 智能分词选项
            preserve_config = ComponentConfig(
                key="preserve_duplicates",
                label="保留重复词",
                help_text="勾选后智能分词将保留重复的词汇，不勾选则自动去重"
            )
            preserve_duplicates = adapter.inputs.checkbox(
                preserve_config,
                value=st.session_state.get('preserve_duplicates', False)
            )

            # Debug marker
            adapter.markdown(
                f'<span data-testid="dbg-preserve-duplicates" style="display:none">{int(st.session_state.get("preserve_duplicates", False))}</span>',
                unsafe_allow_html=True
            )

        with col_btn:
            # Use adapter for spacing and button
            adapter.write("")  # Add some spacing
            adapter.write("")  # Add some spacing

            segment_config = ComponentConfig(
                key="segment_btn",
                label="🔄 智能分词",
                help_text="对输入文本进行智能分词"
            )
            if adapter.inputs.button(segment_config, use_container_width=True):
                # Capture checkbox state at click time to avoid race conditions
                st.session_state.pending_preserve_duplicates = st.session_state.get('preserve_duplicates', False)
                # Trigger apply on next run; the apply step will read and persist the snapshot
                st.session_state.apply_segmentation = True
                adapter.rerun()

        # Parse input text
        text_input = st.session_state.input_text
        if text_input.strip():
            cards = parse_input_text(text_input)

    else:  # CSV upload
        adapter.markdown('<span data-testid="csv-upload" style="display:none"></span>', unsafe_allow_html=True)

        upload_config = ComponentConfig(
            key="csv_upload",
            label="选择CSV文件",
            help_text="上传包含汉字的CSV文件"
        )
        uploaded_file = adapter.inputs.file_uploader(upload_config, type=['csv'])
        if uploaded_file is not None:
            try:
                # Read CSV
                stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
                df = pd.read_csv(stringio)

                # Validate columns
                required_cols = ['hanzi']
                if not all(col in df.columns for col in required_cols):
                    adapter.notifications.show_error(f"CSV文件必须包含以下列: {', '.join(required_cols)}")
                    return []

                # Convert to cards format
                for _, row in df.iterrows():
                    cards.append({
                        'hanzi': str(row['hanzi']),
                        'pinyin': str(row.get('pinyin', '')),
                        'english': str(row.get('english', ''))
                    })

                adapter.notifications.show_success(f"成功读取 {len(cards)} 张卡片")

            except Exception as e:
                adapter.notifications.show_error(f"读取CSV文件时出错: {e}")
                return []
        else:
            adapter.notifications.show_info("请上传CSV文件")

    return cards


# Legacy simplified functions removed - using full implementation above


def render_input_section_adapted(adapter: UIAdapter) -> List[Dict[str, str]]:
    """
    Render input section using UI adapter.
    Framework-agnostic version for future migration.
    """
    adapter.header("📝 输入")

    # Input method selection
    method_config = ComponentConfig(
        key="input_method_adapted",
        label="选择输入方式"
    )
    input_method = adapter.inputs.radio(
        method_config, 
        options=["手动输入", "上传CSV文件"], 
        index=0, 
        horizontal=True
    )

    cards = []

    if input_method == "手动输入":
        cards = render_manual_input_adapted(adapter)
    else:
        cards = render_csv_upload_adapted(adapter)

    return cards


def render_manual_input_adapted(adapter: UIAdapter) -> List[Dict[str, str]]:
    """Render manual input using UI adapter."""
    # Text input area
    input_config = ComponentConfig(
        key="input_text_adapted",
        label="输入中文文本（每行一个词或短语）",
        help_text="输入要制作卡片的中文文本，每行一个词或短语"
    )
    input_text = adapter.inputs.text_area(input_config, value="", height=200)

    # Processing options
    col1, col2 = adapter.layout.columns([1, 1])
    
    with col1:
        segment_config = ComponentConfig(
            key="use_segmented_adapted",
            label="使用智能分词",
            help_text="自动将长句分割成词语"
        )
        use_segmented = adapter.inputs.checkbox(segment_config, value=False)
    
    with col2:
        reprocess_config = ComponentConfig(
            key="reprocess_btn_adapted",
            label="🔄 重新处理"
        )
        if adapter.inputs.button(reprocess_config):
            adapter.notifications.show_message(
                "重新处理输入文本", NotificationLevel.INFO
            )

    # Process input text
    cards = []
    if input_text.strip():
        try:
            if use_segmented:
                segmented_text = auto_segment_text(input_text)
                cards = parse_input_text(segmented_text)
                
                # Show segmentation result
                with adapter.layout.expander("🔍 分词结果", expanded=False):
                    result_config = ComponentConfig(
                        key="segmented_result_adapted",
                        label="分词后的文本",
                        disabled=True
                    )
                    adapter.inputs.text_area(result_config, value=segmented_text, height_cm=100)
            else:
                cards = parse_input_text(input_text)
                
        except Exception as e:
            adapter.notifications.show_message(
                f"处理失败: {str(e)}", NotificationLevel.ERROR
            )

    return cards


def render_csv_upload_adapted(adapter: UIAdapter) -> List[Dict[str, str]]:
    """Render CSV upload using UI adapter."""
    upload_config = ComponentConfig(
        key="csv_upload_adapted",
        label="选择CSV文件",
        help_text="CSV文件应包含 hanzi, pinyin, english 列"
    )
    uploaded_file = adapter.inputs.file_uploader(
        upload_config, accepted_types=['csv']
    )

    cards = []

    if uploaded_file is not None:
        try:
            # Note: In real implementation, this would need to handle
            # file reading through the adapter interface
            adapter.notifications.show_message(
                "CSV文件上传功能需要完整的适配器实现", 
                NotificationLevel.INFO
            )
            
        except Exception as e:
            adapter.notifications.show_message(
                f"读取CSV文件失败: {str(e)}", NotificationLevel.ERROR
            )

    return cards


def use_adapted_inputs() -> bool:
    """Check if adapted inputs should be used."""
    return True


def render_input_section_unified() -> List[Dict[str, str]]:
    """
    Unified input section that chooses between legacy and adapted versions.
    """
    if use_adapted_inputs():
        adapter = get_ui_adapter()
        return render_input_section_adapted(adapter)
    else:
        return render_input_section()


# Export the main function
__all__ = [
    'render_input_section',
    'render_input_section_adapted', 
    'render_input_section_unified',
    'use_adapted_inputs'
]
