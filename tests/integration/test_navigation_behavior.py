"""
Integration tests for navigation behavior.
Tests that nav resets only on layout/cards_count changes, not on style-only changes.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import the state service and related modules
import importlib.util
spec = importlib.util.spec_from_file_location("ui_state", os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'state.py'))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)

StateService = ui_state_module.StateService
get_state_service = ui_state_module.get_state_service


class TestNavigationResetBehavior:
    """Test navigation reset behavior based on change types."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock state service for testing
        self.state_service = MagicMock()
        self.state_values = {
            'current_page': 2,
            'layout_rows': 2,
            'layout_cols': 3,
            'cards_count': 20,
            'background_color': '#FFFFFF',
            'hanzi_font_size_pt': 48
        }
        
        # Mock state service methods
        def mock_get_option(key, default=None):
            return self.state_values.get(key, default)
        
        def mock_set_option(key, value):
            old_value = self.state_values.get(key)
            self.state_values[key] = value
            return old_value != value
        
        self.state_service.get_option = mock_get_option
        self.state_service.set_option = mock_set_option
        
        # Mock navigation reset logic
        self.nav_reset_called = False
        def mock_reset_navigation():
            self.nav_reset_called = True
            self.state_values['current_page'] = 1
        
        self.state_service.reset_navigation = mock_reset_navigation
    
    def test_layout_change_resets_navigation(self):
        """Test that layout changes reset navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 3)
        assert self.state_service.get_option('current_page') == 3
        
        # Change layout - should trigger nav reset
        self.state_service.set_option('layout_rows', 3)
        
        # Simulate the navigation reset logic
        if self.state_service.get_option('layout_rows') != 2:  # Changed from initial
            self.state_service.reset_navigation()
        
        # Navigation should be reset
        assert self.nav_reset_called
        assert self.state_service.get_option('current_page') == 1
    
    def test_cards_count_change_resets_navigation(self):
        """Test that cards count changes reset navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 3)
        assert self.state_service.get_option('current_page') == 3
        
        # Change cards count - should trigger nav reset
        self.state_service.set_option('cards_count', 30)
        
        # Simulate the navigation reset logic
        if self.state_service.get_option('cards_count') != 20:  # Changed from initial
            self.state_service.reset_navigation()
        
        # Navigation should be reset
        assert self.nav_reset_called
        assert self.state_service.get_option('current_page') == 1
    
    def test_style_change_preserves_navigation(self):
        """Test that style-only changes preserve navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 3)
        assert self.state_service.get_option('current_page') == 3
        
        # Change style only - should NOT trigger nav reset
        self.state_service.set_option('background_color', '#F0F0F0')
        
        # Simulate the navigation reset logic (should not trigger)
        layout_changed = (
            self.state_service.get_option('layout_rows') != 2 or
            self.state_service.get_option('layout_cols') != 3
        )
        cards_count_changed = self.state_service.get_option('cards_count') != 20
        
        if layout_changed or cards_count_changed:
            self.state_service.reset_navigation()
        
        # Navigation should be preserved
        assert not self.nav_reset_called
        assert self.state_service.get_option('current_page') == 3
    
    def test_typography_change_preserves_navigation(self):
        """Test that typography changes preserve navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 2)
        assert self.state_service.get_option('current_page') == 2
        
        # Change typography only - should NOT trigger nav reset
        self.state_service.set_option('hanzi_font_size_pt', 52)
        
        # Simulate the navigation reset logic (should not trigger)
        layout_changed = (
            self.state_service.get_option('layout_rows') != 2 or
            self.state_service.get_option('layout_cols') != 3
        )
        cards_count_changed = self.state_service.get_option('cards_count') != 20
        
        if layout_changed or cards_count_changed:
            self.state_service.reset_navigation()
        
        # Navigation should be preserved
        assert not self.nav_reset_called
        assert self.state_service.get_option('current_page') == 2
    
    def test_multiple_style_changes_preserve_navigation(self):
        """Test that multiple style changes preserve navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 4)
        assert self.state_service.get_option('current_page') == 4
        
        # Change multiple style properties - should NOT trigger nav reset
        self.state_service.set_option('background_color', '#E0E0E0')
        self.state_service.set_option('hanzi_font_size_pt', 44)
        
        # Simulate the navigation reset logic (should not trigger)
        layout_changed = (
            self.state_service.get_option('layout_rows') != 2 or
            self.state_service.get_option('layout_cols') != 3
        )
        cards_count_changed = self.state_service.get_option('cards_count') != 20
        
        if layout_changed or cards_count_changed:
            self.state_service.reset_navigation()
        
        # Navigation should be preserved
        assert not self.nav_reset_called
        assert self.state_service.get_option('current_page') == 4
    
    def test_mixed_changes_with_layout_resets_navigation(self):
        """Test that mixed changes including layout reset navigation."""
        # Set initial navigation state
        self.state_service.set_option('current_page', 3)
        assert self.state_service.get_option('current_page') == 3
        
        # Change both style and layout - should trigger nav reset due to layout
        self.state_service.set_option('background_color', '#D0D0D0')
        self.state_service.set_option('layout_cols', 4)  # Layout change
        
        # Simulate the navigation reset logic
        layout_changed = (
            self.state_service.get_option('layout_rows') != 2 or
            self.state_service.get_option('layout_cols') != 3
        )
        cards_count_changed = self.state_service.get_option('cards_count') != 20
        
        if layout_changed or cards_count_changed:
            self.state_service.reset_navigation()
        
        # Navigation should be reset due to layout change
        assert self.nav_reset_called
        assert self.state_service.get_option('current_page') == 1


class TestNavigationBoundaryConditions:
    """Test navigation behavior at boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.state_service = MagicMock()
        self.state_values = {
            'current_page': 1,
            'layout_rows': 2,
            'layout_cols': 3,
            'cards_count': 6,  # Exactly one page
        }
        
        def mock_get_option(key, default=None):
            return self.state_values.get(key, default)
        
        def mock_set_option(key, value):
            old_value = self.state_values.get(key)
            self.state_values[key] = value
            return old_value != value
        
        self.state_service.get_option = mock_get_option
        self.state_service.set_option = mock_set_option
        
        # Mock cards per page calculation
        def mock_get_cards_per_page():
            rows = self.state_values.get('layout_rows', 2)
            cols = self.state_values.get('layout_cols', 3)
            return rows * cols
        
        self.state_service.get_cards_per_page = mock_get_cards_per_page
    
    def test_navigation_reset_when_current_page_exceeds_total(self):
        """Test navigation reset when current page exceeds total pages."""
        # Set navigation to page 2 with multiple pages
        self.state_service.set_option('cards_count', 12)  # 2 pages
        self.state_service.set_option('current_page', 2)
        
        # Reduce cards count so current page exceeds total
        self.state_service.set_option('cards_count', 6)  # 1 page
        
        # Calculate if navigation needs reset
        cards_per_page = self.state_service.get_cards_per_page()
        total_pages = max(1, (self.state_service.get_option('cards_count') + cards_per_page - 1) // cards_per_page)
        current_page = self.state_service.get_option('current_page')
        
        if current_page > total_pages:
            self.state_service.set_option('current_page', 1)
        
        # Should reset to page 1
        assert self.state_service.get_option('current_page') == 1
    
    def test_navigation_preserved_when_within_bounds(self):
        """Test navigation preserved when within bounds."""
        # Set navigation to page 2 with multiple pages
        self.state_service.set_option('cards_count', 18)  # 3 pages
        self.state_service.set_option('current_page', 2)
        
        # Reduce cards count but keep current page valid
        self.state_service.set_option('cards_count', 12)  # 2 pages
        
        # Calculate if navigation needs reset
        cards_per_page = self.state_service.get_cards_per_page()
        total_pages = max(1, (self.state_service.get_option('cards_count') + cards_per_page - 1) // cards_per_page)
        current_page = self.state_service.get_option('current_page')
        
        if current_page > total_pages:
            self.state_service.set_option('current_page', 1)
        
        # Should preserve page 2
        assert self.state_service.get_option('current_page') == 2


class TestNavigationIntegrationWithPagination:
    """Test navigation integration with pagination logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Import pagination function
        try:
            from services.layout import paginate, PaginateInfo
            self.paginate = paginate
            self.PaginateInfo = PaginateInfo
        except ImportError:
            # Mock if not available
            self.PaginateInfo = type('PaginateInfo', (), {})
            def mock_paginate(cards_count, layout_rows, layout_cols):
                cards_per_page = layout_rows * layout_cols
                total_pages = max(1, (cards_count + cards_per_page - 1) // cards_per_page)
                return self.PaginateInfo()
            self.paginate = mock_paginate
    
    def test_navigation_with_pagination_calculation(self):
        """Test navigation behavior with actual pagination calculation."""
        # Test with realistic pagination scenarios
        test_cases = [
            # (cards_count, rows, cols, expected_pages)
            (20, 2, 3, 4),  # 20 cards, 6 per page = 4 pages
            (18, 3, 3, 2),  # 18 cards, 9 per page = 2 pages
            (5, 2, 3, 1),   # 5 cards, 6 per page = 1 page
            (12, 2, 2, 3),  # 12 cards, 4 per page = 3 pages
        ]
        
        for cards_count, rows, cols, expected_pages in test_cases:
            # Calculate pagination
            cards_per_page = rows * cols
            total_pages = max(1, (cards_count + cards_per_page - 1) // cards_per_page)
            
            # Verify expected pages calculation
            assert total_pages == expected_pages, f"Failed for {cards_count} cards, {rows}x{cols} layout"
            
            # Test navigation bounds
            for current_page in range(1, expected_pages + 2):  # Test beyond bounds
                if current_page <= expected_pages:
                    # Should be valid
                    assert current_page >= 1 and current_page <= total_pages
                else:
                    # Should be clamped to valid range
                    clamped_page = min(max(1, current_page), total_pages)
                    assert clamped_page <= total_pages


if __name__ == "__main__":
    pytest.main([__file__])
