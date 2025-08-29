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


def compute_auto_card_size_cm(page_size: str, margin_cm: float, gap_cm: float, 
                             rows: int, cols: int) -> float:
    """Compute automatic card size based on layout parameters."""
    # Simple A4 calculation (21cm x 29.7cm)
    if page_size == 'A4':
        usable_width = 21.0 - (2 * margin_cm) - ((cols - 1) * gap_cm)
        usable_height = 29.7 - (2 * margin_cm) - ((rows - 1) * gap_cm)
    else:
        # Default to A4 if unknown page size
        usable_width = 21.0 - (2 * margin_cm) - ((cols - 1) * gap_cm)
        usable_height = 29.7 - (2 * margin_cm) - ((rows - 1) * gap_cm)

    card_width = usable_width / cols
    card_height = usable_height / rows

    # Return the smaller dimension to ensure cards fit
    return min(card_width, card_height)


def validate_layout_params(rows: int, cols: int, card_size_cm: float, 
                          gap_cm: float, margin_cm: float, page_size: str) -> Dict[str, Any]:
    """Validate layout parameters."""
    # Simple validation - could be enhanced
    fits_on_page = True
    if page_size == 'A4':
        total_width = cols * card_size_cm + (cols - 1) * gap_cm + 2 * margin_cm
        total_height = rows * card_size_cm + (rows - 1) * gap_cm + 2 * margin_cm
        fits_on_page = total_width <= 21.0 and total_height <= 29.7
    
    return {
        'fits_on_page': fits_on_page,
        'total_width': cols * card_size_cm + (cols - 1) * gap_cm + 2 * margin_cm,
        'total_height': rows * card_size_cm + (rows - 1) * gap_cm + 2 * margin_cm
    }
