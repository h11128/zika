"""
Layout utilities for the UI refactor.
Provides pagination and layout computation functions.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class PaginateInfo:
    """Pagination information."""
    cards_per_page: int
    total_pages: int


def paginate(total_cards: int, rows: int, cols: int) -> PaginateInfo:
    """Calculate pagination information."""
    cards_per_page = max(1, rows * cols)
    total_pages = max(1, (total_cards + cards_per_page - 1) // cards_per_page)
    return PaginateInfo(cards_per_page=cards_per_page, total_pages=total_pages)


def get_page_dimensions_cm(page_size: str) -> tuple:
    """Get page dimensions in cm for different page sizes."""
    dimensions = {
        'A4': (21.0, 29.7),
        'A3': (29.7, 42.0),
        'A5': (14.8, 21.0),
        'Letter': (21.6, 27.9)
    }
    return dimensions.get(page_size, (21.0, 29.7))  # Default to A4


def compute_auto_card_size_cm(page_size: str, margin_cm: float, gap_cm: float,
                             rows: int, cols: int) -> float:
    """Compute automatic card size based on layout parameters."""
    # Get page dimensions
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Calculate usable space
    usable_width = page_width - (2 * margin_cm) - ((cols - 1) * gap_cm)
    usable_height = page_height - (2 * margin_cm) - ((rows - 1) * gap_cm)

    card_width = usable_width / cols
    card_height = usable_height / rows

    # Return the smaller dimension to ensure cards fit
    return min(card_width, card_height)


def compute_pdf_layout(page_size: str, card_size_cm: float, gap_cm: float,
                      margin_cm: float, rows: int, cols: int) -> Dict[str, Any]:
    """
    Compute layout parameters for PDF generation.
    Extracted from src/layout_pdf.py
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Convert to points (1 cm = 28.35 points)
    CM_TO_POINTS = 28.35

    layout = {
        'page_width_pt': page_width * CM_TO_POINTS,
        'page_height_pt': page_height * CM_TO_POINTS,
        'card_size_pt': card_size_cm * CM_TO_POINTS,
        'gap_pt': gap_cm * CM_TO_POINTS,
        'margin_pt': margin_cm * CM_TO_POINTS,
        'rows': rows,
        'cols': cols,
        'cards_per_page': rows * cols
    }

    # Calculate card positions
    layout['card_positions'] = []
    for row in range(rows):
        for col in range(cols):
            x = layout['margin_pt'] + col * (layout['card_size_pt'] + layout['gap_pt'])
            y = layout['margin_pt'] + row * (layout['card_size_pt'] + layout['gap_pt'])
            layout['card_positions'].append((x, y))

    return layout


def compute_pptx_layout(page_size: str, card_size_cm: float, gap_cm: float,
                       margin_cm: float, rows: int, cols: int) -> Dict[str, Any]:
    """
    Compute layout parameters for PPTX generation.
    Extracted from src/layout_pptx.py
    """
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Convert to EMU (English Metric Units, 1 cm = 360000 EMU)
    CM_TO_EMU = 360000

    layout = {
        'page_width_emu': page_width * CM_TO_EMU,
        'page_height_emu': page_height * CM_TO_EMU,
        'card_size_emu': card_size_cm * CM_TO_EMU,
        'gap_emu': gap_cm * CM_TO_EMU,
        'margin_emu': margin_cm * CM_TO_EMU,
        'rows': rows,
        'cols': cols,
        'cards_per_page': rows * cols
    }

    # Calculate card positions
    layout['card_positions'] = []
    for row in range(rows):
        for col in range(cols):
            x = layout['margin_emu'] + col * (layout['card_size_emu'] + layout['gap_emu'])
            y = layout['margin_emu'] + row * (layout['card_size_emu'] + layout['gap_emu'])
            layout['card_positions'].append((x, y))

    return layout


def validate_layout_params(rows: int, cols: int, card_size_cm: float,
                          gap_cm: float, margin_cm: float, page_size: str) -> Dict[str, Any]:
    """Validate layout parameters with enhanced validation."""
    page_width, page_height = get_page_dimensions_cm(page_size)

    # Calculate required space
    total_width = cols * card_size_cm + (cols - 1) * gap_cm + 2 * margin_cm
    total_height = rows * card_size_cm + (rows - 1) * gap_cm + 2 * margin_cm

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

    if card_size_cm < 2.0:
        result['warnings'].append("Card size is very small (< 2cm)")
    elif card_size_cm > 8.0:
        result['warnings'].append("Card size is very large (> 8cm)")

    return result
