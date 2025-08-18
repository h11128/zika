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
        font-size: {font_hanzi * scale_factor * 0.8}px;
        font-weight: bold;
        margin-bottom: {max(2, font_hanzi * 0.1) * scale_factor}px;
        color: #000;
        text-align: center;
        line-height: 1.1;
    }}
    .page-pinyin {{
        font-size: {font_pinyin * scale_factor * 0.8}px;
        font-style: italic;
        margin-bottom: {max(2, font_pinyin * 0.1) * scale_factor}px;
        color: #333;
        text-align: center;
        line-height: 1.2;
    }}
    .page-english {{
        font-size: {font_english * scale_factor * 0.8}px;
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
                           rows: int = 3, cols: int = 3) -> str:
    """Create simple HTML preview of cards in rows x cols grid with custom styling."""
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    simple_html = f"""
    <style>
    .simple-grid {{
        display: grid;
        grid-template-columns: repeat({cols}, 1fr);
        gap: 15px;
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }}
    .simple-card {{
        border: 2px solid #333;
        aspect-ratio: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        padding: 15px;
        background: {background_color};
        font-family: '{hanzi_font}', 'Microsoft YaHei', 'SimSun', sans-serif;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    .simple-card.empty {{
        border-style: dashed;
        opacity: 0.3;
    }}
    .simple-hanzi {{
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 8px;
        color: #000;
    }}
    .simple-pinyin {{
        font-size: 1.2em;
        font-style: italic;
        margin-bottom: 8px;
        color: #333;
    }}
    .simple-english {{
        font-size: 1em;
        text-align: center;
        color: #555;
        line-height: 1.3;
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


# Cached versions of the functions
@st.cache_data(show_spinner=False)
def cached_create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    return create_page_preview_html(cards, page_num, card_size, gap, margin,
                                   font_hanzi, font_pinyin, font_english,
                                   page_size, hanzi_font, background_color,
                                   rows, cols, auto_fill)


@st.cache_data(show_spinner=False)
def cached_create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR, rows: int = 3, cols: int = 3) -> str:
    return create_simple_grid_html(cards, hanzi_font, background_color, rows, cols)


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
