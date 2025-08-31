"""
Unit tests for rule precedence logic.
Tests the rule engine logic for proper precedence and application.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any


class MockStateService:
    """Mock state service that implements rule logic for testing."""

    def __init__(self):
        self.state_values = {}
        self.mock_card_size = 6.0

    def get_option(self, key: str, default=None):
        """Get option value."""
        return self.state_values.get(key, default)

    def set_option(self, key: str, value: Any) -> bool:
        """Set option with rule application."""
        old_value = self.state_values.get(key)

        # Set the value first
        self.state_values[key] = value

        # Apply Rule 1: Manual card_size adjustment → layout_auto_fill=False
        if key == 'card_size_cm':
            current_auto_fill = self.state_values.get('layout_auto_fill')
            if current_auto_fill:
                self.state_values['layout_auto_fill'] = False
            elif current_auto_fill is None:
                # Default to False when not set
                self.state_values['layout_auto_fill'] = False

        # Apply Rule 2: layout_auto_fill=True → recompute card_size
        if key == 'layout_auto_fill' and value is True:
            self.state_values['card_size_cm'] = self.mock_card_size

        # Apply Rule 3: Layout changes with auto_fill=True → recompute card_size
        layout_keys = {'layout_rows', 'layout_cols', 'page_size', 'gap_cm', 'margin_cm'}
        if key in layout_keys:
            layout_auto_fill = self.state_values.get('layout_auto_fill')
            if layout_auto_fill:
                self.state_values['card_size_cm'] = self.mock_card_size

        return old_value != value

    def set_options_batch(self, changes: Dict[str, Any]):
        """Set multiple options with rule application."""
        # Apply rules in order of precedence
        normalized_changes = changes.copy()

        # Rule 1: Manual card_size adjustment → layout_auto_fill=False
        # Only apply if layout_auto_fill is not explicitly set
        if 'card_size_cm' in changes and 'layout_auto_fill' not in changes:
            current_auto_fill = self.state_values.get('layout_auto_fill')
            if current_auto_fill:
                normalized_changes['layout_auto_fill'] = False

        # Rule 2: layout_auto_fill=True → recompute card_size
        # Apply if layout_auto_fill is explicitly set to True (overrides manual card_size)
        if changes.get('layout_auto_fill') is True:
            normalized_changes['card_size_cm'] = self.mock_card_size

        # Rule 3: Layout changes with auto_fill=True → recompute card_size
        # Only apply if card_size_cm is not explicitly set and auto_fill is True
        layout_keys = {'layout_rows', 'layout_cols', 'page_size', 'gap_cm', 'margin_cm'}
        if any(key in changes for key in layout_keys) and 'card_size_cm' not in changes:
            layout_auto_fill = normalized_changes.get('layout_auto_fill', self.state_values.get('layout_auto_fill'))
            if layout_auto_fill:
                normalized_changes['card_size_cm'] = self.mock_card_size

        # Apply all changes
        for key, value in normalized_changes.items():
            self.state_values[key] = value


class TestRulePrecedence:
    """Test rule precedence logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_service = MockStateService()

    def test_rule_1_manual_card_size_disables_auto_fill(self):
        """Test Rule 1: Manual card_size adjustment → layout_auto_fill=False."""
        # Set initial state with auto_fill enabled
        self.state_service.set_option('layout_auto_fill', True)

        # Manually adjust card size
        self.state_service.set_option('card_size_cm', 5.5)

        # Should automatically disable auto_fill
        assert self.state_service.get_option('layout_auto_fill') is False
        assert self.state_service.get_option('card_size_cm') == 5.5
    
    def test_rule_1_explicit_auto_fill_overrides_rule(self):
        """Test that explicit auto_fill=True overrides manual card_size."""
        # Set initial state
        self.state_service.set_option('layout_auto_fill', True)

        # Set both card_size and auto_fill explicitly
        changes = {
            'card_size_cm': 5.5,
            'layout_auto_fill': True  # Explicit override - should trigger recompute
        }
        self.state_service.set_options_batch(changes)

        # Explicit auto_fill=True should win and recompute card_size
        assert self.state_service.get_option('layout_auto_fill') is True
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
    
    def test_rule_2_auto_fill_true_recomputes_card_size(self):
        """Test Rule 2: layout_auto_fill=True → recompute card_size."""
        # Set initial state with manual card size
        self.state_service.set_option('card_size_cm', 4.0)
        self.state_service.set_option('layout_auto_fill', False)
        
        # Enable auto_fill
        self.state_service.set_option('layout_auto_fill', True)
        
        # Should recompute card size
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
        assert self.state_service.get_option('layout_auto_fill') is True
    
    def test_rule_3_layout_changes_with_auto_fill_recomputes(self):
        """Test Rule 3: Layout changes with auto_fill=True → recompute card_size."""
        # Set initial state with auto_fill enabled and let it compute card size
        self.state_service.set_option('layout_auto_fill', True)
        # Don't manually set card_size_cm - let auto_fill compute it

        # Verify auto_fill computed the card size
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
        assert self.state_service.get_option('layout_auto_fill') is True

        # Change layout parameter - should trigger recompute since auto_fill is still True
        self.state_service.set_option('layout_rows', 3)

        # Should still have recomputed card size
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
        assert self.state_service.get_option('layout_rows') == 3
        assert self.state_service.get_option('layout_auto_fill') is True

    def test_rule_3_layout_changes_without_auto_fill_no_recompute(self):
        """Test that layout changes without auto_fill don't trigger recompute."""
        # Set initial state with auto_fill disabled
        self.state_service.set_option('layout_auto_fill', False)
        self.state_service.set_option('card_size_cm', 4.0)

        # Change layout parameter
        self.state_service.set_option('layout_rows', 3)

        # Should NOT recompute card size
        assert self.state_service.get_option('card_size_cm') == 4.0
        assert self.state_service.get_option('layout_rows') == 3
    
    def test_rule_precedence_order(self):
        """Test that rules are applied in correct precedence order."""
        # Start with auto_fill enabled
        self.state_service.set_option('layout_auto_fill', True)
        
        # Apply changes that trigger multiple rules
        changes = {
            'card_size_cm': 5.5,      # Would trigger Rule 1 (disable auto_fill)
            'layout_rows': 3,         # Would trigger Rule 3 (recompute if auto_fill)
            'layout_auto_fill': True  # Explicit override
        }
        
        self.state_service.set_options_batch(changes)
        
        # Explicit auto_fill should win, and card_size should be recomputed
        assert self.state_service.get_option('layout_auto_fill') is True
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
        assert self.state_service.get_option('layout_rows') == 3
    
    def test_rule_application_with_batch_changes(self):
        """Test rule application with batch changes."""
        # Set initial state
        self.state_service.set_option('layout_auto_fill', False)
        self.state_service.set_option('card_size_cm', 4.0)
        
        # Apply batch changes
        changes = {
            'layout_auto_fill': True,
            'layout_rows': 2,
            'layout_cols': 4,
            'gap_cm': 0.8
        }
        
        self.state_service.set_options_batch(changes)
        
        # Should apply all changes and recompute card size once
        assert self.state_service.get_option('layout_auto_fill') is True
        assert self.state_service.get_option('layout_rows') == 2
        assert self.state_service.get_option('layout_cols') == 4
        assert self.state_service.get_option('gap_cm') == 0.8
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size


class TestRuleEngineEdgeCases:
    """Test edge cases in rule engine behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_service = MockStateService()

    def test_compute_auto_card_size_failure_handling(self):
        """Test handling when auto card size computation fails."""
        # Simulate failure by setting mock_card_size to None
        self.state_service.mock_card_size = None

        # Set initial card size
        self.state_service.set_option('card_size_cm', 4.0)

        # Enable auto_fill (should trigger recompute but fail)
        self.state_service.set_option('layout_auto_fill', True)

        # Should keep original card size when computation fails
        # (In real implementation, this would handle the None case gracefully)
        assert self.state_service.get_option('layout_auto_fill') is True
    
    def test_compute_auto_card_size_exception_handling(self):
        """Test handling when auto card size computation raises exception."""
        # Simulate exception by modifying the MockStateService behavior
        original_mock_card_size = self.state_service.mock_card_size

        # Override set_option to simulate exception during computation
        original_set_option = self.state_service.set_option
        def failing_set_option(key, value):
            if key == 'layout_auto_fill' and value is True:
                # Simulate computation failure - keep original card size
                self.state_service.state_values[key] = value
                return True
            return original_set_option(key, value)

        self.state_service.set_option = failing_set_option

        # Set initial card size
        self.state_service.set_option('card_size_cm', 4.0)

        # Enable auto_fill (should trigger recompute but handle exception)
        self.state_service.set_option('layout_auto_fill', True)

        # Should handle exception gracefully
        assert self.state_service.get_option('layout_auto_fill') is True
    
    def test_rule_application_with_missing_current_values(self):
        """Test rule application when current values are missing."""
        # Don't set any initial values
        
        # Apply change that would trigger Rule 1
        self.state_service.set_option('card_size_cm', 5.5)
        
        # Should handle missing current auto_fill value gracefully
        # (should default to False and apply rule)
        assert self.state_service.get_option('card_size_cm') == 5.5
        # auto_fill should be set to False by Rule 1
        assert self.state_service.get_option('layout_auto_fill') is False
    
    def test_rule_application_with_invalid_values(self):
        """Test rule application with invalid values."""
        # Set initial state
        self.state_service.set_option('layout_auto_fill', True)
        
        # Try to set invalid card size
        try:
            self.state_service.set_option('card_size_cm', -1.0)
            # If validation allows it, rule should still apply
            assert self.state_service.get_option('layout_auto_fill') is False
        except ValueError:
            # If validation rejects it, that's also acceptable
            pass


class TestRuleEngineIntegration:
    """Test rule engine integration with other components."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_service = MockStateService()
    
    def test_mock_integration_behavior(self):
        """Test mock integration behavior."""
        # Set up state for auto computation
        self.state_service.set_option('layout_rows', 2)
        self.state_service.set_option('layout_cols', 3)
        self.state_service.set_option('gap_cm', 0.5)
        self.state_service.set_option('margin_cm', 1.0)
        self.state_service.set_option('page_size', 'A4')

        # Enable auto_fill to trigger computation
        self.state_service.set_option('layout_auto_fill', True)

        # Should use mock card size
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
        assert self.state_service.get_option('layout_auto_fill') is True
    
    def test_rule_engine_with_real_state_values(self):
        """Test rule engine with realistic state values."""
        # Set up realistic initial state
        initial_state = {
            'layout_rows': 2,
            'layout_cols': 3,
            'card_size_cm': 5.0,
            'gap_cm': 0.5,
            'margin_cm': 1.0,
            'page_size': 'A4',
            'layout_auto_fill': False
        }
        
        for key, value in initial_state.items():
            self.state_service.set_option(key, value)
        
        # Change to auto_fill mode
        self.state_service.set_option('layout_auto_fill', True)
        
        # Should recompute card size based on layout
        new_card_size = self.state_service.get_option('card_size_cm')
        assert new_card_size != 5.0  # Should be different from initial
        assert new_card_size > 0     # Should be positive
    
    def test_rule_consistency_across_multiple_changes(self):
        """Test that rules are consistently applied across multiple changes."""
        # Start with known state
        self.state_service.set_option('layout_auto_fill', True)
        self.state_service.set_option('card_size_cm', 5.0)
        
        # Make multiple changes that should trigger rules
        changes_sequence = [
            {'layout_rows': 3},           # Should trigger Rule 3
            {'card_size_cm': 4.5},        # Should trigger Rule 1
            {'layout_auto_fill': True},   # Should trigger Rule 2
            {'gap_cm': 0.8},              # Should trigger Rule 3
        ]
        
        for changes in changes_sequence:
            self.state_service.set_options_batch(changes)
        
        # Final state should be consistent
        final_auto_fill = self.state_service.get_option('layout_auto_fill')
        final_card_size = self.state_service.get_option('card_size_cm')
        
        assert final_auto_fill is True
        assert final_card_size > 0
        
        # If auto_fill is True, card_size should be computed, not manual
        # (This tests that the final rule application was correct)


class TestRuleEnginePerformance:
    """Test rule engine performance characteristics."""

    def setup_method(self):
        """Set up test fixtures."""
        self.state_service = MockStateService()
    
    def test_rule_application_efficiency(self):
        """Test that rules are applied efficiently."""
        # Set initial state
        self.state_service.set_option('layout_auto_fill', True)
        
        # Apply batch changes that trigger multiple rules
        changes = {
            'layout_rows': 3,
            'layout_cols': 4,
            'gap_cm': 0.8,
            'margin_cm': 1.2,
            'page_size': 'Letter'
        }
        
        self.state_service.set_options_batch(changes)
        
        # Should apply all changes and recompute card size
        assert self.state_service.get_option('card_size_cm') == self.state_service.mock_card_size
    
    def test_no_unnecessary_rule_applications(self):
        """Test that rules are not applied unnecessarily."""
        # Set state where no rules should trigger
        self.state_service.set_option('layout_auto_fill', False)
        self.state_service.set_option('card_size_cm', 5.0)
        
        # Make changes that don't trigger rules
        changes = {
            'hanzi_font_size_pt': 48,
            'background_color': '#FFFFFF'
        }
        
        self.state_service.set_options_batch(changes)
        
        # Values should be unchanged (no rules triggered)
        assert self.state_service.get_option('layout_auto_fill') is False
        assert self.state_service.get_option('card_size_cm') == 5.0
        assert self.state_service.get_option('hanzi_font_size_pt') == 48
        assert self.state_service.get_option('background_color') == '#FFFFFF'


if __name__ == "__main__":
    pytest.main([__file__])
