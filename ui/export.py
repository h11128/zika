"""
Export functionality module for the UI refactor.
Handles PDF, PPTX, and CSV export operations.
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.feature_flags import get_feature_flag
from services.export_pdf import export_to_pdf
from services.export_pptx import export_to_pptx
from services.export_csv import export_to_csv
from ui.error_boundary import with_error_boundary
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel


@with_error_boundary("export_section")
def render_export_section(processed_cards: List[Dict[str, str]], 
                         config: Dict[str, Any]) -> None:
    """Render the export section with all export options."""
    st.header("📤 导出")

    if not processed_cards:
        st.info("请先生成卡片以启用导出功能")
        return

    # Export format selection
    export_format = st.selectbox(
        "选择导出格式",
        ["PDF", "PowerPoint (PPTX)", "CSV"],
        help="选择要导出的文件格式"
    )

    # Export options based on format
    if export_format == "PDF":
        render_pdf_export_options(processed_cards, config)
    elif export_format == "PowerPoint (PPTX)":
        render_pptx_export_options(processed_cards, config)
    else:  # CSV
        render_csv_export_options(processed_cards)


def render_pdf_export_options(processed_cards: List[Dict[str, str]], 
                            config: Dict[str, Any]) -> None:
    """Render PDF export options and button."""
    st.subheader("📄 PDF 导出")

    # PDF-specific options
    col1, col2 = st.columns(2)

    with col1:
        include_page_numbers = st.checkbox(
            "包含页码",
            value=True,
            help="在PDF页面底部添加页码"
        )

        optimize_for_print = st.checkbox(
            "优化打印",
            value=True,
            help="优化PDF以便打印"
        )

    with col2:
        pdf_quality = st.selectbox(
            "PDF质量",
            ["高质量", "标准", "压缩"],
            index=1,
            help="选择PDF输出质量"
        )

    # Export button
    if st.button("📄 导出为PDF", type="primary"):
        with st.spinner("正在生成PDF..."):
            try:
                pdf_data = export_to_pdf(
                    processed_cards,
                    card_size=config.get('card_size', 5.5),
                    gap=config.get('gap', 0.5),
                    margin=config.get('margin', 1.0),
                    font_hanzi=config.get('font_hanzi', 48),
                    font_pinyin=config.get('font_pinyin', 18),
                    font_english=config.get('font_english', 14),
                    page_size=config.get('page_size', 'A4'),
                    hanzi_font=config.get('hanzi_font', 'SimHei'),
                    background_color=config.get('background_color', '#ffffff'),
                    rows=config.get('rows', 2),
                    cols=config.get('cols', 3),
                    auto_fill=config.get('auto_fill', True),
                    include_page_numbers=include_page_numbers,
                    optimize_for_print=optimize_for_print,
                    quality=pdf_quality
                )

                if pdf_data:
                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"chinese_cards_{timestamp}.pdf"

                    # Provide download
                    st.download_button(
                        label="⬇️ 下载PDF文件",
                        data=pdf_data,
                        file_name=filename,
                        mime="application/pdf"
                    )

                    # Record export
                    record_export_history("pdf", len(processed_cards), filename)

                    st.success("PDF导出成功！")
                else:
                    st.error("PDF导出失败")

            except Exception as e:
                st.error(f"PDF导出错误: {str(e)}")


def render_pptx_export_options(processed_cards: List[Dict[str, str]], 
                             config: Dict[str, Any]) -> None:
    """Render PPTX export options and button."""
    st.subheader("📊 PowerPoint 导出")

    # PPTX-specific options
    col1, col2 = st.columns(2)

    with col1:
        slide_layout = st.selectbox(
            "幻灯片布局",
            ["标准布局", "紧凑布局", "大字体布局"],
            help="选择幻灯片的布局样式"
        )

        include_title_slide = st.checkbox(
            "包含标题页",
            value=True,
            help="在演示文稿开头添加标题页"
        )

    with col2:
        cards_per_slide = st.number_input(
            "每页卡片数",
            min_value=1,
            max_value=12,
            value=6,
            help="每张幻灯片显示的卡片数量"
        )

    # Export button
    if st.button("📊 导出为PowerPoint", type="primary"):
        with st.spinner("正在生成PowerPoint..."):
            try:
                pptx_data = export_to_pptx(
                    processed_cards,
                    card_size=config.get('card_size', 5.5),
                    gap=config.get('gap', 0.5),
                    margin=config.get('margin', 1.0),
                    font_hanzi=config.get('font_hanzi', 48),
                    font_pinyin=config.get('font_pinyin', 18),
                    font_english=config.get('font_english', 14),
                    hanzi_font=config.get('hanzi_font', 'SimHei'),
                    background_color=config.get('background_color', '#ffffff'),
                    slide_layout=slide_layout,
                    include_title_slide=include_title_slide,
                    cards_per_slide=cards_per_slide
                )

                if pptx_data:
                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"chinese_cards_{timestamp}.pptx"

                    # Provide download
                    st.download_button(
                        label="⬇️ 下载PowerPoint文件",
                        data=pptx_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )

                    # Record export
                    record_export_history("pptx", len(processed_cards), filename)

                    st.success("PowerPoint导出成功！")
                else:
                    st.error("PowerPoint导出失败")

            except Exception as e:
                st.error(f"PowerPoint导出错误: {str(e)}")


def render_csv_export_options(processed_cards: List[Dict[str, str]]) -> None:
    """Render CSV export options and button."""
    st.subheader("📋 CSV 导出")

    # CSV-specific options
    col1, col2 = st.columns(2)

    with col1:
        include_headers = st.checkbox(
            "包含列标题",
            value=True,
            help="在CSV文件中包含列标题行"
        )

        encoding = st.selectbox(
            "文件编码",
            ["UTF-8", "GBK", "UTF-8 BOM"],
            help="选择CSV文件的字符编码"
        )

    with col2:
        delimiter = st.selectbox(
            "分隔符",
            [",", ";", "\t"],
            format_func=lambda x: {"," : "逗号 (,)", ";" : "分号 (;)", "\t" : "制表符"}[x],
            help="选择CSV字段分隔符"
        )

    # Export button
    if st.button("📋 导出为CSV", type="primary"):
        try:
            csv_data = export_to_csv(
                processed_cards,
                include_headers=include_headers,
                encoding=encoding,
                delimiter=delimiter
            )

            if csv_data:
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"chinese_cards_{timestamp}.csv"

                # Provide download
                st.download_button(
                    label="⬇️ 下载CSV文件",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv"
                )

                # Record export
                record_export_history("csv", len(processed_cards), filename)

                st.success("CSV导出成功！")
            else:
                st.error("CSV导出失败")

        except Exception as e:
            st.error(f"CSV导出错误: {str(e)}")


def render_export_section_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]], 
                                config: Dict[str, Any]) -> None:
    """Render export section using UI adapter."""
    adapter.header("📤 导出")

    if not processed_cards:
        adapter.notifications.show_message(
            "请先生成卡片以启用导出功能", NotificationLevel.INFO
        )
        return

    # Export format selection
    format_config = ComponentConfig(
        key="export_format_adapted",
        label="选择导出格式",
        help_text="选择要导出的文件格式"
    )
    export_format = adapter.inputs.selectbox(
        format_config, 
        options=["PDF", "PowerPoint (PPTX)", "CSV"], 
        index=0
    )

    # Export options based on format
    if export_format == "PDF":
        render_pdf_export_adapted(adapter, processed_cards, config)
    elif export_format == "PowerPoint (PPTX)":
        render_pptx_export_adapted(adapter, processed_cards, config)
    else:  # CSV
        render_csv_export_adapted(adapter, processed_cards)


def render_pdf_export_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]], 
                            config: Dict[str, Any]) -> None:
    """Render PDF export using UI adapter."""
    adapter.subheader("📄 PDF 导出")

    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        page_numbers_config = ComponentConfig(
            key="include_page_numbers_adapted",
            label="包含页码",
            help_text="在PDF页面底部添加页码"
        )
        include_page_numbers = adapter.inputs.checkbox(page_numbers_config, value=True)

    with col2:
        quality_config = ComponentConfig(
            key="pdf_quality_adapted",
            label="PDF质量",
            help_text="选择PDF输出质量"
        )
        pdf_quality = adapter.inputs.selectbox(
            quality_config, options=["高质量", "标准", "压缩"], index=1
        )

    # Export button
    export_config = ComponentConfig(
        key="export_pdf_adapted",
        label="📄 导出为PDF"
    )
    if adapter.inputs.button(export_config):
        adapter.notifications.show_message(
            "PDF导出功能需要完整的文件处理实现", NotificationLevel.INFO
        )


def render_pptx_export_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]], 
                             config: Dict[str, Any]) -> None:
    """Render PPTX export using UI adapter."""
    adapter.subheader("📊 PowerPoint 导出")

    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        layout_config = ComponentConfig(
            key="slide_layout_adapted",
            label="幻灯片布局",
            help_text="选择幻灯片的布局样式"
        )
        slide_layout = adapter.inputs.selectbox(
            layout_config, options=["标准布局", "紧凑布局", "大字体布局"], index=0
        )

    with col2:
        cards_config = ComponentConfig(
            key="cards_per_slide_adapted",
            label="每页卡片数",
            help_text="每张幻灯片显示的卡片数量"
        )
        cards_per_slide = adapter.inputs.number_input(
            cards_config, value=6, min_value=1, max_value=12, step=1
        )

    # Export button
    export_config = ComponentConfig(
        key="export_pptx_adapted",
        label="📊 导出为PowerPoint"
    )
    if adapter.inputs.button(export_config):
        adapter.notifications.show_message(
            "PowerPoint导出功能需要完整的文件处理实现", NotificationLevel.INFO
        )


def render_csv_export_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]]) -> None:
    """Render CSV export using UI adapter."""
    adapter.subheader("📋 CSV 导出")

    col1, col2 = adapter.layout.columns([1, 1])

    with col1:
        headers_config = ComponentConfig(
            key="include_headers_adapted",
            label="包含列标题",
            help_text="在CSV文件中包含列标题行"
        )
        include_headers = adapter.inputs.checkbox(headers_config, value=True)

    with col2:
        encoding_config = ComponentConfig(
            key="encoding_adapted",
            label="文件编码",
            help_text="选择CSV文件的字符编码"
        )
        encoding = adapter.inputs.selectbox(
            encoding_config, options=["UTF-8", "GBK", "UTF-8 BOM"], index=0
        )

    # Export button
    export_config = ComponentConfig(
        key="export_csv_adapted",
        label="📋 导出为CSV"
    )
    if adapter.inputs.button(export_config):
        adapter.notifications.show_message(
            "CSV导出功能需要完整的文件处理实现", NotificationLevel.INFO
        )


def record_export_history(format_type: str, card_count: int, filename: str) -> None:
    """Record export operation in history."""
    if 'export_history' not in st.session_state:
        st.session_state.export_history = []

    export_record = {
        'timestamp': datetime.now().isoformat(),
        'format_type': format_type,
        'card_count': card_count,
        'filename': filename
    }

    st.session_state.export_history.append(export_record)

    # Keep only last 50 exports
    if len(st.session_state.export_history) > 50:
        st.session_state.export_history = st.session_state.export_history[-50:]


def use_adapted_export() -> bool:
    """Check if adapted export should be used."""
    return get_feature_flag('adapted_export', False)


def render_export_section_unified(processed_cards: List[Dict[str, str]],
                                config: Dict[str, Any]) -> None:
    """
    Unified export section that uses shared render core for all exports.
    """
    from core.feature_flags import get_feature_flag

    # Always use shared render core if available
    if get_feature_flag('shared_render_core', False):
        render_export_section_with_shared_core(processed_cards, config)
    elif use_adapted_export():
        adapter = get_ui_adapter()
        render_export_section_adapted(adapter, processed_cards, config)
    else:
        render_export_section(processed_cards, config)


def render_export_section_with_shared_core(processed_cards: List[Dict[str, str]],
                                          config: Dict[str, Any]) -> None:
    """
    Export section using shared render core for consistent rendering.
    """
    from ui.unified import get_unified_ui

    ui = get_unified_ui()
    ui.header("📤 导出")

    if not processed_cards:
        ui.info("请先生成卡片以启用导出功能")
        return

    # Export format selection
    export_format = ui.selectbox(
        "选择导出格式",
        ["PDF", "PowerPoint (PPTX)", "CSV"],
        help_text="选择要导出的文件格式"
    )

    # Export options and download button
    if export_format == "PDF":
        render_unified_pdf_export(ui, processed_cards, config)
    elif export_format == "PowerPoint (PPTX)":
        render_unified_pptx_export(ui, processed_cards, config)
    else:  # CSV
        render_unified_csv_export(ui, processed_cards)


def render_unified_pdf_export(ui, processed_cards: List[Dict[str, str]],
                             config: Dict[str, Any]) -> None:
    """Render PDF export using shared render core."""
    ui.write("**PDF 导出选项**")

    # Export button
    if ui.button("📄 下载 PDF", key="download_pdf_unified"):
        try:
            from services.render_core import render_cards_unified, create_render_options_from_legacy

            # Create render options from config
            render_options = create_render_options_from_legacy(
                card_size=config.get('card_size', 5.5),
                gap=config.get('gap', 0.5),
                margin=config.get('margin', 1.0),
                font_hanzi=config.get('font_hanzi', 48),
                font_pinyin=config.get('font_pinyin', 18),
                font_english=config.get('font_english', 14),
                page_size=config.get('page_size', 'A4'),
                hanzi_font=config.get('hanzi_font', 'SimHei'),
                background_color=config.get('background_color', '#ffffff'),
                rows=config.get('rows', 2),
                cols=config.get('cols', 3),
                auto_fill=config.get('auto_fill', True)
            )

            # Render PDF using shared core
            result = render_cards_unified(processed_cards, render_options, output_format='pdf')

            if result.success:
                # Create download
                filename = f"chinese_cards_{len(processed_cards)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                ui.download_button(
                    label="📄 下载 PDF 文件",
                    data=result.content,
                    file_name=filename,
                    mime="application/pdf"
                )

                # Record export history
                record_export_history(processed_cards, 'pdf', filename)
                ui.success(f"PDF 已生成！包含 {result.card_count} 张卡片，共 {result.page_count} 页。")
            else:
                ui.error(f"PDF 生成失败：{result.error_message}")

        except Exception as e:
            ui.error(f"导出失败：{str(e)}")


def render_unified_pptx_export(ui, processed_cards: List[Dict[str, str]],
                              config: Dict[str, Any]) -> None:
    """Render PPTX export using shared render core."""
    ui.write("**PowerPoint 导出选项**")

    # Export button
    if ui.button("📊 下载 PPTX", key="download_pptx_unified"):
        try:
            from services.render_core import render_cards_unified, create_render_options_from_legacy

            # Create render options from config
            render_options = create_render_options_from_legacy(
                card_size=config.get('card_size', 5.5),
                gap=config.get('gap', 0.5),
                margin=config.get('margin', 1.0),
                font_hanzi=config.get('font_hanzi', 48),
                font_pinyin=config.get('font_pinyin', 18),
                font_english=config.get('font_english', 14),
                page_size=config.get('page_size', 'A4'),
                hanzi_font=config.get('hanzi_font', 'SimHei'),
                background_color=config.get('background_color', '#ffffff'),
                rows=config.get('rows', 2),
                cols=config.get('cols', 3),
                auto_fill=config.get('auto_fill', True)
            )

            # Render PPTX using shared core
            result = render_cards_unified(processed_cards, render_options, output_format='pptx')

            if result.success:
                # Create download
                filename = f"chinese_cards_{len(processed_cards)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pptx"
                ui.download_button(
                    label="📊 下载 PPTX 文件",
                    data=result.content,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                )

                # Record export history
                record_export_history(processed_cards, 'pptx', filename)
                ui.success(f"PPTX 已生成！包含 {result.card_count} 张卡片，共 {result.page_count} 页。")
            else:
                ui.error(f"PPTX 生成失败：{result.error_message}")

        except Exception as e:
            ui.error(f"导出失败：{str(e)}")


def render_unified_csv_export(ui, processed_cards: List[Dict[str, str]]) -> None:
    """Render CSV export (no shared core needed for CSV)."""
    ui.write("**CSV 导出选项**")

    # Export button
    if ui.button("📊 下载 CSV", key="download_csv_unified"):
        try:
            from services.export_csv import export_to_csv

            # Generate CSV content
            csv_content = export_to_csv(processed_cards)

            # Create download
            filename = f"chinese_cards_{len(processed_cards)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            ui.download_button(
                label="📊 下载 CSV 文件",
                data=csv_content,
                file_name=filename,
                mime="text/csv"
            )

            # Record export history
            record_export_history(processed_cards, 'csv', filename)
            ui.success(f"CSV 已生成！包含 {len(processed_cards)} 张卡片。")

        except Exception as e:
            ui.error(f"导出失败：{str(e)}")


# Export the main functions
__all__ = [
    'render_export_section',
    'render_export_section_adapted',
    'render_export_section_unified',
    'render_export_section_with_shared_core',
    'record_export_history',
    'use_adapted_export'
]
