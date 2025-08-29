"""
Layout computation services for the Chinese Character Learning Cards application.
Provides functions for automatic card sizing, pagination, and layout calculations.
"""

from typing import Tuple, Dict, Any
from dataclasses import dataclass


@dataclass
class PaginateInfo:
    """Information about pagination."""
    cards_per_page: int
    total_pages: int


# Page size definitions in cm (width, height)
PAGE_SIZES = {
    'A4': (21.0, 29.7),
    'A3': (29.7, 42.0),
    'A5': (14.8, 21.0),
    'Letter': (21.6, 27.9),
    'Legal': (21.6, 35.6),
}


def compute_auto_card_size_cm(page_size: str, margin_cm: float, gap_cm: float, 
                             rows: int, cols: int) -> float:
    """
    Compute automatic card size based on layout parameters.
    
    Args:
        page_size: Page size name (e.g., 'A4', 'A3', 'Letter')
        margin_cm: Margin around the page in cm
        gap_cm: Gap between cards in cm
        rows: Number of rows
        cols: Number of columns
        
    Returns:
        Card size in cm (square cards, so width = height)
    """
    if page_size not in PAGE_SIZES:
        # Default to A4 if unknown page size
        page_size = 'A4'
    
    page_width, page_height = PAGE_SIZES[page_size]
    
    # Calculate usable area
    usable_width = page_width - (2 * margin_cm) - ((cols - 1) * gap_cm)
    usable_height = page_height - (2 * margin_cm) - ((rows - 1) * gap_cm)
    
    # Calculate card dimensions
    card_width = usable_width / cols
    card_height = usable_height / rows
    
    # Return the smaller dimension to ensure cards fit (square cards)
    card_size = min(card_width, card_height)
    
    # Ensure minimum size
    return max(card_size, 1.0)


def paginate(cards_count: int, rows: int, cols: int) -> PaginateInfo:
    """
    Calculate pagination information.
    
    Args:
        cards_count: Total number of cards
        rows: Number of rows per page
        cols: Number of columns per page
        
    Returns:
        PaginateInfo with cards_per_page and total_pages
    """
    cards_per_page = rows * cols
    
    if cards_count == 0:
        total_pages = 1  # Always at least 1 page for empty state
    else:
        total_pages = (cards_count + cards_per_page - 1) // cards_per_page
    
    return PaginateInfo(cards_per_page=cards_per_page, total_pages=total_pages)


def validate_layout_params(rows: int, cols: int, card_size: float, 
                          gap_cm: float, margin_cm: float, page_size: str) -> Dict[str, Any]:
    """
    Validate and normalize layout parameters.
    
    Args:
        rows: Number of rows
        cols: Number of columns
        card_size: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Margin around page in cm
        page_size: Page size name
        
    Returns:
        Dictionary with validated parameters and any warnings
    """
    warnings = []
    
    # Validate and clamp values
    rows = max(1, min(rows, 10))  # 1-10 rows
    cols = max(1, min(cols, 10))  # 1-10 columns
    card_size = max(1.0, min(card_size, 20.0))  # 1-20 cm
    gap_cm = max(0.0, min(gap_cm, 5.0))  # 0-5 cm
    margin_cm = max(0.5, min(margin_cm, 10.0))  # 0.5-10 cm
    
    # Validate page size
    if page_size not in PAGE_SIZES:
        warnings.append(f"Unknown page size '{page_size}', using A4")
        page_size = 'A4'
    
    # Check if cards fit on page
    page_width, page_height = PAGE_SIZES[page_size]
    required_width = (cols * card_size) + ((cols - 1) * gap_cm) + (2 * margin_cm)
    required_height = (rows * card_size) + ((rows - 1) * gap_cm) + (2 * margin_cm)
    
    if required_width > page_width:
        warnings.append(f"Cards may not fit horizontally (need {required_width:.1f}cm, have {page_width:.1f}cm)")
    
    if required_height > page_height:
        warnings.append(f"Cards may not fit vertically (need {required_height:.1f}cm, have {page_height:.1f}cm)")
    
    return {
        'rows': rows,
        'cols': cols,
        'card_size': card_size,
        'gap_cm': gap_cm,
        'margin_cm': margin_cm,
        'page_size': page_size,
        'warnings': warnings,
        'fits_on_page': len(warnings) == 0 or not any('not fit' in w for w in warnings)
    }


def compute_layout_metrics(cards_count: int, rows: int, cols: int, 
                          card_size: float, gap_cm: float, margin_cm: float, 
                          page_size: str) -> Dict[str, Any]:
    """
    Compute comprehensive layout metrics.
    
    Args:
        cards_count: Total number of cards
        rows: Number of rows per page
        cols: Number of columns per page
        card_size: Card size in cm
        gap_cm: Gap between cards in cm
        margin_cm: Margin around page in cm
        page_size: Page size name
        
    Returns:
        Dictionary with layout metrics and information
    """
    # Get pagination info
    pagination = paginate(cards_count, rows, cols)
    
    # Validate parameters
    validation = validate_layout_params(rows, cols, card_size, gap_cm, margin_cm, page_size)
    
    # Calculate dimensions
    page_width, page_height = PAGE_SIZES.get(page_size, PAGE_SIZES['A4'])
    total_width = (cols * card_size) + ((cols - 1) * gap_cm) + (2 * margin_cm)
    total_height = (rows * card_size) + ((rows - 1) * gap_cm) + (2 * margin_cm)
    
    # Calculate utilization
    page_area = page_width * page_height
    card_area = cards_count * (card_size * card_size)
    utilization = (card_area / (pagination.total_pages * page_area)) * 100 if page_area > 0 else 0
    
    return {
        'pagination': pagination,
        'validation': validation,
        'dimensions': {
            'page_width': page_width,
            'page_height': page_height,
            'total_width': total_width,
            'total_height': total_height,
            'card_area': card_size * card_size,
            'total_card_area': card_area,
        },
        'utilization': {
            'percentage': utilization,
            'cards_per_page': pagination.cards_per_page,
            'total_pages': pagination.total_pages,
        },
        'fits_on_page': validation['fits_on_page'],
        'warnings': validation['warnings']
    }


def suggest_optimal_layout(cards_count: int, page_size: str = 'A4', 
                          margin_cm: float = 1.0, gap_cm: float = 0.5,
                          min_card_size: float = 3.0) -> Dict[str, Any]:
    """
    Suggest optimal layout parameters for given constraints.
    
    Args:
        cards_count: Total number of cards
        page_size: Target page size
        margin_cm: Desired margin in cm
        gap_cm: Desired gap in cm
        min_card_size: Minimum acceptable card size in cm
        
    Returns:
        Dictionary with suggested layout parameters
    """
    best_layout = None
    best_score = 0
    
    # Try different row/column combinations
    for rows in range(1, 6):  # 1-5 rows
        for cols in range(1, 6):  # 1-5 columns
            # Calculate auto card size
            card_size = compute_auto_card_size_cm(page_size, margin_cm, gap_cm, rows, cols)
            
            # Skip if card size is too small
            if card_size < min_card_size:
                continue
            
            # Calculate metrics
            metrics = compute_layout_metrics(cards_count, rows, cols, card_size, 
                                           gap_cm, margin_cm, page_size)
            
            # Skip if doesn't fit
            if not metrics['fits_on_page']:
                continue
            
            # Score based on utilization and card size
            utilization_score = metrics['utilization']['percentage']
            card_size_score = min(card_size / 8.0, 1.0) * 100  # Prefer larger cards up to 8cm
            total_score = (utilization_score * 0.7) + (card_size_score * 0.3)
            
            if total_score > best_score:
                best_score = total_score
                best_layout = {
                    'rows': rows,
                    'cols': cols,
                    'card_size': card_size,
                    'gap_cm': gap_cm,
                    'margin_cm': margin_cm,
                    'page_size': page_size,
                    'score': total_score,
                    'metrics': metrics
                }
    
    return best_layout or {
        'rows': 2,
        'cols': 3,
        'card_size': min_card_size,
        'gap_cm': gap_cm,
        'margin_cm': margin_cm,
        'page_size': page_size,
        'score': 0,
        'metrics': None,
        'warning': 'No optimal layout found, using defaults'
    }
