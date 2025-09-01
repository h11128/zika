"""
Application Controller for Chinese Character Learning Cards Web UI.
Handles all business logic and application flow control.
"""

import streamlit as st
from typing import List, Dict, Tuple

# Import required modules
from services.processing import generate_missing_data, generate_missing_data_ordered
from core.state import (
    initialize_session_state, get_processed_cards, get_current_page, get_layout_settings,
    get_ui_preferences, set_processed_cards, set_current_page, clear_export_data,
    clear_processed_cards, get_dictionary, get_all_ui_params, handle_param_changes
)
from ui.components import render_page_navigation, render_preview_section, render_page_info
# Use unified sections if available
from core.feature_flags import get_feature_flag
from ui.ports import get_ui_adapter

if get_feature_flag('unified_sections', True):
    from ui.sections_unified import (
        render_sidebar, render_export_section, render_left_column,
        render_preview_column_header
    )
    # These functions are not in unified yet, keep from original
    from ui.sections import render_preview_content_legacy, render_improved_card_editor
else:
    from ui.sections import (
        render_sidebar, render_export_section, render_left_column,
        render_preview_column_header, render_preview_content_legacy,
        render_improved_card_editor
    )
from core.config import AppConfig, create_config_from_params
from ui.styles import apply_global_styles, render_sticky_wrapper_start, render_sticky_wrapper_end


class AppController:
    """Main application controller that handles all business logic and flow."""
    
    def __init__(self):
        """Initialize the application controller."""
        self.setup_app()
    
    def setup_app(self):
        """Initialize application setup."""
        apply_global_styles()
        initialize_session_state()
    
    def render_header(self):
        """Render application header."""
        adapter = get_ui_adapter()
        adapter.header("🀄 Chinese Learning Cards Generator", level=1)
        adapter.markdown("输入汉字，自动生成拼音和翻译，制作学习卡片")
        adapter.markdown("💡 **新功能**: 支持空格分隔输入和智能自动分词")
    

    
    def should_reprocess_cards(self, cards, current_source):
        """Check if cards need reprocessing with error handling."""
        try:
            processed_cards = get_processed_cards()
            if not hasattr(st.session_state, 'cards_source'):
                st.session_state.cards_source = None

            return (
                st.session_state.cards_source != current_source or
                len(processed_cards) != len(cards) or
                not processed_cards
            )
        except Exception as e:
            adapter = get_ui_adapter()
            adapter.notifications.show_error(f"检查卡片状态时出错: {e}")
            return True  # Force reprocessing on error
    
    def process_cards_if_needed(self, cards, auto_pinyin, auto_translate, translate_order: str = 'local_first'):
        """Process cards and generate missing data if needed with error handling."""
        try:
            # Input validation
            if not isinstance(cards, list):
                cards = []

            if not cards:
                if get_processed_cards():
                    clear_processed_cards()
                return []

            current_source = f"cards:{len(cards)}:{hash(str(cards))}:{translate_order}"

            if self.should_reprocess_cards(cards, current_source):
                clear_export_data()
                try:
                    # Use ordered variant only if non-default to preserve backwards compat
                    if translate_order and translate_order != 'local_first':
                        processed_cards = generate_missing_data_ordered(cards, auto_pinyin, auto_translate, get_dictionary(), translate_order)
                    else:
                        processed_cards = generate_missing_data(cards, auto_pinyin, auto_translate, get_dictionary())
                    set_processed_cards(processed_cards, current_source)
                    return processed_cards
                except Exception as e:
                    adapter = get_ui_adapter()
                    adapter.notifications.show_error(f"生成卡片数据时出错: {e}")
                    # Return basic cards without generated data
                    basic_cards = [{'hanzi': card.get('hanzi', ''), 'pinyin': card.get('pinyin', ''), 'english': card.get('english', '')} for card in cards]
                    return basic_cards

            return get_processed_cards()
        except Exception as e:
            adapter = get_ui_adapter()
            adapter.notifications.show_error(f"处理卡片时出错: {e}")
            return []
    

    
    def calculate_pagination(self, processed_cards, layout):
        """Calculate pagination information."""
        from services.layout import paginate, PaginateInfo

        # Use the standardized paginate function
        pagination_info = paginate(
            len(processed_cards),
            layout['layout_rows'],
            layout['layout_cols']
        )

        # Reset current page if out of range
        current_page = get_current_page()
        if current_page >= pagination_info.total_pages:
            set_current_page(0)

        return pagination_info
    
    def render_card_editor(self, processed_cards, cards_per_page):
        """Render card editing section."""
        if not processed_cards:
            return
            
        adapter = get_ui_adapter()
        with adapter.layout.expander("✏️ 编辑卡片", expanded=False):
            # Use the improved editor supporting pagination/search
            render_improved_card_editor(processed_cards)
    

    
    def render_right_column_content(self, left_params):
        """Render the right column with preview and editing using high-level functions."""
        from ui.styles import sticky_preview

        with sticky_preview():
            # Get preview parameters
            preview_params = render_preview_column_header()

            # Process cards
            processed_cards = self.process_cards_if_needed(
                left_params['cards'], left_params['auto_pinyin'], left_params['auto_translate'], left_params.get('translate_order', 'local_first')
            )

            if processed_cards:
                # Handle parameter changes
                try:
                    current_params = get_all_ui_params(
                        left_params['card_size_cm'], left_params['gap_cm'], left_params['margin_cm'],
                        left_params['page_size'], left_params['hanzi_font_size'], left_params['pinyin_font_size'],
                        left_params['english_font_size'], processed_cards,
                        preview_params.get('preview_mode') if isinstance(preview_params, dict) else None
                    )
                    handle_param_changes(current_params)
                except Exception as e:
                    adapter = get_ui_adapter()
                    adapter.notifications.show_error(f"参数处理错误: {e}")

                # Use SINGLE unified preview entry point
                try:
                    from ui.preview_controller import render_preview_content_unified
                    from services.preview_types import AppConfig

                    # Build unified config - SINGLE configuration format
                    config = AppConfig(
                        card_size_cm=left_params.get('card_size_cm', 5.5),
                        gap_cm=left_params.get('gap_cm', 0.5),
                        margin_cm=left_params.get('margin_cm', 1.0),
                        page_size=left_params.get('page_size', 'A4'),
                        hanzi_font_size=left_params.get('hanzi_font_size', 48),
                        pinyin_font_size=left_params.get('pinyin_font_size', 18),
                        english_font_size=left_params.get('english_font_size', 14),
                        hanzi_font_family=preview_params.get('hanzi_font_family', 'SimHei'),
                        background_color=preview_params.get('background_color', '#ffffff'),
                        layout_rows=left_params.get('layout_rows', 2),
                        layout_cols=left_params.get('layout_cols', 3),
                        layout_auto_fill=left_params.get('layout_auto_fill', True)
                    )

                    # SINGLE entry point for ALL preview rendering
                    cards_per_page, total_pages = render_preview_content_unified(processed_cards, config)

                except ImportError:
                    # Emergency fallback only
                    from ui.sections import render_preview_content_legacy
                    cards_per_page, total_pages = render_preview_content_legacy(processed_cards, preview_params, left_params)

                # Render card editor
                self.render_card_editor(processed_cards, cards_per_page)
            else:
                # Render empty preview
                try:
                    from ui.preview import render_preview_unified
                    from core.feature_flags import use_new_preview_pipeline

                    if use_new_preview_pipeline():
                        config = {
                            'card_size_cm': left_params.get('card_size_cm', 5.5),
                            'gap_cm': left_params.get('gap_cm', 0.5),
                            'margin_cm': left_params.get('margin_cm', 1.0),
                            'hanzi_font_size': left_params.get('hanzi_font_size', 48),
                            'pinyin_font_size': left_params.get('pinyin_font_size', 18),
                            'english_font_size': left_params.get('english_font_size', 14),
                            'page_size': left_params.get('page_size', 'A4'),
                            'hanzi_font_family': left_params.get('hanzi_font_family', 'SimHei'),
                            'background_color': left_params.get('background_color', '#ffffff'),
                            'layout_rows': left_params.get('layout_rows', 2),
                            'layout_cols': left_params.get('layout_cols', 3),
                            'layout_auto_fill': left_params.get('layout_auto_fill', True)
                        }
                        render_preview_unified([], config)
                    else:
                        render_preview_content_legacy([], preview_params, left_params)
                except ImportError:
                    render_preview_content_legacy([], preview_params, left_params)

    def run_main_flow(self):
        """Execute the main application flow using high-level rendering functions with error handling."""
        try:
            # Render sidebar and header
            render_sidebar()
            self.render_header()

            # Create two columns
            adapter = get_ui_adapter()
            col1, col2 = adapter.layout.columns([1, 1])

            with col1:
                try:
                    left_params = render_left_column()
                except Exception as e:
                    adapter = get_ui_adapter()
                    adapter.notifications.show_error(f"左侧面板渲染错误: {e}")
                    left_params = {
                        'cards': [], 'auto_pinyin': True, 'auto_translate': True,
                        'page_size': 'A4', 'card_size_cm': 5.5, 'gap_cm': 0.5, 'margin_cm': 1.0,
                        'hanzi_font_size': 48, 'pinyin_font_size': 18, 'english_font_size': 14
                    }

            with col2:
                try:
                    self.render_right_column_content(left_params)
                except Exception as e:
                    adapter = get_ui_adapter()
                    adapter.notifications.show_error(f"右侧面板渲染错误: {e}")
                    adapter.notifications.show_message("请刷新页面重试")

            # Export section
            try:
                render_export_section(get_processed_cards())
            except Exception as e:
                adapter = get_ui_adapter()
                adapter.notifications.show_error(f"导出区域渲染错误: {e}")

        except Exception as e:
            adapter = get_ui_adapter()
            adapter.notifications.show_error(f"应用运行时发生严重错误: {e}")
            adapter.notifications.show_message("请刷新页面重新开始")
