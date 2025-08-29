"""
Cache service for the Chinese Character Learning Cards application.
Centralized location for all cached functions and their implementations.
"""

import streamlit as st
from typing import List, Dict
from core.constants import DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR


def create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
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

    # Convert point (pt) sizes to CSS pixels and scale with page scale_factor so
    # that preview matches PDF/PPT (which use point sizes)
    PT_TO_PX = 96 / 72  # 1pt = 1/72in; CSS px at 96 DPI → 96/72 px per pt

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
        font-size: {font_hanzi * PT_TO_PX * scale_factor}px;
        font-weight: bold;
        margin-bottom: {max(2, font_hanzi * 0.1) * scale_factor}px;
        color: #000;
        text-align: center;
        line-height: 1.1;
    }}
    .page-pinyin {{
        font-size: {font_pinyin * PT_TO_PX * scale_factor}px;
        font-style: italic;
        margin-bottom: {max(2, font_pinyin * 0.1) * scale_factor}px;
        color: #333;
        text-align: center;
        line-height: 1.2;
    }}
    .page-english {{
        font-size: {font_english * PT_TO_PX * scale_factor}px;
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


def create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3,
                           font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14,
                           card_size: float = 5.5, auto_fill: bool = True) -> str:
    """Create simple HTML preview of cards in rows x cols grid with custom styling.
    Respects font sizes and card size when provided to keep behavior consistent with full-page preview.
    """
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    # Calculate card size in pixels (similar to full page preview)
    # Use pt→px conversion so fonts align with export sizing
    PT_TO_PX = 96 / 72

    if auto_fill:
        # For simple grid, use responsive sizing
        card_size_px = "auto"
        card_width = "1fr"
    else:
        # Convert cm to pixels for manual sizing
        mm_to_px = 3.78  # 96 DPI conversion factor
        card_size_px = card_size * 10 * mm_to_px  # cm to mm to px
        card_width = f"{card_size_px}px"

    # Calculate responsive grid layout
    mm_to_px = 3.78
    card_size_px_calc = card_size * 10 * mm_to_px
    gap_px = 15
    theoretical_width = cols * card_size_px_calc + (cols - 1) * gap_px

    if auto_fill:
        # Auto-fill mode: use responsive columns that fit the container
        grid_columns = f"repeat(auto-fit, minmax(150px, 1fr))"
        container_max_width = "100%"
        card_width_css = "100%"  # Cards fill their grid cells
        card_height_css = "auto"
        card_size_css = card_size_px_calc  # Keep original size for aspect ratio
    elif theoretical_width > 900:
        # Use responsive design when content would overflow
        min_card_size = max(120, card_size_px_calc * 0.7)  # Minimum readable size
        grid_columns = f"repeat(auto-fit, minmax({min_card_size}px, 1fr))"
        container_max_width = "100%"
        card_width_css = "100%"  # Cards fill their grid cells
        card_height_css = "auto"
        card_size_css = min_card_size  # Use minimum size for responsive cards
    else:
        # Use fixed layout when it fits
        grid_columns = f"repeat({cols}, {card_width})"
        container_max_width = "900px"
        card_width_css = card_width
        card_height_css = card_width
        card_size_css = card_size_px_calc

    simple_html = f"""
    <style>
    .simple-grid {{
        display: grid;
        grid-template-columns: {grid_columns};
        gap: 15px;
        max-width: {container_max_width};
        margin: 0 auto;
        padding: 20px;
        justify-content: center;
        overflow: hidden;
    }}
    .simple-card {{
        border: 2px solid #333;
        {f"width: {card_width_css}; height: {card_height_css}; aspect-ratio: 1;" if card_width_css == "100%" else f"width: {card_size_px}px; height: {card_size_px}px;"}
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: {max(10, card_size_css * 0.1)}px;
        background: {background_color};
        font-family: '{hanzi_font}', 'Microsoft YaHei', 'SimSun', sans-serif;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        box-sizing: border-box;
        min-height: 120px;
        max-width: 100%;
    }}
    .simple-card.empty {{
        border-style: dashed;
        opacity: 0.3;
    }}
    .simple-hanzi {{
        font-size: {font_hanzi * PT_TO_PX}px;
        font-weight: bold;
        margin-bottom: max(6px, {font_hanzi * 0.2}px);
        color: #000;
        line-height: 1.1;
        text-align: center;
    }}
    .simple-pinyin {{
        font-size: {font_pinyin * PT_TO_PX}px;
        font-style: italic;
        margin-bottom: max(4px, {font_pinyin * 0.2}px);
        color: #333;
        line-height: 1.2;
        text-align: center;
    }}
    .simple-english {{
        font-size: {font_english * PT_TO_PX}px;
        text-align: center;
        color: #555;
        line-height: 1.2;
        word-wrap: break-word;
        overflow-wrap: break-word;
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


# Cached versions of the functions with hash-based cache keys
@st.cache_data(show_spinner=False)
def cached_create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    """Cached version of create_page_preview_html with proper parameter tracking."""
    return create_page_preview_html(cards, page_num, card_size, gap, margin,
                                   font_hanzi, font_pinyin, font_english,
                                   page_size, hanzi_font, background_color,
                                   rows, cols, auto_fill)


@st.cache_data(show_spinner=False)
def cached_create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR, rows: int = 3, cols: int = 3,
                           font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14,
                           card_size: float = 5.5, auto_fill: bool = True) -> str:
    """Cached version of create_simple_grid_html with proper parameter tracking."""
    return create_simple_grid_html(cards, hanzi_font, background_color, rows, cols,
                                   font_hanzi, font_pinyin, font_english, card_size, auto_fill)


# Non-cached versions for immediate updates when needed
def create_page_preview_html_immediate(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    """Non-cached version for immediate preview updates."""
    return create_page_preview_html(cards, page_num, card_size, gap, margin,
                                   font_hanzi, font_pinyin, font_english,
                                   page_size, hanzi_font, background_color,
                                   rows, cols, auto_fill)


def create_simple_grid_html_immediate(cards: List[Dict[str, str]], hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR, rows: int = 3, cols: int = 3,
                           font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14,
                           card_size: float = 5.5, auto_fill: bool = True) -> str:
    """Non-cached version for immediate preview updates."""
    return create_simple_grid_html(cards, hanzi_font, background_color, rows, cols,
                                   font_hanzi, font_pinyin, font_english, card_size, auto_fill)


def clear_preview_cache() -> None:
    """Clear all preview-related caches to force regeneration."""
    try:
        cached_create_page_preview_html.clear()
        cached_create_simple_grid_html.clear()
    except Exception:
        # Cache clearing might fail if functions haven't been called yet
        pass


def create_preview_html(cards: List[Dict[str, str]], max_cards: int = 9) -> str:
    """Create simple HTML preview of cards in 3x3 grid (legacy function)."""
    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    # Use the new page preview function for first page with defaults
    from core.constants import (
        DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN, DEFAULT_FONT_HANZI,
        DEFAULT_FONT_PINYIN, DEFAULT_FONT_ENGLISH, DEFAULT_PAGE_SIZE,
        DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL
    )
    return cached_create_page_preview_html(cards, 0, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN,
                                         DEFAULT_FONT_HANZI, DEFAULT_FONT_PINYIN, DEFAULT_FONT_ENGLISH,
                                         DEFAULT_PAGE_SIZE, DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR,
                                         DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL)
