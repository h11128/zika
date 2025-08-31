"""
Unit tests for the enhanced services/layout.py module.
Tests layout computation, pagination, auto-sizing, and optimization functions.
"""

import pytest
import math
from services.layout import (
    compute_auto_card_size_cm, paginate, PaginateInfo, LayoutMetrics, CardPosition,
    validate_layout_params, compute_layout_metrics, suggest_optimal_layout,
    compute_layout_efficiency, compute_card_positions, compute_pdf_layout,
    compute_pptx_layout, get_page_dimensions_cm, PAGE_SIZES, DEFAULT_PAGE_SIZE,
    CM_TO_POINTS, CM_TO_EMU
)


class TestComputeAutoCardSize:
    """Test automatic card size computation."""
    
    def test_compute_auto_card_size_a4_basic(self):
        """Test basic A4 card size computation."""
        card_size_cm = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
        
        # A4 is 21x29.7cm, with 1cm margin and 0.5cm gap
        # Usable width_cm: 21 - 2*1 - 2*0.5 = 18cm, so 18/3 = 6cm per card
        # Usable height_cm: 29.7 - 2*1 - 1*0.5 = 27.2cm, so 27.2/2 = 13.6cm per card
        # Should return min(6, 13.6) = 6cm
        assert abs(card_size - 6.0) < 0.1
    
    def test_compute_auto_card_size_unknown_page(self):
        """Test card size computation with unknown page size."""
        card_size_cm = compute_auto_card_size_cm('UNKNOWN', 1.0, 0.5, 2, 3)
        
        # Should default to A4
        expected = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
        assert card_size_cm == expected
    
    def test_compute_auto_card_size_minimum(self):
        """Test card size computation with extreme parameters."""
        # Use very large margins to force small card size
        card_size_cm = compute_auto_card_size_cm('A4', 10.0, 5.0, 5, 5)

        # Should return 0.0 when layout is impossible
        assert card_size >= 0.0

        # Test with reasonable parameters that should work
        reasonable_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 2)
        assert reasonable_size >= 1.0
    
    def test_compute_auto_card_size_different_pages(self):
        """Test card size computation for different page sizes."""
        a4_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 2)
        a3_size = compute_auto_card_size_cm('A3', 1.0, 0.5, 2, 2)
        
        # A3 is larger than A4, so cards should be larger
        assert a3_size > a4_size


class TestLayoutMetrics:
    """Test layout metrics computation."""

    def test_compute_layout_metrics_auto_fill(self):
        """Test layout metrics with auto-fill enabled."""
        metrics = compute_layout_metrics('A4', 5.0, 0.5, 1.0, 2, 3, layout_auto_fill=True)

        assert isinstance(metrics, LayoutMetrics)
        assert metrics.card_size_cm > 0
        assert metrics.grid_width_cm > 0
        assert metrics.grid_height_cm > 0
        assert metrics.fits_on_page is True
        assert metrics.scale_factor == 1.0  # Should fit without scaling

    def test_compute_layout_metrics_fixed_size(self):
        """Test layout metrics with fixed card size."""
        metrics = compute_layout_metrics('A4', 5.0, 0.5, 1.0, 2, 3, layout_auto_fill=False)

        assert metrics.card_size_cm == 5.0
        assert metrics.fits_on_page is True

    def test_compute_layout_metrics_scaling_needed(self):
        """Test layout metrics when scaling is needed."""
        # Use very large card size that won't fit
        metrics = compute_layout_metrics('A4', 15.0, 0.5, 1.0, 3, 3, layout_auto_fill=False)

        assert metrics.card_size_cm < 15.0  # Should be scaled down
        assert metrics.scale_factor < 1.0
        assert metrics.fits_on_page is True  # Should fit after scaling


class TestCardPositions:
    """Test card position computation."""

    def test_compute_card_positions_basic(self):
        """Test basic card position computation."""
        positions = compute_card_positions(2, 3, 5.0, 0.5, 1.0, 'A4')

        assert len(positions) == 6  # 2 rows * 3 cols
        assert all(isinstance(pos, CardPosition) for pos in positions)

        # Check first position
        first_pos = positions[0]
        assert first_pos.row == 0
        assert first_pos.col == 0
        assert first_pos.x_cm > 0
        assert first_pos.y_cm > 0

    def test_compute_card_positions_ordering(self):
        """Test that card positions are ordered correctly."""
        positions = compute_card_positions(2, 2, 5.0, 0.5, 1.0, 'A4')

        # Should be ordered row by row
        assert positions[0].row == 0 and positions[0].col == 0
        assert positions[1].row == 0 and positions[1].col == 1
        assert positions[2].row == 1 and positions[2].col == 0
        assert positions[3].row == 1 and positions[3].col == 1

    def test_compute_card_positions_spacing(self):
        """Test that card positions have correct spacing."""
        positions = compute_card_positions(1, 2, 5.0, 1.0, 1.0, 'A4')

        # Second card should be 6cm to the right (5cm card + 1cm gap)
        x_diff = positions[1].x_cm - positions[0].x_cm
        assert abs(x_diff - 6.0) < 0.1


class TestPDFLayout:
    """Test PDF layout computation."""

    def test_compute_pdf_layout_basic(self):
        """Test basic PDF layout computation."""
        layout = compute_pdf_layout('A4', 5.0, 0.5, 1.0, 2, 3)

        assert 'page_width_pt' in layout
        assert 'page_height_pt' in layout
        assert 'card_size_pt' in layout
        assert 'card_positions' in layout

        # Check conversion to points
        assert layout['card_size_pt'] == 5.0 * CM_TO_POINTS
        assert len(layout['card_positions']) == 6  # 2 rows * 3 cols

    def test_compute_pdf_layout_positions(self):
        """Test PDF layout position computation."""
        layout = compute_pdf_layout('A4', 5.0, 0.5, 1.0, 2, 2)

        positions = layout['card_positions']
        assert len(positions) == 4

        # All positions should be in points
        for x, y in positions:
            assert x > 0
            assert y > 0


class TestPPTXLayout:
    """Test PPTX layout computation."""

    def test_compute_pptx_layout_basic(self):
        """Test basic PPTX layout computation."""
        layout = compute_pptx_layout('A4', 5.0, 0.5, 1.0, 2, 3)

        assert 'page_width_emu' in layout
        assert 'page_height_emu' in layout
        assert 'card_size_emu' in layout
        assert 'card_positions' in layout

        # Check conversion to EMU
        assert layout['card_size_emu'] == 5.0 * CM_TO_EMU
        assert len(layout['card_positions']) == 6  # 2 rows * 3 cols

    def test_compute_pptx_layout_positions(self):
        """Test PPTX layout position computation."""
        layout = compute_pptx_layout('A4', 5.0, 0.5, 1.0, 2, 2)

        positions = layout['card_positions']
        assert len(positions) == 4

        # All positions should be in EMU
        for x, y in positions:
            assert x > 0
            assert y > 0


class TestValidateLayoutParams:
    """Test layout parameter validation."""

    def test_validate_layout_params_valid(self):
        """Test validation with valid parameters."""
        result = validate_layout_params(2, 3, 5.0, 0.5, 1.0, 'A4')

        assert result['fits_on_page'] is True
        assert len(result['errors']) == 0
        assert 'total_width' in result
        assert 'total_height' in result
        assert 'page_width' in result
        assert 'page_height' in result

    def test_validate_layout_params_too_large(self):
        """Test validation with layout too large for page."""
        result = validate_layout_params(5, 5, 10.0, 1.0, 1.0, 'A4')

        assert result['fits_on_page'] is False
        assert len(result['errors']) > 0
        assert any('too wide' in error or 'too tall' in error for error in result['errors'])

    def test_validate_layout_params_invalid_values(self):
        """Test validation with invalid parameter values."""
        result = validate_layout_params(0, 3, -1.0, -0.5, -1.0, 'A4')

        assert len(result['errors']) >= 4  # layout_rows, card_size, gap, margin
        assert any('positive' in error for error in result['errors'])
        assert any('negative' in error for error in result['errors'])

    def test_validate_layout_params_warnings(self):
        """Test validation warnings for suboptimal values."""
        result = validate_layout_params(2, 3, 1.0, 3.0, 0.1, 'A4')

        assert len(result['warnings']) > 0
        assert any('small' in warning for warning in result['warnings'])


class TestSuggestOptimalLayout:
    """Test optimal layout suggestion."""

    def test_suggest_optimal_layout_basic(self):
        """Test basic optimal layout suggestion."""
        suggestion = suggest_optimal_layout('A4', 12, margin_cm=1.0, gap_cm=0.5)

        if 'error' not in suggestion:
            assert 'layout_rows' in suggestion
            assert 'layout_cols' in suggestion
            assert 'card_size_cm' in suggestion
            assert suggestion['layout_rows'] > 0
            assert suggestion['layout_cols'] > 0
            assert suggestion['card_size_cm'] > 0

    def test_suggest_optimal_layout_many_cards(self):
        """Test optimal layout suggestion for many cards."""
        suggestion = suggest_optimal_layout('A4', 50, margin_cm=1.0, gap_cm=0.5)

        if 'error' not in suggestion:
            cards_per_page = suggestion['layout_rows'] * suggestion['layout_cols']
            pages_needed = math.ceil(50 / cards_per_page)
            assert pages_needed == suggestion['pages_needed']

    def test_suggest_optimal_layout_impossible_constraints(self):
        """Test optimal layout suggestion with impossible constraints."""
        suggestion = suggest_optimal_layout('A4', 10, margin_cm=1.0, gap_cm=0.5,
                                          min_card_size=15.0, max_card_size=20.0)

        # Should return error for impossible constraints
        assert 'error' in suggestion
        assert 'suggestions' in suggestion


class TestLayoutEfficiency:
    """Test layout efficiency computation."""

    def test_compute_layout_efficiency_perfect(self):
        """Test efficiency computation with perfect utilization."""
        efficiency = compute_layout_efficiency(3, 4, 12)  # Exactly fills one page

        assert efficiency['cards_per_page'] == 12
        assert efficiency['pages_needed'] == 1
        assert efficiency['utilization'] == 1.0
        assert efficiency['aspect_ratio'] == 4/3

    def test_compute_layout_efficiency_partial(self):
        """Test efficiency computation with partial utilization."""
        efficiency = compute_layout_efficiency(3, 4, 10)  # 10 cards on 12-slot page

        assert efficiency['cards_per_page'] == 12
        assert efficiency['pages_needed'] == 1
        assert efficiency['utilization'] == 10/12
        assert efficiency['efficiency_score'] > 0

    def test_compute_layout_efficiency_multiple_pages(self):
        """Test efficiency computation with multiple pages."""
        efficiency = compute_layout_efficiency(2, 3, 20)  # 20 cards, 6 per page

        assert efficiency['cards_per_page'] == 6
        assert efficiency['pages_needed'] == 4  # ceil(20/6) = 4
        assert efficiency['total_slots'] == 24  # 4 pages * 6 slots
        assert efficiency['utilization'] == 20/24


if __name__ == "__main__":
    pytest.main([__file__])



class TestPaginate:
    """Test pagination functionality."""
    
    def test_paginate_basic(self):
        """Test basic pagination."""
        result = paginate(10, 2, 3)
        
        assert isinstance(result, PaginateInfo)
        assert result.cards_per_page == 6  # 2 * 3
        assert result.total_pages == 2  # ceil(10/6)
    
    def test_paginate_exact_fit(self):
        """Test pagination with exact fit."""
        result = paginate(12, 2, 3)
        
        assert result.cards_per_page == 6
        assert result.total_pages == 2  # 12/6 = 2 exactly
    
    def test_paginate_empty_cards(self):
        """Test pagination with no cards."""
        result = paginate(0, 2, 3)
        
        assert result.cards_per_page == 6
        assert result.total_pages == 1  # Always at least 1 page
    
    def test_paginate_single_card(self):
        """Test pagination with single card."""
        result = paginate(1, 2, 3)
        
        assert result.cards_per_page == 6
        assert result.total_pages == 1


class TestValidateLayoutParams:
    """Test layout parameter validation."""
    
    def test_validate_layout_params_valid(self):
        """Test validation with valid parameters."""
        result = validate_layout_params(2, 3, 5.0, 0.5, 1.0, 'A4')

        assert result['fits_on_page'] is True
        assert len(result['errors']) == 0
        assert len(result['warnings']) == 0
        assert 'total_width' in result
        assert 'total_height' in result
        assert 'page_width' in result
        assert 'page_height' in result
    
    def test_validate_layout_params_invalid_values(self):
        """Test validation with invalid parameter values."""
        result = validate_layout_params(0, 3, -1.0, -0.5, -1.0, 'A4')

        assert len(result['errors']) >= 4  # layout_rows, card_size, gap, margin
        assert any('positive' in error for error in result['errors'])
        assert any('negative' in error for error in result['errors'])

    def test_validate_layout_params_warnings(self):
        """Test validation warnings for suboptimal values."""
        result = validate_layout_params(2, 3, 1.0, 3.0, 0.1, 'A4')

        assert len(result['warnings']) > 0
        assert any('small' in warning for warning in result['warnings'])
    
    def test_validate_layout_params_too_large(self):
        """Test validation with layout too large for page."""
        result = validate_layout_params(5, 5, 10.0, 1.0, 1.0, 'A4')

        assert result['fits_on_page'] is False
        assert len(result['errors']) > 0
        assert any('too wide' in error or 'too tall' in error for error in result['errors'])


class TestLayoutMetrics:
    """Test layout metrics computation."""

    def test_compute_layout_metrics_auto_fill(self):
        """Test layout metrics with auto-fill enabled."""
        metrics = compute_layout_metrics('A4', 5.0, 0.5, 1.0, 2, 3, layout_auto_fill=True)

        assert isinstance(metrics, LayoutMetrics)
        assert metrics.card_size_cm > 0
        assert metrics.grid_width_cm > 0
        assert metrics.grid_height_cm > 0
        assert metrics.fits_on_page is True
        assert metrics.scale_factor == 1.0  # Should fit without scaling

    def test_compute_layout_metrics_fixed_size(self):
        """Test layout metrics with fixed card size."""
        metrics = compute_layout_metrics('A4', 5.0, 0.5, 1.0, 2, 3, layout_auto_fill=False)

        assert metrics.card_size_cm == 5.0
        assert metrics.fits_on_page is True

    def test_compute_layout_metrics_scaling_needed(self):
        """Test layout metrics when scaling is needed."""
        # Use very large card size that won't fit
        metrics = compute_layout_metrics('A4', 15.0, 0.5, 1.0, 3, 3, layout_auto_fill=False)

        assert metrics.card_size_cm < 15.0  # Should be scaled down
        assert metrics.scale_factor < 1.0
        assert metrics.fits_on_page is True  # Should fit after scaling



class TestSuggestOptimalLayout:
    """Test optimal layout suggestion."""
    
    def test_suggest_optimal_layout_basic(self):
        """Test basic optimal layout suggestion."""
        suggestion = suggest_optimal_layout('A4', 12, margin_cm=1.0, gap_cm=0.5)

        if 'error' not in suggestion:
            assert 'layout_rows' in suggestion
            assert 'layout_cols' in suggestion
            assert 'card_size_cm' in suggestion
            assert suggestion['layout_rows'] > 0
            assert suggestion['layout_cols'] > 0
            assert suggestion['card_size_cm'] > 0
    
    def test_suggest_optimal_layout_impossible_constraints(self):
        """Test optimal layout suggestion with impossible constraints."""
        suggestion = suggest_optimal_layout('A4', 10, margin_cm=1.0, gap_cm=0.5,
                                          min_card_size=15.0, max_card_size=20.0)

        # Should return error for impossible constraints
        assert 'error' in suggestion
        assert 'suggestions' in suggestion
    
    def test_suggest_optimal_layout_different_counts(self):
        """Test optimal layout for different card counts."""
        small_result = suggest_optimal_layout('A4', 6, margin_cm=1.0, gap_cm=0.5, min_card_size=3.0)
        large_result = suggest_optimal_layout('A4', 50, margin_cm=1.0, gap_cm=0.5, min_card_size=3.0)
        
        # Both should have valid layouts
        assert small_result['score'] > 0
        assert large_result['score'] > 0
        
        # Layouts might be different for different counts
        small_cards_per_page = small_result['layout_rows'] * small_result['layout_cols']
        large_cards_per_page = large_result['layout_rows'] * large_result['layout_cols']
        
        # Both should be reasonable
        assert 1 <= small_cards_per_page <= 25
        assert 1 <= large_cards_per_page <= 25


class TestPageSizes:
    """Test page size definitions."""
    
    def test_page_sizes_defined(self):
        """Test that common page sizes are defined."""
        assert 'A4' in PAGE_SIZES
        assert 'A3' in PAGE_SIZES
        assert 'A5' in PAGE_SIZES
        assert 'Letter' in PAGE_SIZES
        assert 'Legal' in PAGE_SIZES
    
    def test_page_sizes_reasonable(self):
        """Test that page sizes have reasonable dimensions."""
        for name, (width, height) in PAGE_SIZES.items():
            assert width > 0
            assert height > 0
            assert width < 100  # Reasonable upper bound in cm
            assert height < 100
    
    def test_a4_size_correct(self):
        """Test that A4 size is correct."""
        width, height_cm = PAGE_SIZES['A4']
        assert abs(width - 21.0) < 0.1
        assert abs(height - 29.7) < 0.1
