"""
Unit tests for the services/layout.py module.
Tests layout computation, pagination, and auto-sizing functions.
"""

import pytest
from services.layout import (
    compute_auto_card_size_cm, paginate, PaginateInfo,
    validate_layout_params, compute_layout_metrics,
    suggest_optimal_layout, PAGE_SIZES
)


class TestComputeAutoCardSize:
    """Test automatic card size computation."""
    
    def test_compute_auto_card_size_a4_basic(self):
        """Test basic A4 card size computation."""
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
        
        # A4 is 21x29.7cm, with 1cm margin and 0.5cm gap
        # Usable width: 21 - 2*1 - 2*0.5 = 18cm, so 18/3 = 6cm per card
        # Usable height: 29.7 - 2*1 - 1*0.5 = 27.2cm, so 27.2/2 = 13.6cm per card
        # Should return min(6, 13.6) = 6cm
        assert abs(card_size - 6.0) < 0.1
    
    def test_compute_auto_card_size_unknown_page(self):
        """Test card size computation with unknown page size."""
        card_size = compute_auto_card_size_cm('UNKNOWN', 1.0, 0.5, 2, 3)
        
        # Should default to A4
        expected = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
        assert card_size == expected
    
    def test_compute_auto_card_size_minimum(self):
        """Test that card size has a minimum value."""
        # Use very large margins to force small card size
        card_size = compute_auto_card_size_cm('A4', 10.0, 5.0, 5, 5)
        
        # Should return at least 1.0cm
        assert card_size >= 1.0
    
    def test_compute_auto_card_size_different_pages(self):
        """Test card size computation for different page sizes."""
        a4_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 2)
        a3_size = compute_auto_card_size_cm('A3', 1.0, 0.5, 2, 2)
        
        # A3 is larger than A4, so cards should be larger
        assert a3_size > a4_size


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
        
        assert result['rows'] == 2
        assert result['cols'] == 3
        assert result['card_size'] == 5.0
        assert result['gap_cm'] == 0.5
        assert result['margin_cm'] == 1.0
        assert result['page_size'] == 'A4'
        assert len(result['warnings']) == 0
        assert result['fits_on_page'] is True
    
    def test_validate_layout_params_clamping(self):
        """Test parameter clamping."""
        result = validate_layout_params(-1, 15, 25.0, -1.0, 0.1, 'A4')
        
        assert result['rows'] == 1  # Clamped from -1
        assert result['cols'] == 10  # Clamped from 15
        assert result['card_size'] == 20.0  # Clamped from 25.0
        assert result['gap_cm'] == 0.0  # Clamped from -1.0
        assert result['margin_cm'] == 0.5  # Clamped from 0.1
    
    def test_validate_layout_params_unknown_page_size(self):
        """Test validation with unknown page size."""
        result = validate_layout_params(2, 3, 5.0, 0.5, 1.0, 'UNKNOWN')
        
        assert result['page_size'] == 'A4'  # Should default to A4
        assert any('Unknown page size' in w for w in result['warnings'])
    
    def test_validate_layout_params_too_large(self):
        """Test validation with cards too large for page."""
        result = validate_layout_params(3, 4, 10.0, 2.0, 2.0, 'A4')
        
        # Should have warnings about not fitting
        assert any('not fit' in w for w in result['warnings'])
        assert result['fits_on_page'] is False


class TestComputeLayoutMetrics:
    """Test comprehensive layout metrics computation."""
    
    def test_compute_layout_metrics_basic(self):
        """Test basic layout metrics computation."""
        result = compute_layout_metrics(10, 2, 3, 5.0, 0.5, 1.0, 'A4')
        
        assert 'pagination' in result
        assert 'validation' in result
        assert 'dimensions' in result
        assert 'utilization' in result
        
        # Check pagination
        assert result['pagination'].cards_per_page == 6
        assert result['pagination'].total_pages == 2
        
        # Check dimensions
        assert result['dimensions']['page_width'] == 21.0  # A4 width
        assert result['dimensions']['page_height'] == 29.7  # A4 height
        assert result['dimensions']['card_area'] == 25.0  # 5.0 * 5.0
        
        # Check utilization
        assert result['utilization']['percentage'] > 0
        assert result['utilization']['cards_per_page'] == 6
        assert result['utilization']['total_pages'] == 2
    
    def test_compute_layout_metrics_empty_cards(self):
        """Test layout metrics with no cards."""
        result = compute_layout_metrics(0, 2, 3, 5.0, 0.5, 1.0, 'A4')
        
        assert result['pagination'].total_pages == 1
        assert result['utilization']['percentage'] == 0


class TestSuggestOptimalLayout:
    """Test optimal layout suggestion."""
    
    def test_suggest_optimal_layout_basic(self):
        """Test basic optimal layout suggestion."""
        result = suggest_optimal_layout(12, 'A4', 1.0, 0.5, 3.0)
        
        assert 'rows' in result
        assert 'cols' in result
        assert 'card_size' in result
        assert 'score' in result
        assert result['card_size'] >= 3.0  # Respects minimum
        assert result['rows'] >= 1
        assert result['cols'] >= 1
    
    def test_suggest_optimal_layout_no_solution(self):
        """Test optimal layout when no good solution exists."""
        # Very high minimum card size that can't be satisfied
        result = suggest_optimal_layout(100, 'A4', 1.0, 0.5, 25.0)

        # Should return defaults with warning when no solution found
        if 'warning' in result:
            assert result['rows'] == 2
            assert result['cols'] == 3
            assert result['card_size'] == 25.0
        else:
            # If a solution was found, it should still be valid
            assert result['card_size'] >= 25.0
            assert result['score'] >= 0
    
    def test_suggest_optimal_layout_different_counts(self):
        """Test optimal layout for different card counts."""
        small_result = suggest_optimal_layout(6, 'A4', 1.0, 0.5, 3.0)
        large_result = suggest_optimal_layout(50, 'A4', 1.0, 0.5, 3.0)
        
        # Both should have valid layouts
        assert small_result['score'] > 0
        assert large_result['score'] > 0
        
        # Layouts might be different for different counts
        small_cards_per_page = small_result['rows'] * small_result['cols']
        large_cards_per_page = large_result['rows'] * large_result['cols']
        
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
        width, height = PAGE_SIZES['A4']
        assert abs(width - 21.0) < 0.1
        assert abs(height - 29.7) < 0.1
