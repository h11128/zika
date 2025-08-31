"""
Layout utilities for the UI refactor.
Provides pagination and layout computation functions extracted from PDF/PPTX exporters.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple, List, Optional
import math


@dataclass(frozen=True)
class PaginateInfo:
    """Pagination information with immutable dataclass."""
    cards_per_page: int
    total_pages: int


@dataclass(frozen=True)
class LayoutMetrics:
    """Layout metrics for card positioning."""
    card_size_cm: float
    grid_width_cm: float
    grid_height_cm: float
    fits_on_page: bool
    scale_factor: float = 1.0


@dataclass(frozen=True)
class CardPosition:
    """Position of a card in the layout."""
    row: int
    col: int
    x_cm: float
    y_cm: float


def paginate(total_cards: int, layout_rows: int, layout_cols: int) -> PaginateInfo:
    """
    Calculate pagination information.

    Args:
        total_cards: Total number of cards to paginate
        layout_rows: Number of rows per page
        layout_cols: Number of columns per page

    Returns:
        PaginateInfo with cards_per_page and total_pages
    """
    cards_per_page = max(1, layout_rows * layout_cols)
    total_pages = max(1, (total_cards + cards_per_page - 1) // cards_per_page)
    return PaginateInfo(cards_per_page=cards_per_page, total_pages=total_pages)


# Standard page sizes in cm
PAGE_SIZES = {
    'A4': (21.0, 29.7),
    'A3': (29.7, 42.0),
    'A5': (14.8, 21.0),
    'Letter': (21.6, 27.9),
    'Legal': (21.6, 35.6),
    'Tabloid': (27.9, 43.2)
}

# Default page size
DEFAULT_PAGE_SIZE = 'A4'

# Conversion constants
CM_TO_POINTS = 28.35  # 1 cm = 28.35 points (PDF)
CM_TO_EMU = 360000    # 1 cm = 360000 EMU (PPTX)
CM_TO_MM = 10.0       # 1 cm = 10 mm


def get_page_dimensions_cm(page_size: str) -> Tuple[float, float]:
    """
    Get page dimensions in cm for different page sizes.

    Args:
        page_size: Page size name (e.g., 'A4', 'Letter')

    Returns:
        Tuple of (width_cm, height_cm)
    """
    return PAGE_SIZES.get(page_size, PAGE_SIZES[DEFAULT_PAGE_SIZE])


def compute_auto_card_size_cm(page_size: str, margin_cm: float, gap_cm: float,
                             layout_rows: int, layout_cols: int) -> float:
    """
    Compute automatic card size based on layout parameters.
    Extracted from PDF/PPTX generator logic.

    Args:
        page_size: Page size name
        margin_cm: Page margin in cm
        gap_cm: Gap between cards in cm
        layout_rows: Number of rows
        layout_cols: Number of columns

    Returns:
        Optimal card size in cm that fits the layout
    """
    # Get page dimensions
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Calculate usable space
    usable_width = page_width - (2 * margin_cm) - (max(0, cols - 1) * gap_cm)
    usable_height = page_height - (2 * margin_cm) - (max(0, rows - 1) * gap_cm)

    # Calculate card dimensions
    card_width = usable_width / cols if cols > 0 else 0
    card_height = usable_height / rows if rows > 0 else 0

    # Return the smaller dimension to ensure cards fit
    return max(0.0, min(card_width, card_height))


def compute_layout_metrics(page_size: str, card_size_cm: float, gap_cm: float,
                          margin_cm: float, layout_rows: int, layout_cols: int,
                          layout_auto_fill: bool = True) -> LayoutMetrics:
    """
    Compute comprehensive layout metrics with auto-sizing and validation.
    Extracted and enhanced from PDF/PPTX generator logic.

    Args:
        page_size: Page size name
        card_size_cm: Initial card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Page margin in cm
        layout_rows: Number of rows
        layout_cols: Number of columns
        layout_auto_fill: Whether to auto-compute card size to fill page

    Returns:
        LayoutMetrics with computed dimensions and fit validation
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Determine final card size
    if layout_auto_fill:
        final_card_size = compute_auto_card_size_cm(page_size, margin_cm, gap_cm, layout_rows, cols)
    else:
        final_card_size = card_size_cm

    # Calculate grid dimensions
    grid_width = cols * final_card_size + max(0, cols - 1) * gap_cm
    grid_height = rows * final_card_size + max(0, rows - 1) * gap_cm

    # Check if layout fits on page
    total_width = grid_width + 2 * margin_cm
    total_height = grid_height + 2 * margin_cm
    fits_on_page = total_width <= page_width and total_height <= page_height

    # Calculate scale factor if needed
    scale_factor = 1.0
    if not fits_on_page:
        scale_w = page_width / total_width if total_width > 0 else 1.0
        scale_h = page_height / total_height if total_height > 0 else 1.0
        scale_factor = min(scale_w, scale_h) * 0.995  # Small safety margin
        final_card_size *= scale_factor
        grid_width *= scale_factor
        grid_height *= scale_factor
        fits_on_page = True  # After scaling

    return LayoutMetrics(
        card_size_cm=final_card_size,
        grid_width_cm=grid_width,
        grid_height_cm=grid_height,
        fits_on_page=fits_on_page,
        scale_factor=scale_factor
    )


def compute_card_positions(layout_rows: int, layout_cols: int, card_size_cm: float,
                          gap_cm: float, margin_cm: float,
                          page_size: str) -> List[CardPosition]:
    """
    Compute positions for all cards in the grid layout.

    Args:
        layout_rows: Number of rows
        layout_cols: Number of columns
        card_size_cm: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Page margin in cm
        page_size: Page size name

    Returns:
        List of CardPosition objects with row, col, x_cm, y_cm
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Calculate grid dimensions
    grid_width = cols * card_size_cm + max(0, cols - 1) * gap_cm
    grid_height = rows * card_size_cm + max(0, rows - 1) * gap_cm

    # Center grid on page
    start_x = margin_cm + (page_width - 2 * margin_cm - grid_width) / 2
    start_y = margin_cm + (page_height - 2 * margin_cm - grid_height) / 2

    positions = []
    for row in range(rows):
        for col in range(cols):
            x = start_x + col * (card_size_cm + gap_cm)
            y = start_y + row * (card_size_cm + gap_cm)
            positions.append(CardPosition(row=row, col=col, x_cm=x, y_cm=y))

    return positions


def compute_pdf_layout(page_size: str, card_size_cm: float, gap_cm: float,
                      margin_cm: float, layout_rows: int, layout_cols: int) -> Dict[str, Any]:
    """
    Compute layout parameters for PDF generation.
    Extracted from src/layout_pdf.py

    Args:
        page_size: Page size name
        card_size_cm: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Page margin in cm
        layout_rows: Number of rows
        layout_cols: Number of columns

    Returns:
        Dictionary with PDF layout parameters in points
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    layout = {
        'page_width_pt': page_width * CM_TO_POINTS,
        'page_height_pt': page_height * CM_TO_POINTS,
        'card_size_pt': card_size_cm * CM_TO_POINTS,
        'gap_pt': gap_cm * CM_TO_POINTS,
        'margin_pt': margin_cm * CM_TO_POINTS,
        'layout_rows': layout_rows,
        'layout_cols': layout_cols,
        'cards_per_page': rows * cols
    }

    # Calculate card positions in points
    positions = compute_card_positions(layout_rows, layout_cols, card_size_cm, gap_cm, margin_cm, page_size)
    layout['card_positions'] = [(pos.x_cm * CM_TO_POINTS, pos.y_cm * CM_TO_POINTS)
                               for pos in positions]

    return layout


def compute_pptx_layout(page_size: str, card_size_cm: float, gap_cm: float,
                       margin_cm: float, layout_rows: int, layout_cols: int) -> Dict[str, Any]:
    """
    Compute layout parameters for PPTX generation.
    Extracted from src/layout_pptx.py

    Args:
        page_size: Page size name
        card_size_cm: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Page margin in cm
        layout_rows: Number of rows
        layout_cols: Number of columns

    Returns:
        Dictionary with PPTX layout parameters in EMU
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    layout = {
        'page_width_emu': page_width * CM_TO_EMU,
        'page_height_emu': page_height * CM_TO_EMU,
        'card_size_emu': card_size_cm * CM_TO_EMU,
        'gap_emu': gap_cm * CM_TO_EMU,
        'margin_emu': margin_cm * CM_TO_EMU,
        'layout_rows': layout_rows,
        'layout_cols': layout_cols,
        'cards_per_page': rows * cols
    }

    # Calculate card positions in EMU
    positions = compute_card_positions(layout_rows, layout_cols, card_size_cm, gap_cm, margin_cm, page_size)
    layout['card_positions'] = [(pos.x_cm * CM_TO_EMU, pos.y_cm * CM_TO_EMU)
                               for pos in positions]

    return layout


def validate_layout_params(layout_rows: int, layout_cols: int, card_size_cm: float,
                          gap_cm: float, margin_cm: float, page_size: str) -> Dict[str, Any]:
    """
    Validate layout parameters with enhanced validation.

    Args:
        layout_rows: Number of rows
        layout_cols: Number of columns
        card_size_cm: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Page margin in cm
        page_size: Page size name

    Returns:
        Dictionary with validation results, warnings, and errors
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Calculate required space
    total_width = cols * card_size_cm + max(0, cols - 1) * gap_cm + 2 * margin_cm
    total_height = rows * card_size_cm + max(0, rows - 1) * gap_cm + 2 * margin_cm

    fits_on_page = total_width <= page_width and total_height <= page_height

    result = {
        'fits_on_page': fits_on_page,
        'total_width': total_width,
        'total_height': total_height,
        'page_width': page_width,
        'page_height': page_height,
        'warnings': [],
        'errors': []
    }

    # Add warnings and errors
    if not fits_on_page:
        if total_width > page_width:
            result['errors'].append(f"Layout too wide: {total_width:.1f}cm > {page_width:.1f}cm")
        if total_height > page_height:
            result['errors'].append(f"Layout too tall: {total_height:.1f}cm > {page_height:.1f}cm")

    # Parameter validation
    if rows <= 0 or cols <= 0:
        result['errors'].append("Rows and columns must be positive")
    if card_size_cm <= 0:
        result['errors'].append("Card size must be positive")
    if gap_cm < 0:
        result['errors'].append("Gap cannot be negative")
    if margin_cm < 0:
        result['errors'].append("Margin cannot be negative")

    # Warnings for suboptimal values
    if card_size_cm < 2.0:
        result['warnings'].append("Card size is very small (< 2cm)")
    elif card_size_cm > 8.0:
        result['warnings'].append("Card size is very large (> 8cm)")

    if margin_cm < 0.5:
        result['warnings'].append("Margin is very small (< 0.5cm)")
    elif margin_cm > 3.0:
        result['warnings'].append("Margin is very large (> 3cm)")

    if gap_cm > 2.0:
        result['warnings'].append("Gap is very large (> 2cm)")

    return result


def suggest_optimal_layout(page_size: str, total_cards: int,
                          margin_cm: float = 1.0, gap_cm: float = 0.5,
                          min_card_size: float = 3.0, max_card_size: float = 7.0) -> Dict[str, Any]:
    """
    Suggest optimal layout parameters for given constraints.

    Args:
        page_size: Page size name
        total_cards: Total number of cards to layout
        margin_cm: Preferred margin in cm
        gap_cm: Preferred gap in cm
        min_card_size: Minimum acceptable card size in cm
        max_card_size: Maximum acceptable card size in cm

    Returns:
        Dictionary with suggested layout parameters
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    best_layout = None
    best_score = 0

    # Try different row/column combinations
    max_dimension = min(8, int(math.sqrt(total_cards)) + 3)

    for rows in range(1, max_dimension + 1):
        for cols in range(1, max_dimension + 1):
            cards_per_page = rows * cols
            if cards_per_page < total_cards * 0.5:  # Skip very inefficient layouts
                continue

            # Compute auto card size
            card_size_cm = compute_auto_card_size_cm(page_size, margin_cm, gap_cm, layout_rows, cols)

            # Check constraints
            if card_size < min_card_size or card_size > max_card_size:
                continue

            # Validate layout
            validation = validate_layout_params(layout_rows, layout_cols, card_size, gap_cm, margin_cm, page_size)
            if not validation['fits_on_page'] or validation['errors']:
                continue

            # Calculate score (prefer larger cards, fewer pages, balanced aspect ratio)
            pages_needed = math.ceil(total_cards / cards_per_page)
            aspect_ratio = max(layout_rows, cols) / min(layout_rows, cols)

            score = (
                card_size * 10 +  # Prefer larger cards
                (10 / pages_needed) +  # Prefer fewer pages
                (5 / aspect_ratio) +  # Prefer square-ish layouts
                (5 if len(validation['warnings']) == 0 else 0)  # Prefer no warnings
            )

            if score > best_score:
                best_score = score
                best_layout = {
                    'layout_rows': layout_rows,
                    'layout_cols': layout_cols,
                    'card_size_cm': card_size,
                    'gap_cm': gap_cm,
                    'margin_cm': margin_cm,
                    'cards_per_page': cards_per_page,
                    'pages_needed': pages_needed,
                    'score': score,
                    'validation': validation
                }

    return best_layout or {
        'error': 'No suitable layout found for given constraints',
        'suggestions': [
            'Try reducing margin or gap',
            'Consider smaller minimum card size',
            'Use larger page size'
        ]
    }


def compute_layout_efficiency(layout_rows: int, layout_cols: int, total_cards: int) -> Dict[str, float]:
    """
    Compute layout efficiency metrics.

    Args:
        layout_rows: Number of rows
        layout_cols: Number of columns
        total_cards: Total number of cards

    Returns:
        Dictionary with efficiency metrics
    """
    cards_per_page = rows * cols
    pages_needed = math.ceil(total_cards / cards_per_page)
    total_slots = pages_needed * cards_per_page

    utilization = total_cards / total_slots if total_slots > 0 else 0
    aspect_ratio = max(layout_rows, cols) / min(layout_rows, cols) if min(layout_rows, cols) > 0 else float('inf')

    return {
        'cards_per_page': cards_per_page,
        'pages_needed': pages_needed,
        'total_slots': total_slots,
        'utilization': utilization,
        'aspect_ratio': aspect_ratio,
        'efficiency_score': utilization / aspect_ratio if aspect_ratio > 0 else 0
    }
