"""
Preview rendering module for the UI refactor.
Handles preview display, navigation, and mode selection.
"""

from typing import List, Dict, Any

from core.feature_flags import get_feature_flag
from services.cache_v2 import create_preview_html
from services.layout import paginate
from ui.error_boundaries import with_error_boundary
from ui.components import render_page_navigation, render_page_info, render_preview_section
from ui.ports import UIAdapter, get_ui_adapter, ComponentConfig, NotificationLevel
from ui.unified import get_unified_ui
from ui.state_bridge import state_get, state_set, state_delete


@with_error_boundary("preview_section_wrapper")
def render_preview_section_wrapper(processed_cards: List[Dict[str, str]],
                                 card_size_cm: float, gap_cm: float, margin_cm: float,
                                 hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                                 page_size: str, hanzi_font_family: str, background_color: str,
                                 layout_rows: int, layout_cols: int, layout_auto_fill: bool) -> None:
    """
    Render the complete preview section with mode selection and navigation.
    Migrated from ui/sections.py
    """
    # Check if new preview pipeline is enabled
    try:
        from core.feature_flags import use_new_preview_pipeline
        from services.preview_types import convert_legacy_params_to_preview_params
        from ui.preview_controller import get_preview_controller

        if use_new_preview_pipeline():
            # Convert legacy parameters to new format
            preview_params = convert_legacy_params_to_preview_params(
                card_size_cm=card_size, gap_cm=gap, margin_cm=margin, page_size=page_size,
                hanzi_font_size=hanzi_font_size, pinyin_font_size=pinyin_font_size, english_font_size=english_font_size,
                hanzi_font_family=hanzi_font_family, background_color=background_color,
                preview_mode=state_get('preview_mode', '📄 完整页面'),
                layout_rows=layout_rows, layout_cols=layout_cols, layout_auto_fill=auto_fill
            )

            # Create mock AppConfig for new pipeline
            from dataclasses import dataclass

            @dataclass
            class MockLayoutConfig:
                layout_rows: int
                layout_cols: int
                layout_auto_fill: bool
                card_size_cm: float
                gap_cm: float
                margin_cm: float
                page_size: str
                hanzi_font_size: int
                pinyin_font_size: int
                english_font_size: int

            @dataclass
            class MockUIConfig:
                hanzi_font_family: str
                background_color: str
                preview_mode: str

            @dataclass
            class MockAppConfig:
                layout: MockLayoutConfig
                ui: MockUIConfig

            mock_config = MockAppConfig(
                layout=MockLayoutConfig(
                    layout_rows=preview_params.layout.layout_rows,
                    layout_cols=preview_params.layout.layout_cols,
                    layout_auto_fill=preview_params.layout.layout_auto_fill,
                    card_size_cm=preview_params.layout.card_size_cm,
                    gap_cm=preview_params.layout.gap_cm,
                    margin_cm=preview_params.layout.margin_cm,
                    page_size=preview_params.layout.page_size,
                    hanzi_font_size=preview_params.typography.hanzi_font_size_pt,
                    pinyin_font_size=preview_params.typography.pinyin_font_size_pt,
                    english_font_size=preview_params.typography.english_font_size_pt,
                ),
                ui=MockUIConfig(
                    hanzi_font_family=preview_params.typography.hanzi_font_family,
                    background_color=preview_params.visual.background_color,
                    preview_mode=preview_params.visual.preview_mode,
                )
            )
            controller = get_preview_controller()
            controller.render_preview_content_v2(processed_cards, mock_config)
            return
    except ImportError:
        # Fall back to legacy implementation
        pass

    # Check if we should use adapter for UI elements
    from core.feature_flags import get_feature_flag

    if get_feature_flag('adapted_preview', False):
        from ui.ports import get_ui_adapter, ComponentConfig
        adapter = get_ui_adapter()

        adapter.header("👀 预览")

        # Preview mode selection using adapter
        preview_config = ComponentConfig(
            key="preview_mode_wrapper",
            label="预览模式",
            help_text="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
        )
        preview_mode = adapter.inputs.radio(
            preview_config,
            options=["📄 完整页面", "🔲 简单网格"],
            index=0,
            horizontal=True
        )
        # Persist preview mode in session for consistent param tracking
        state_set('preview_mode', preview_mode)
    else:
        ui = get_unified_ui()
        ui.header("👀 预览")

        # Preview mode selection
        preview_mode = ui.radio(
            "预览模式",
            ["📄 完整页面", "🔲 简单网格"],
            horizontal=True,
            help_text="完整页面：按实际打印布局预览；简单网格：快速查看卡片内容"
        )
        # Persist preview mode in session for consistent param tracking
        state_set('preview_mode', preview_mode)

    # Build effective params using session_state as the source of truth
    passed = {
        'card_size_cm': card_size,
        'gap_cm': gap,
        'margin_cm': margin,
        'hanzi_font_size': hanzi_font_size,
        'pinyin_font_size': pinyin_font_size,
        'english_font_size': english_font_size,
        'page_size': page_size,
        'hanzi_font_family': hanzi_font_family,
        'background_color': background_color,
        'layout_rows': layout_rows,
        'layout_cols': layout_cols,
        'layout_auto_fill': layout_auto_fill,
    }
    eff = _effective_preview_params_from_state(passed)
    card_size, gap, margin_cm = eff['card_size_cm'], eff['gap_cm'], eff['margin_cm']
    hanzi_font_size, pinyin_font_size, english_font_size = eff['hanzi_font_size'], eff['pinyin_font_size'], eff['english_font_size']
    page_size, hanzi_font_family, background_color = eff['page_size'], eff['hanzi_font_family'], eff['background_color']
    layout_rows, layout_cols, layout_auto_fill = eff['layout_rows'], eff['layout_cols'], eff['layout_auto_fill']

    if processed_cards:
        # Calculate total pages (rows x cols per page)
        cards_per_page = max(1, rows * cols)
        total_pages = max(1, (len(processed_cards) + cards_per_page - 1) // cards_per_page)

        # Use state values as source of truth for fonts to avoid accidental resets
        effective_font_hanzi = state_get('hanzi_font_size', hanzi_font_size)
        effective_font_pinyin = state_get('pinyin_font_size', pinyin_font_size)
        effective_font_english = state_get('english_font_size', english_font_size)

        # Check if parameters changed (reset to first page if they did)
        current_params = {
            'card_size_cm': card_size,
            'gap_cm': gap,
            'margin_cm': margin,
            'hanzi_font_size': effective_font_hanzi,
            'pinyin_font_size': effective_font_pinyin,
            'english_font_size': effective_font_english,
            'page_size': page_size,
            'hanzi_font_family': hanzi_font_family,
            'background_color': background_color,
            'layout_rows': layout_rows,
            'layout_cols': layout_cols,
            'layout_auto_fill': layout_auto_fill,
            'total_cards': len(processed_cards),
            # Include preview mode to ensure state resets and cache invalidation on mode change
            'preview_mode': preview_mode,
        }

        if state_get('last_params') != current_params:
            state_set('current_page', 0)
            state_set('last_params', current_params)
            # Clear export data when parameters change
            state_set('export_ready', {})
            state_set('export_data', {})

        # Reset current page if it's out of range
        if state_get('current_page', 0) >= total_pages:
            state_set('current_page', 0)

        # Page navigation
        render_page_navigation(total_pages)

        # 渲染预览（封装函数，缓存+占位符，降低其它UI重绘）
        render_preview_section(
            processed_cards, preview_mode,
            card_size, gap, margin,
            effective_font_hanzi, effective_font_pinyin, effective_font_english,
            page_size, hanzi_font_family, background_color,
            layout_rows, layout_cols, auto_fill
        )

        # Show card count and page info
        render_page_info(processed_cards, cards_per_page, total_pages)

        # Card editing section
        if len(processed_cards) > 0:
            # Use adapter for expander if available
            if get_feature_flag('adapted_preview', False):
                with adapter.layout.expander("✏️ 编辑卡片", expanded=False):
                    # Editor content will use legacy implementation for now
                    _render_card_editing_section(processed_cards)
            else:
                ui = get_unified_ui()
                with ui.expander("✏️ 编辑卡片", expanded=False):
                    _render_card_editing_section(processed_cards)
                # Use table editor if enabled, otherwise fall back to legacy


    else:
        # Show empty state using adapter if available
        if get_feature_flag('adapted_preview', False):
            from services.cache_v2 import create_preview_html
            adapter.preview.render_html(create_preview_html([]), height_cm=650)
        else:
            from services.cache_v2 import create_preview_html
            ui = get_unified_ui()
            ui.html(create_preview_html([]), height_cm=650)

    # Sticky wrapper is managed by ui.styles.sticky_preview() at a higher level.


def _render_card_editing_section(processed_cards: List[Dict[str, str]]) -> None:
    """Render the card editing section."""
    # Use table editor if enabled, otherwise fall back to legacy
    try:
        from ui.table_editor import use_table_editor, render_table_editor, TableEditorConfig
        from services.card_models import CardCollection, use_stable_card_ids

        if use_table_editor() and use_stable_card_ids():
            # Convert to CardCollection and use table editor
            collection = CardCollection.from_legacy_format(processed_cards)
            config = TableEditorConfig(
                page_size=10,
                show_search=True,
                show_pagination=True,
                editable=True
            )
            updated_collection, needs_refresh = render_table_editor(collection, config)

            # Update processed_cards if changes were made
            if needs_refresh:
                state_set('processed_cards', updated_collection.to_legacy_format())
                ui = get_unified_ui()
                ui.rerun()
        else:
            # Fall back to legacy editor
            from ui.editor import render_improved_card_editor
            render_improved_card_editor(processed_cards)
    except ImportError:
        # Fall back if table editor not available
        from ui.editor import render_improved_card_editor
        render_improved_card_editor(processed_cards)


def _effective_preview_params_from_state(passed: Dict[str, Any]) -> Dict[str, Any]:
    """Get effective preview parameters from session state."""
    # Use session state as source of truth, fall back to passed values
    return {
        'card_size_cm': state_get('card_size_cm', passed['card_size_cm']),
        'gap_cm': state_get('gap_cm', passed['gap_cm']),
        'margin_cm': state_get('margin_cm', passed['margin_cm']),
        'hanzi_font_size': state_get('hanzi_font_size', passed['hanzi_font_size']),
        'pinyin_font_size': state_get('pinyin_font_size', passed['pinyin_font_size']),
        'english_font_size': state_get('english_font_size', passed['english_font_size']),
        'page_size': state_get('page_size', passed['page_size']),
        'hanzi_font_family': state_get('hanzi_font_family', passed['hanzi_font_family']),
        'background_color': state_get('background_color', passed['background_color']),
        'layout_rows': state_get('layout_rows', passed['layout_rows']),
        'layout_cols': state_get('layout_cols', passed['layout_cols']),
        'layout_auto_fill': state_get('layout_auto_fill', passed['layout_auto_fill']),
    }


def render_preview_content_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]],
                                 config: Dict[str, Any]) -> None:
    """Render preview content using UI adapter."""
    adapter.header("👀 预览")

    if not processed_cards:
        adapter.notifications.show_message(
            "请先输入文本以生成预览", NotificationLevel.INFO
        )
        adapter.markdown('</div>', unsafe_allow_html=True)
        return

    # Preview mode selection
    mode_config = ComponentConfig(
        key="preview_mode_adapted",
        label="预览模式",
        help_text="选择预览显示模式"
    )
    preview_mode = adapter.inputs.radio(
        mode_config, 
        options=["📄 完整页面", "🔲 简单网格"], 
        index=0, 
        horizontal=True
    )

    # Calculate pagination
    layout_rows = config.get('layout_rows', 2)
    layout_cols = config.get('layout_cols', 3)
    pagination_info = paginate(len(processed_cards), layout_rows, cols)
    cards_per_page = pagination_info.cards_per_page
    total_pages = pagination_info.total_pages

    # Page navigation
    render_page_navigation_adapted(adapter, total_pages)

    # Render preview content
    render_preview_content_html_adapted(adapter, processed_cards, config, preview_mode)

    # Show page info
    render_page_info_adapted(adapter, processed_cards, cards_per_page, total_pages)

    # sticky wrapper is provided by outer context


def render_page_navigation_adapted(adapter: UIAdapter, total_pages: int) -> None:
    """Render page navigation using UI adapter."""
    if total_pages <= 1:
        return

    col1, col2, col3, col4, col5 = adapter.layout.columns([1, 1, 2, 1, 1])

    # Get current page from session state (simplified)
    current_page = 0  # In real implementation, this would come from state

    with col1:
        first_config = ComponentConfig(
            key="first_page_adapted",
            label="⏮️ 首页",
            disabled=current_page <= 0
        )
        if adapter.inputs.button(first_config):
            # Update current page to 0
            pass

    with col2:
        prev_config = ComponentConfig(
            key="prev_page_adapted",
            label="◀️ 上页",
            disabled=current_page <= 0
        )
        if adapter.inputs.button(prev_config):
            # Update current page
            pass

    with col3:
        adapter.markdown(f"**第 {current_page + 1} 页，共 {total_pages} 页**")

    with col4:
        next_config = ComponentConfig(
            key="next_page_adapted",
            label="▶️ 下页",
            disabled=current_page >= total_pages - 1
        )
        if adapter.inputs.button(next_config):
            # Update current page
            pass

    with col5:
        last_config = ComponentConfig(
            key="last_page_adapted",
            label="⏭️ 末页",
            disabled=current_page >= total_pages - 1
        )
        if adapter.inputs.button(last_config):
            # Update current page to last
            pass


def render_preview_content_html_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]],
                                      config: Dict[str, Any], preview_mode: str) -> None:
    """Render HTML preview content using UI adapter with shared render core."""
    try:
        # Try to use shared render core if available
        from core.feature_flags import get_feature_flag

        if get_feature_flag('shared_render_core', True):
            try:
                from services.render_core import render_cards_unified, create_render_options_from_legacy

                # Create render options from config
                render_options = create_render_options_from_legacy(
                    card_size_cm=config.get('card_size_cm', 5.5),
                    gap_cm=config.get('gap_cm', 0.5),
                    margin_cm=config.get('margin_cm', 1.0),
                    hanzi_font_size=config.get('hanzi_font_size', 48),
                    pinyin_font_size=config.get('pinyin_font_size', 18),
                    english_font_size=config.get('english_font_size', 14),
                    page_size=config.get('page_size', 'A4'),
                    hanzi_font_family=config.get('hanzi_font_family', 'SimHei'),
                    background_color=config.get('background_color', '#ffffff'),
                    layout_rows=config.get('layout_rows', 2),
                    layout_cols=config.get('layout_cols', 3),
                    layout_auto_fill=config.get('layout_auto_fill', True)
                )

                # Use unified rendering
                result = render_cards_unified(processed_cards, render_options, output_format='html')

                if result.success:
                    # Determine height based on preview mode (pixels)
                    height = 850 if preview_mode == '📄 完整页面' else 650

                    # Render HTML component
                    adapter.preview.html_component(result.content, height_cm=height)
                    return
                else:
                    # Fall back to legacy implementation
                    adapter.notifications.show_message(
                        f"共享渲染核心失败，使用传统方式: {result.error_message}",
                        NotificationLevel.WARNING
                    )
            except Exception as e:
                # Fall back to legacy implementation
                adapter.notifications.show_message(
                    f"共享渲染核心不可用，使用传统方式: {str(e)}",
                    NotificationLevel.WARNING
                )

        # Legacy implementation fallback
        html_content = create_preview_html(
            processed_cards,
            card_size_cm=config.get('card_size_cm', 5.5),
            gap_cm=config.get('gap_cm', 0.5),
            margin_cm=config.get('margin_cm', 1.0),
            hanzi_font_size=config.get('hanzi_font_size', 48),
            pinyin_font_size=config.get('pinyin_font_size', 18),
            english_font_size=config.get('english_font_size', 14),
            page_size=config.get('page_size', 'A4'),
            hanzi_font_family=config.get('hanzi_font_family', 'SimHei'),
            background_color=config.get('background_color', '#ffffff'),
            layout_rows=config.get('layout_rows', 2),
            layout_cols=config.get('layout_cols', 3),
            layout_auto_fill=config.get('layout_auto_fill', True)
        )

        # Determine height based on preview mode (pixels)
        height = 850 if preview_mode == '📄 完整页面' else 650

        # Render HTML component
        adapter.preview.html_component(html_content, height_cm=height)

    except Exception as e:
        adapter.notifications.show_message(
            f"预览生成失败: {str(e)}", NotificationLevel.ERROR
        )


def render_page_info_adapted(adapter: UIAdapter, processed_cards: List[Dict[str, str]],
                           cards_per_page: int, total_pages: int) -> None:
    """Render page information using UI adapter."""
    current_page = 0  # In real implementation, this would come from state
    
    start_card = current_page * cards_per_page + 1
    end_card = min((current_page + 1) * cards_per_page, len(processed_cards))
    
    info_text = f"**显示卡片 {start_card}-{end_card}，共 {len(processed_cards)} 张**"
    adapter.markdown(info_text)


def render_empty_preview_state(adapter: UIAdapter) -> None:
    """Render empty preview state using UI adapter."""
    try:
        empty_html = create_preview_html([])
        adapter.preview.html_component(empty_html, height_cm=650)
    except Exception:
        adapter.notifications.show_message(
            "无预览内容", NotificationLevel.INFO
        )


def use_adapted_preview() -> bool:
    """Check if adapted preview should be used."""
    return True


def render_preview_unified(processed_cards: List[Dict[str, str]], 
                         config: Dict[str, Any]) -> None:
    """
    Unified preview rendering that chooses between legacy and adapted versions.
    """
    if use_adapted_preview():
        adapter = get_ui_adapter()
        render_preview_content_adapted(adapter, processed_cards, config)
    else:
        # Extract parameters for legacy function
        render_preview_section_wrapper(
            processed_cards,
            card_size_cm=config.get('card_size_cm', 5.5),
            gap_cm=config.get('gap_cm', 0.5),
            margin_cm=config.get('margin_cm', 1.0),
            hanzi_font_size=config.get('hanzi_font_size', 48),
            pinyin_font_size=config.get('pinyin_font_size', 18),
            english_font_size=config.get('english_font_size', 14),
            page_size=config.get('page_size', 'A4'),
            hanzi_font_family=config.get('hanzi_font_family', 'SimHei'),
            background_color=config.get('background_color', '#ffffff'),
            layout_rows=config.get('layout_rows', 2),
            layout_cols=config.get('layout_cols', 3),
            layout_auto_fill=config.get('layout_auto_fill', True)
        )


# Export the main functions
__all__ = [
    'render_preview_section_wrapper',
    'render_preview_content_adapted',
    'render_preview_unified',
    'use_adapted_preview'
]
