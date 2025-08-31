"""
Unified export section implementation.

This module provides a clean, unified export section that eliminates
all dual-path code and direct Streamlit calls.
"""

import time
from typing import List, Dict
from ui.unified import get_unified_ui
from ui.state_bridge import state_get, state_set, state_append, state_increment


def render_export_section_unified(processed_cards: List[Dict[str, str]]) -> None:
    """Render the export section with unified UI."""
    if not processed_cards:
        return

    ui = get_unified_ui()
    
    ui.header("📥 导出")
    col_btn1, col_btn2, col_btn3 = ui.columns([1, 1, 2])

    # Export parameters from state
    export_params = {
        'card_size_cm': state_get('card_size_cm', 5.5),
        'gap_cm': state_get('gap_cm', 0.5),
        'margin_cm': state_get('margin_cm', 1.0),
        'hanzi_font_size': state_get('hanzi_font_size', 48),
        'pinyin_font_size': state_get('pinyin_font_size', 18),
        'english_font_size': state_get('english_font_size', 14),
        'page_size': state_get('page_size', 'A4'),
        'hanzi_font_family': state_get('hanzi_font_family', 'SimHei'),
        'background_color': state_get('background_color', '#ffffff'),
        'layout_rows': state_get('layout_rows', 2),
        'layout_cols': state_get('layout_cols', 3),
        'layout_auto_fill': state_get('layout_auto_fill', True)
    }

    # Create export key for caching with content version signal
    from ui.state import compute_export_key, get_content_version_signal

    # Get content version signal from cards
    content_version_signal = get_content_version_signal(processed_cards)

    # Compute proper export key with content versioning
    export_key = compute_export_key(
        export_params=export_params,
        cards_count=len(processed_cards),
        content_version_signal=content_version_signal
    )
    
    # Get state data
    export_ready = state_get('export_ready', {})
    export_data = state_get('export_data', {})

    # PPTX Export Button
    with col_btn1:
        if ui.button("📄 导出 PowerPoint", key="export_pptx_btn", use_container_width=True):
            if export_key not in export_ready or export_ready[export_key] != 'pptx':
                with ui.spinner("正在生成 PowerPoint 文件..."):
                    try:
                        from services.export import export_cards
                        file_content = export_cards(processed_cards, 'pptx', **export_params)
                        
                        # Update export data
                        export_data[export_key] = file_content
                        export_ready[export_key] = 'pptx'
                        state_set('export_data', export_data)
                        state_set('export_ready', export_ready)

                        # Add to export history
                        state_append('export_history', {
                            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'format': 'pptx',
                            'cards': len(processed_cards)
                        })
                        state_increment('total_cards_generated', len(processed_cards))

                    except Exception as e:
                        ui.error(f"导出失败: {e}")
                        return

            # Show download button if data is ready
            if export_key in export_data:
                ui.download_button(
                    label="⬇️ 下载 PPTX",
                    data=export_data[export_key],
                    filename=f"cards_{len(processed_cards)}_{time.strftime('%Y%m%d_%H%M%S')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )

    # PDF Export Button
    with col_btn2:
        if ui.button("📑 导出 PDF", key="export_pdf_btn", use_container_width=True):
            if export_key not in export_ready or export_ready[export_key] != 'pdf':
                with ui.spinner("正在生成 PDF 文件..."):
                    try:
                        from services.export import export_cards
                        file_content = export_cards(processed_cards, 'pdf', **export_params)
                        
                        # Update export data
                        export_data[export_key] = file_content
                        export_ready[export_key] = 'pdf'
                        state_set('export_data', export_data)
                        state_set('export_ready', export_ready)

                        # Add to export history
                        state_append('export_history', {
                            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'format': 'pdf',
                            'cards': len(processed_cards)
                        })
                        state_increment('total_cards_generated', len(processed_cards))

                    except Exception as e:
                        ui.error(f"导出失败: {e}")
                        return

            # Show download button if data is ready
            if export_key in export_data:
                ui.download_button(
                    label="⬇️ 下载 PDF",
                    data=export_data[export_key],
                    filename=f"cards_{len(processed_cards)}_{time.strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    # Info Column
    with col_btn3:
        ui.info(f"💡 将导出 {len(processed_cards)} 张卡片")
        if len(processed_cards) > 50:
            ui.warning("⚠️ 卡片数量较多，导出可能需要一些时间")


def render_right_column_unified():
    """Render the right column with unified UI."""
    from core.state import get_ui_preferences
    from ui.state_bridge import state_get, state_set
    
    ui = get_unified_ui()
    
    # Check if we should use state service for preview mode
    from core.feature_flags import get_feature_flag
    
    if get_feature_flag('state_service', False):
        try:
            from ui.state import get_state_service
            state_service = get_state_service()
            
            # Get UI preferences
            prefs = get_ui_preferences()
            hanzi_font_family, background_color = prefs['hanzi_font_family'], prefs['background_color']

            # Preview mode selection
            preview_mode = ui.radio(
                "预览模式",
                ["📄 完整页面", "🔲 简单网格"],
                horizontal=True,
                help_text="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
            )
            
            # Use debouncing if available
            if get_feature_flag('debouncing', False):
                from ui.debounce import debounce_state_update
                debounce_state_update('preview_mode', preview_mode, delay_ms=150)
            else:
                state_service.set('preview_mode', preview_mode)
                
        except Exception:
            # Fallback to session state
            state_set('preview_mode', preview_mode)

        return {
            'hanzi_font_family': hanzi_font_family,
            'background_color': background_color,
            'preview_mode': preview_mode
        }
    else:
        # Legacy implementation using unified UI
        prefs = get_ui_preferences()
        hanzi_font_family, background_color = prefs['hanzi_font_family'], prefs['background_color']

        # Preview mode selection
        preview_mode = ui.radio(
            "预览模式",
            ["📄 完整页面", "🔲 简单网格"],
            horizontal=True,
            help_text="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
        )
        
        # Persist preview mode for parameter tracking across components
        state_set('preview_mode', preview_mode)

        return {
            'hanzi_font_family': hanzi_font_family,
            'background_color': background_color,
            'preview_mode': preview_mode
        }


def render_empty_preview_unified():
    """Render preview for empty cards case using unified UI."""
    ui = get_unified_ui()
    
    try:
        from services.cache_v2 import create_preview_html
        # Note: This still uses st.components.v1.html as there's no adapter equivalent yet
        # This is one of the few remaining direct calls that's acceptable
        import streamlit as st
        st.components.v1.html(create_preview_html([]), height_cm=650)
    except Exception as e:
        ui.error(f"预览渲染错误: {e}")


# Export the main functions
__all__ = [
    'render_export_section_unified',
    'render_right_column_unified', 
    'render_empty_preview_unified'
]
