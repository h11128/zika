"""
Cache service for the Chinese Character Learning Cards application.
Centralized location for all cached functions and their implementations.
"""

import streamlit as st
from typing import List, Dict, Tuple
from core.constants import (
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR,
    MM_TO_PX, CM_TO_MM, PT_TO_PX,
    PAGE_SIZE_MM, DEFAULT_PAGE_SIZE_KEY, FALLBACK_PAGE_SIZE_KEY,
    PREVIEW_MAX_WIDTH_PX, PREVIEW_MAX_HEIGHT_PX,
    SIMPLE_GRID_GAP_PX, SIMPLE_MIN_CARD_SIZE_PX, AUTO_FILL_MIN_FACTOR, MANUAL_SIZE_MIN_FACTOR,
    CSS_CONTAINER_MAX_WIDTH,
    PAGE_MARGIN_RATIO, PAGE_MARGIN_MIN_PX, SIMPLE_MARGIN_RATIO,
    SIMPLE_MARGIN_MIN_HANZI_PX, SIMPLE_MARGIN_MIN_PINYIN_PX,
    PAGE_PADDING_RATIO, PAGE_PADDING_MIN_PX, SIMPLE_PADDING_RATIO, SIMPLE_PADDING_MIN_PX,
)


from dataclasses import dataclass

# --- Data models ---

@dataclass
class PageLayoutMetrics:
    page_width_px: float
    page_height_px: float
    gap_px: float
    margin_px: float
    card_size_px: float
    grid_width: float
    grid_height: float
    start_x: float
    start_y: float
    scale_factor: float


@dataclass
class FontMetrics:
    hanzi_px: float
    pinyin_px: float
    english_px: float
    hanzi_margin_px: float
    pinyin_margin_px: float

@dataclass
class PageTemplateContext:
    page_num: int
    rows: int
    cols: int
    hanzi_font: str
    background_color: str

@dataclass
class SimpleGridTemplateContext:
    rows: int
    cols: int
    hanzi_font: str
    background_color: str



@dataclass
class CardBox:
    padding_px: float


@dataclass
class SimpleGridCSSParams:
    grid_columns: str
    container_max_width: str
    gap_px: int
    min_card_size: int
    card_size_px_calc: int

# --- Layout helpers (extracted) ---

def _compute_page_layout_metrics(page_size: str, gap_cm: float, margin_cm: float,
                                 rows: int, cols: int, card_size_cm: float,
                                 auto_fill: bool) -> PageLayoutMetrics:
    """Compute pixel-based layout metrics for full-page preview.
    Returns dict with: page_width_px, page_height_px, gap_px, margin_px,
    card_size_px, grid_width, grid_height, start_x, start_y, scale_factor.
    """
    # Page size
    page_width_mm, page_height_mm = PAGE_SIZE_MM.get(page_size, PAGE_SIZE_MM[FALLBACK_PAGE_SIZE_KEY])
    # Units
    page_width_px = page_width_mm * MM_TO_PX
    page_height_px = page_height_mm * MM_TO_PX
    gap_px = gap_cm * CM_TO_MM * MM_TO_PX
    margin_px = margin_cm * CM_TO_MM * MM_TO_PX
    # Available area
    avail_w = max(0, page_width_px - 2 * margin_px)
    avail_h = max(0, page_height_px - 2 * margin_px)
    # Card size
    if auto_fill:
        size_w = (avail_w - max(0, cols - 1) * gap_px) / max(1, cols)
        size_h = (avail_h - max(0, rows - 1) * gap_px) / max(1, rows)
        card_size_px = max(0, min(size_w, size_h))
    else:
        card_size_px = card_size_cm * CM_TO_MM * MM_TO_PX
    # Grid
    grid_width = cols * card_size_px + max(0, cols - 1) * gap_px
    grid_height = rows * card_size_px + max(0, rows - 1) * gap_px
    # Center inside margins
    start_x = margin_px + max(0, (avail_w - grid_width) / 2)
    start_y = margin_px + max(0, (avail_h - grid_height) / 2)
    # Preview scale
    scale_factor = min(PREVIEW_MAX_WIDTH_PX / page_width_px, PREVIEW_MAX_HEIGHT_PX / page_height_px, 1.0)
    return PageLayoutMetrics(
        page_width_px=page_width_px,
        page_height_px=page_height_px,
        gap_px=gap_px,
        margin_px=margin_px,
        card_size_px=card_size_px,
        grid_width=grid_width,
        grid_height=grid_height,
        start_x=start_x,
        start_y=start_y,
        scale_factor=scale_factor,
    )


def _compute_simple_grid_css(cols: int, card_size_cm: float, auto_fill: bool) -> SimpleGridCSSParams:
    """Return responsive CSS params for simple grid (no fixed 900px branch)."""
    # Base sizes
    card_size_px_calc = card_size_cm * CM_TO_MM * MM_TO_PX
    gap_px = SIMPLE_GRID_GAP_PX

    # Always responsive to container width
    # Use auto-fit with a reasonable min size; if manual size is provided, honor it as min
    min_card_size = max(SIMPLE_MIN_CARD_SIZE_PX, int(card_size_px_calc * (MANUAL_SIZE_MIN_FACTOR if not auto_fill else AUTO_FILL_MIN_FACTOR)))

    grid_columns = f"repeat(auto-fit, minmax({min_card_size}px, 1fr))"
    container_max_width = CSS_CONTAINER_MAX_WIDTH

    return SimpleGridCSSParams(
        grid_columns=grid_columns,
        container_max_width=container_max_width,
        gap_px=gap_px,
        min_card_size=min_card_size,
        card_size_px_calc=int(card_size_px_calc),
    )



def _slice_cards_for_page(cards: List[Dict[str, str]], page_num: int, rows: int, cols: int) -> Tuple[int, List[Dict[str, str]]]:
    """Return (cards_per_page, page_cards) for the given page."""
    cards_per_page = max(1, rows * cols)
    start_idx = page_num * cards_per_page
    end_idx = min(start_idx + cards_per_page, len(cards))
    return cards_per_page, cards[start_idx:end_idx]


def _compute_font_px(font_hanzi: int, font_pinyin: int, font_english: int, scale: float = 1.0) -> FontMetrics:
    """Convert pt to px with optional scale, also compute default margins used in page preview."""
    return FontMetrics(
        hanzi_px=font_hanzi * PT_TO_PX * scale,
        pinyin_px=font_pinyin * PT_TO_PX * scale,
        english_px=font_english * PT_TO_PX * scale,
        hanzi_margin_px=max(PAGE_MARGIN_MIN_PX, font_hanzi * PAGE_MARGIN_RATIO) * scale,
        pinyin_margin_px=max(PAGE_MARGIN_MIN_PX, font_pinyin * PAGE_MARGIN_RATIO) * scale,
    )


def _compute_simple_grid_font_px(font_hanzi: int, font_pinyin: int, font_english: int) -> FontMetrics:
    """Font sizes for simple grid (no page scale); margins per existing UI design."""
    return FontMetrics(
        hanzi_px=font_hanzi * PT_TO_PX,
        pinyin_px=font_pinyin * PT_TO_PX,
        english_px=font_english * PT_TO_PX,
        hanzi_margin_px=max(SIMPLE_MARGIN_MIN_HANZI_PX, font_hanzi * SIMPLE_MARGIN_RATIO),
        pinyin_margin_px=max(SIMPLE_MARGIN_MIN_PINYIN_PX, font_pinyin * SIMPLE_MARGIN_RATIO),
    )


def _compute_page_card_box(M: PageLayoutMetrics) -> CardBox:
    """Compute padding, etc. for page preview card box based on card size and scale."""
    return CardBox(padding_px=max(PAGE_PADDING_MIN_PX, M.card_size_px * PAGE_PADDING_RATIO) * M.scale_factor)


def _compute_simple_card_box(card_size_baseline_px: float) -> CardBox:
    """Compute padding for simple grid card from baseline pixel size."""
    return CardBox(padding_px=max(SIMPLE_PADDING_MIN_PX, card_size_baseline_px * SIMPLE_PADDING_RATIO))

def create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                           card_size: float, gap: float, margin: float,
                           font_hanzi: int, font_pinyin: int, font_english: int,
                           page_size: str = "A4", hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3, auto_fill: bool = True) -> str:
    """Create HTML preview of a specific page with realistic layout (template only)."""
    # Safety guards
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    # Compute inputs via helpers
    cards_per_page, page_cards = _slice_cards_for_page(cards, page_num, rows, cols)
    if not page_cards and page_num > 0:
        return "<div style='text-align: center; color: #666; padding: 50px;'>页面不存在</div>"

    M = _compute_page_layout_metrics(page_size, gap, margin, rows, cols, card_size, auto_fill)
    card_box = _compute_page_card_box(M)
    font_px = _compute_font_px(font_hanzi, font_pinyin, font_english, M.scale_factor)

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('page_preview.html.j2')

    ctx = PageTemplateContext(page_num=page_num, rows=rows, cols=cols, hanzi_font=hanzi_font, background_color=background_color)

    page_cards_ctx = [(page_cards[i] if i < len(page_cards) else None) for i in range(cards_per_page)]
    return template.render(M=M, font=font_px, card_box=card_box, ctx=ctx, page_cards=page_cards_ctx)

def create_simple_grid_html(cards: List[Dict[str, str]], hanzi_font: str = DEFAULT_HANZI_FONT,
                           background_color: str = DEFAULT_BACKGROUND_COLOR,
                           rows: int = 3, cols: int = 3,
                           font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14,
                           card_size: float = 5.5, auto_fill: bool = True) -> str:
    """Create simple HTML preview of cards (template via Jinja2)."""
    rows = max(1, int(rows or 3))
    cols = max(1, int(cols or 3))

    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    params = _compute_simple_grid_css(cols, card_size, auto_fill)
    font_px = _compute_simple_grid_font_px(font_hanzi, font_pinyin, font_english)
    card_box = _compute_simple_card_box(params.card_size_px_calc)

    # Build grid cards with padding for empty slots
    cards_per_page = rows * cols
    grid_cards: List[Dict[str, str]] = []
    for i in range(cards_per_page):
        grid_cards.append(cards[i] if i < len(cards) else None)

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('simple_grid.html.j2')

    ctx = SimpleGridTemplateContext(rows=rows, cols=cols, hanzi_font=hanzi_font, background_color=background_color)

    return template.render(params=params, ctx=ctx, font=font_px, card_box=card_box, grid_cards=grid_cards)


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
