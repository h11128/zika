"""
Unit tests for normalize/rounding functions.
Tests normalization and rounding behavior for stable digest computation.
"""

import pytest
import math
from decimal import Decimal
from typing import Any, Dict, List

# Import the functions to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import from the main ui.state module (not the package)
import importlib.util
spec = importlib.util.spec_from_file_location("ui_state", os.path.join(os.path.dirname(__file__), '..', '..', 'ui', 'state.py'))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)

normalize_for_digest = ui_state_module.normalize_for_digest
stable_digest = ui_state_module.stable_digest


class TestNormalizeForDigest:
    """Test normalize_for_digest function."""
    
    def test_normalize_dict_key_sorting(self):
        """Test that dict keys are sorted for stable normalization."""
        data = {'z': 1, 'a': 2, 'b': 3}
        normalized = normalize_for_digest(data)
        
        assert list(normalized.keys()) == ['a', 'b', 'z']
        assert normalized == {'a': 2, 'b': 3, 'z': 1}
    
    def test_normalize_nested_dict(self):
        """Test normalization of nested dictionaries."""
        data = {
            'outer': {'z': 1, 'a': 2},
            'simple': 'value'
        }
        normalized = normalize_for_digest(data)
        
        assert list(normalized.keys()) == ['outer', 'simple']
        assert list(normalized['outer'].keys()) == ['a', 'z']
    
    def test_normalize_list_preservation(self):
        """Test that list order is preserved."""
        data = [3, 1, 2]
        normalized = normalize_for_digest(data)
        
        assert normalized == [3, 1, 2]  # Order preserved
    
    def test_normalize_set_sorting(self):
        """Test that sets are converted to sorted lists."""
        data = {3, 1, 2}
        normalized = normalize_for_digest(data)
        
        assert normalized == [1, 2, 3]  # Sorted
    
    def test_normalize_float_rounding(self):
        """Test float rounding to 4 decimal places."""
        test_cases = [
            (1.23456789, 1.2346),
            (0.00001234, 0.0000),
            (999.99999, 1000.0000),
            (1.0, 1.0),
            (1.1, 1.1),
            (1.12345, 1.1235),
        ]
        
        for input_val, expected in test_cases:
            normalized = normalize_for_digest(input_val)
            assert normalized == expected, f"Failed for {input_val}: got {normalized}, expected {expected}"
    
    def test_normalize_float_edge_cases(self):
        """Test float normalization edge cases."""
        # Test very small numbers
        assert normalize_for_digest(1e-10) == 0.0
        
        # Test infinity and NaN
        assert normalize_for_digest(float('inf')) == float('inf')
        assert math.isnan(normalize_for_digest(float('nan')))
        
        # Test negative numbers
        assert normalize_for_digest(-1.23456) == -1.2346
    
    def test_normalize_mixed_types(self):
        """Test normalization of mixed data types."""
        data = {
            'string': 'hello',
            'int': 42,
            'float': 3.14159,
            'bool': True,
            'none': None,
            'list': [1, 2.5, 'three'],
            'dict': {'nested': 1.23456}
        }
        
        normalized = normalize_for_digest(data)
        
        assert normalized['string'] == 'hello'
        assert normalized['int'] == 42
        assert normalized['float'] == 3.1416
        assert normalized['bool'] is True
        assert normalized['none'] is None
        assert normalized['list'] == [1, 2.5, 'three']
        assert normalized['dict']['nested'] == 1.2346
    
    def test_normalize_dataclass_like_object(self):
        """Test normalization of objects with __dict__."""
        class TestObject:
            def __init__(self):
                self.z_attr = 1.23456
                self.a_attr = 'value'
        
        obj = TestObject()
        normalized = normalize_for_digest(obj)
        
        # Should normalize the __dict__
        assert isinstance(normalized, dict)
        assert list(normalized.keys()) == ['a_attr', 'z_attr']
        assert normalized['z_attr'] == 1.2346
        assert normalized['a_attr'] == 'value'
    
    def test_normalize_complex_nested_structure(self):
        """Test normalization of complex nested structures."""
        data = {
            'level1': {
                'z': [3.14159, 2.71828],
                'a': {
                    'nested': {1.23456, 9.87654},
                    'simple': 'value'
                }
            },
            'level2': [
                {'b': 1.11111, 'a': 2.22222},
                {'d': 3.33333, 'c': 4.44444}
            ]
        }
        
        normalized = normalize_for_digest(data)
        
        # Check structure is preserved but normalized
        assert list(normalized.keys()) == ['level1', 'level2']
        assert list(normalized['level1'].keys()) == ['a', 'z']
        assert normalized['level1']['z'] == [3.1416, 2.7183]
        assert normalized['level1']['a']['nested'] == [1.2346, 9.8765]
        
        # Check list of dicts is normalized
        assert list(normalized['level2'][0].keys()) == ['a', 'b']
        assert normalized['level2'][0]['b'] == 1.1111


class TestStableDigest:
    """Test stable_digest function."""
    
    def test_digest_deterministic(self):
        """Test that digest is deterministic for same input."""
        data = {'key': 'value', 'number': 1.23456}
        
        digest1 = stable_digest(data)
        digest2 = stable_digest(data)
        
        assert digest1 == digest2
        assert isinstance(digest1, str)
        assert len(digest1) == 16  # Truncated SHA256
    
    def test_digest_different_for_different_input(self):
        """Test that different inputs produce different digests."""
        data1 = {'key': 'value1'}
        data2 = {'key': 'value2'}
        
        digest1 = stable_digest(data1)
        digest2 = stable_digest(data2)
        
        assert digest1 != digest2
    
    def test_digest_order_independent(self):
        """Test that dict key order doesn't affect digest."""
        data1 = {'a': 1, 'b': 2, 'c': 3}
        data2 = {'c': 3, 'a': 1, 'b': 2}
        
        digest1 = stable_digest(data1)
        digest2 = stable_digest(data2)
        
        assert digest1 == digest2
    
    def test_digest_float_precision_stable(self):
        """Test that float precision differences are normalized."""
        data1 = {'value': 1.23456789}
        data2 = {'value': 1.2345678901}  # More precision
        
        digest1 = stable_digest(data1)
        digest2 = stable_digest(data2)
        
        assert digest1 == digest2  # Should be same after rounding
    
    def test_digest_complex_structure(self):
        """Test digest of complex nested structure."""
        data = {
            'layout': {
                'rows': 2,
                'cols': 3,
                'size': 5.1234
            },
            'style': {
                'colors': ['#FF0000', '#00FF00'],
                'fonts': {'hanzi': 'SimHei', 'english': 'Arial'}
            }
        }
        
        digest = stable_digest(data)
        
        assert isinstance(digest, str)
        assert len(digest) == 16
        
        # Should be reproducible
        assert digest == stable_digest(data)


class TestRoundingBehavior:
    """Test specific rounding behavior for layout calculations."""
    
    def test_layout_dimension_rounding(self):
        """Test rounding behavior for layout dimensions."""
        # Test cases that might occur in layout calculations
        test_cases = [
            # (input, expected_rounded)
            (5.0000001, 5.0000),  # Very small difference
            (5.9999999, 6.0000),  # Almost 6
            (0.33333333, 0.3333),  # Repeating decimal
            (1.0/3.0, 0.3333),    # Division result
            (2.0/3.0, 0.6667),    # Division result
        ]
        
        for input_val, expected in test_cases:
            normalized = normalize_for_digest(input_val)
            assert normalized == expected, f"Failed for {input_val}: got {normalized}, expected {expected}"
    
    def test_card_size_calculation_stability(self):
        """Test that card size calculations produce stable digests."""
        # Simulate card size calculation results
        page_width = 21.0  # A4 width
        margin = 1.0
        gap = 0.5
        cols = 3
        
        # Calculate available width
        available_width = page_width - 2 * margin
        card_width = (available_width - (cols - 1) * gap) / cols
        
        # This should produce a stable digest
        layout_data = {
            'card_width': card_width,
            'available_width': available_width,
            'page_width': page_width
        }
        
        digest1 = stable_digest(layout_data)
        digest2 = stable_digest(layout_data)
        
        assert digest1 == digest2
    
    def test_font_size_normalization(self):
        """Test font size normalization for consistent hashing."""
        # Font sizes that might come from different sources
        font_sizes = {
            'hanzi_pt': 48.0,
            'pinyin_pt': 18.0,
            'english_pt': 14.0,
            'calculated_px': 64.0000001  # Might have tiny precision errors
        }
        
        normalized = normalize_for_digest(font_sizes)
        
        assert normalized['calculated_px'] == 64.0000
        
        # Should produce stable digest
        digest = stable_digest(normalized)
        assert isinstance(digest, str)
        assert len(digest) == 16


class TestNormalizationEdgeCases:
    """Test edge cases in normalization."""
    
    def test_empty_structures(self):
        """Test normalization of empty structures."""
        assert normalize_for_digest({}) == {}
        assert normalize_for_digest([]) == []
        assert normalize_for_digest(set()) == []
    
    def test_none_values(self):
        """Test handling of None values."""
        data = {'key': None, 'other': 'value'}
        normalized = normalize_for_digest(data)
        
        assert normalized['key'] is None
        assert normalized['other'] == 'value'
    
    def test_boolean_values(self):
        """Test handling of boolean values."""
        data = {'true_val': True, 'false_val': False}
        normalized = normalize_for_digest(data)
        
        assert normalized['true_val'] is True
        assert normalized['false_val'] is False
    
    def test_string_values(self):
        """Test handling of string values."""
        data = {'empty': '', 'normal': 'hello', 'unicode': '你好'}
        normalized = normalize_for_digest(data)
        
        assert normalized['empty'] == ''
        assert normalized['normal'] == 'hello'
        assert normalized['unicode'] == '你好'
    
    def test_numeric_edge_cases(self):
        """Test numeric edge cases."""
        data = {
            'zero': 0,
            'negative_zero': -0.0,
            'small_positive': 1e-10,
            'small_negative': -1e-10,
            'large_number': 1e10
        }
        
        normalized = normalize_for_digest(data)
        
        assert normalized['zero'] == 0
        assert normalized['negative_zero'] == 0.0
        assert normalized['small_positive'] == 0.0  # Rounded to 0
        assert normalized['small_negative'] == 0.0   # Rounded to 0
        assert normalized['large_number'] == 1e10


if __name__ == "__main__":
    pytest.main([__file__])
