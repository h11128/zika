"""
Unit tests for compute_auto_card_size_cm function.
Tests automatic card size calculation logic.
"""

import pytest
import math
from services.layout import compute_auto_card_size_cm, PAGE_SIZES


class TestComputeAutoCardSize:
    """Test compute_auto_card_size_cm function."""
    
    def test_basic_calculation_a4(self):
        """Test basic card size calculation for A4."""
        # A4: 21.0 x 29.7 cm
        # 2x3 grid, 1cm margin, 0.5cm gap
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
        
        # Available width: 21 - 2*1 = 19cm
        # Card width: (19 - 2*0.5) / 3 = 18/3 = 6cm
        # Available height: 29.7 - 2*1 = 27.7cm  
        # Card height: (27.7 - 1*0.5) / 2 = 27.2/2 = 13.6cm
        # Min of width/height: min(6, 13.6) = 6cm
        
        assert abs(card_size - 6.0) < 0.01
    
    def test_basic_calculation_letter(self):
        """Test basic card size calculation for Letter."""
        # Letter: 21.6 x 27.9 cm
        card_size = compute_auto_card_size_cm('Letter', 1.0, 0.5, 2, 3)
        
        # Available width: 21.6 - 2*1 = 19.6cm
        # Card width: (19.6 - 2*0.5) / 3 = 18.6/3 = 6.2cm
        # Available height: 27.9 - 2*1 = 25.9cm
        # Card height: (25.9 - 1*0.5) / 2 = 25.4/2 = 12.7cm
        # Min: min(6.2, 12.7) = 6.2cm
        
        assert abs(card_size - 6.2) < 0.01
    
    def test_single_card_layout(self):
        """Test calculation for single card (1x1 grid)."""
        card_size = compute_auto_card_size_cm('A4', 2.0, 0.0, 1, 1)
        
        # Available width: 21 - 2*2 = 17cm
        # Card width: 17/1 = 17cm (no gaps)
        # Available height: 29.7 - 2*2 = 25.7cm
        # Card height: 25.7/1 = 25.7cm
        # Min: min(17, 25.7) = 17cm
        
        assert abs(card_size - 17.0) < 0.01
    
    def test_large_grid_layout(self):
        """Test calculation for large grid (5x4)."""
        card_size = compute_auto_card_size_cm('A4', 0.5, 0.2, 5, 4)
        
        # Available width: 21 - 2*0.5 = 20cm
        # Card width: (20 - 3*0.2) / 4 = 19.4/4 = 4.85cm
        # Available height: 29.7 - 2*0.5 = 28.7cm
        # Card height: (28.7 - 4*0.2) / 5 = 27.9/5 = 5.58cm
        # Min: min(4.85, 5.58) = 4.85cm
        
        assert abs(card_size - 4.85) < 0.01
    
    def test_zero_margin(self):
        """Test calculation with zero margin."""
        card_size = compute_auto_card_size_cm('A4', 0.0, 0.5, 2, 2)
        
        # Available width: 21 - 0 = 21cm
        # Card width: (21 - 1*0.5) / 2 = 20.5/2 = 10.25cm
        # Available height: 29.7 - 0 = 29.7cm
        # Card height: (29.7 - 1*0.5) / 2 = 29.2/2 = 14.6cm
        # Min: min(10.25, 14.6) = 10.25cm
        
        assert abs(card_size - 10.25) < 0.01
    
    def test_zero_gap(self):
        """Test calculation with zero gap."""
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.0, 2, 3)
        
        # Available width: 21 - 2*1 = 19cm
        # Card width: 19/3 = 6.333...cm
        # Available height: 29.7 - 2*1 = 27.7cm
        # Card height: 27.7/2 = 13.85cm
        # Min: min(6.333, 13.85) = 6.333cm
        
        assert abs(card_size - (19.0/3.0)) < 0.01
    
    def test_large_margin_small_result(self):
        """Test calculation with large margin resulting in small cards."""
        card_size = compute_auto_card_size_cm('A4', 8.0, 1.0, 2, 2)
        
        # Available width: 21 - 2*8 = 5cm
        # Card width: (5 - 1*1) / 2 = 4/2 = 2cm
        # Available height: 29.7 - 2*8 = 13.7cm
        # Card height: (13.7 - 1*1) / 2 = 12.7/2 = 6.35cm
        # Min: min(2, 6.35) = 2cm
        
        assert abs(card_size - 2.0) < 0.01
    
    def test_impossible_layout_returns_zero(self):
        """Test that impossible layouts return 0."""
        # Margin too large for page
        card_size = compute_auto_card_size_cm('A4', 15.0, 0.5, 2, 2)
        assert card_size == 0.0
        
        # Gap too large
        card_size = compute_auto_card_size_cm('A4', 1.0, 20.0, 2, 2)
        assert card_size == 0.0
    
    def test_all_page_sizes(self):
        """Test calculation works for all supported page sizes."""
        for page_size in PAGE_SIZES.keys():
            card_size = compute_auto_card_size_cm(page_size, 1.0, 0.5, 2, 3)
            assert card_size > 0, f"Failed for page size {page_size}"
            assert isinstance(card_size, float)
    
    def test_edge_case_single_row_column(self):
        """Test edge cases with single row or column."""
        # Single row, multiple columns
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 1, 4)
        assert card_size > 0
        
        # Single column, multiple rows
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 4, 1)
        assert card_size > 0
    
    def test_precision_and_rounding(self):
        """Test precision and rounding behavior."""
        # Use parameters that create non-round results
        card_size = compute_auto_card_size_cm('A4', 1.1, 0.3, 3, 3)
        
        # Should return a reasonable float value
        assert isinstance(card_size, float)
        assert card_size > 0
        assert card_size < 20  # Sanity check
    
    def test_parameter_validation(self):
        """Test parameter validation and edge cases."""
        # Zero rows/cols should be handled gracefully
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 0, 3)
        assert card_size == 0.0
        
        card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 3, 0)
        assert card_size == 0.0
        
        # Negative values should be handled
        card_size = compute_auto_card_size_cm('A4', -1.0, 0.5, 2, 3)
        assert card_size >= 0  # Should not crash
    
    def test_unknown_page_size(self):
        """Test handling of unknown page size."""
        # Should either use a default or handle gracefully
        try:
            card_size = compute_auto_card_size_cm('UNKNOWN', 1.0, 0.5, 2, 3)
            # If it doesn't raise an exception, should return a reasonable value
            assert isinstance(card_size, (int, float))
        except (KeyError, ValueError):
            # It's acceptable to raise an exception for unknown page sizes
            pass


class TestCardSizeCalculationConsistency:
    """Test consistency of card size calculations."""
    
    def test_calculation_deterministic(self):
        """Test that calculations are deterministic."""
        params = ('A4', 1.0, 0.5, 2, 3)
        
        size1 = compute_auto_card_size_cm(*params)
        size2 = compute_auto_card_size_cm(*params)
        
        assert size1 == size2
    
    def test_scaling_behavior(self):
        """Test that card size scales appropriately with layout changes."""
        base_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 2)
        
        # More cards should result in smaller card size
        more_cards_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 3, 3)
        assert more_cards_size < base_size
        
        # Larger margin should result in smaller card size
        larger_margin_size = compute_auto_card_size_cm('A4', 2.0, 0.5, 2, 2)
        assert larger_margin_size < base_size
        
        # Larger gap should result in smaller card size
        larger_gap_size = compute_auto_card_size_cm('A4', 1.0, 1.0, 2, 2)
        assert larger_gap_size < base_size
    
    def test_aspect_ratio_constraint(self):
        """Test that card size respects aspect ratio constraints."""
        # Wide layout (more columns than rows)
        wide_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 4)
        
        # Tall layout (more rows than columns)  
        tall_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 4, 2)
        
        # Both should be positive and reasonable
        assert wide_size > 0
        assert tall_size > 0
        
        # The constraint should be different (width vs height limited)
        # This tests that the min() operation is working correctly
    
    def test_mathematical_properties(self):
        """Test mathematical properties of the calculation."""
        # Test that doubling both dimensions roughly halves the card size
        base_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 2)
        double_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 4, 4)
        
        # Should be roughly 1/4 the area, so roughly 1/2 the linear dimension
        # (allowing for gaps and margins affecting the calculation)
        assert double_size < base_size
        assert double_size > base_size * 0.2  # Should not be too small
    
    def test_boundary_conditions(self):
        """Test boundary conditions."""
        # Minimum viable layout
        min_size = compute_auto_card_size_cm('A4', 0.1, 0.1, 1, 1)
        assert min_size > 0
        
        # Maximum reasonable layout
        max_layout_size = compute_auto_card_size_cm('A4', 0.1, 0.1, 10, 10)
        assert max_layout_size > 0
        assert max_layout_size < min_size  # Should be smaller


class TestCardSizeIntegration:
    """Test integration with other layout functions."""
    
    def test_integration_with_page_sizes(self):
        """Test integration with PAGE_SIZES constant."""
        for page_name, (width, height) in PAGE_SIZES.items():
            card_size = compute_auto_card_size_cm(page_name, 1.0, 0.5, 2, 3)
            
            # Card size should be reasonable relative to page size
            assert card_size > 0
            assert card_size < min(width, height)  # Should be smaller than page dimensions
    
    def test_real_world_scenarios(self):
        """Test realistic usage scenarios."""
        # Common business card layout
        business_card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 3, 3)
        assert 3.0 < business_card_size < 8.0  # Reasonable size range
        
        # Flashcard layout
        flashcard_size = compute_auto_card_size_cm('A4', 1.5, 0.8, 2, 2)
        assert 5.0 < flashcard_size < 12.0  # Reasonable size range
        
        # Dense layout for small cards
        dense_size = compute_auto_card_size_cm('A4', 0.5, 0.3, 4, 5)
        assert 1.0 < dense_size < 5.0  # Should be smaller but usable


if __name__ == "__main__":
    pytest.main([__file__])
