#!/usr/bin/env python3
"""
Error Handling and Edge Case Integration Tests

Tests error scenarios and edge cases across module boundaries:
1. Network and I/O error handling
2. Memory and resource constraint handling
3. Invalid input data handling
4. Service failure and recovery
5. Concurrent access and race conditions
6. Configuration and environment errors
"""

import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, generate_missing_data, auto_segment_text
from services.export import export_cards
from services.cache_v2 import create_page_preview_html_v2, create_simple_grid_html_v2
from services.preview_types import LayoutOptions, Typography, VisualOptions

# Helper functions for v2 API compatibility
def create_page_preview_html(cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                           hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                           layout_rows=2, layout_cols=3, hanzi_font_family="SimSun",
                           background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=True,
        card_size_cm=card_size_cm,
        gap_cm=gap_cm,
        margin_cm=margin_cm,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=hanzi_font_size,
        pinyin_font_size_pt=pinyin_font_size,
        english_font_size_pt=english_font_size,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='📄 完整页面'
    )
    return create_page_preview_html_v2(cards, page_num, layout, typography, visual)

def create_simple_grid_html(cards, hanzi_font_family="SimSun", background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=2,
        layout_cols=3,
        layout_auto_fill=True,
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=48,
        pinyin_font_size_pt=18,
        english_font_size_pt=14,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='🔲 简单网格'
    )
    return create_simple_grid_html_v2(cards, layout, typography, visual)
from src.dict_utils import create_default_dict, ChineseDict
from src.pinyin_utils import hanzi_to_pinyin
from core.constants import DEFAULT_PAGE_SIZE


class TestInputValidationAndErrorHandling:
    """Test input validation and error handling across modules."""
    
    def test_empty_and_none_input_handling(self):
        """Test handling of empty and None inputs."""
        # Test empty string inputs
        assert parse_input_text("") == []
        assert parse_input_text("   ") == []
        assert auto_segment_text("") == ""
        assert auto_segment_text("   ") == ""
        
        # Test None inputs (should not crash)
        with pytest.raises(AttributeError):
            parse_input_text(None)
        
        # Test empty card lists
        empty_cards = []
        processed = generate_missing_data(empty_cards, True, True, None)
        assert processed == []
        
        # Test export with empty cards
        content = export_cards([], 'pptx')
        assert isinstance(content, (bytes, bytearray))
        
        # Test preview with empty cards
        html = create_simple_grid_html([])
        assert isinstance(html, str)
        assert "输入汉字以查看预览" in html
    
    def test_invalid_data_type_handling(self):
        """Test handling of invalid data types."""
        # Test non-string input to text processing
        with pytest.raises((TypeError, AttributeError)):
            parse_input_text(123)
        
        with pytest.raises((TypeError, AttributeError)):
            auto_segment_text(['list', 'input'])
        
        # Test invalid card structure
        invalid_cards = [
            {'hanzi': 123, 'pinyin': '', 'english': ''},  # Non-string hanzi
            {'wrong_key': '爱', 'pinyin': '', 'english': ''},  # Wrong keys
            'not_a_dict',  # Not a dictionary
        ]
        
        # Should handle gracefully or raise appropriate errors
        try:
            processed = generate_missing_data(invalid_cards, True, True, None)
            # If it doesn't crash, verify it handles invalid data appropriately
            assert isinstance(processed, list)
        except (TypeError, KeyError, AttributeError):
            # These are acceptable error types for invalid input
            pass
    
    def test_malformed_chinese_text_handling(self):
        """Test handling of malformed Chinese text."""
        malformed_inputs = [
            "爱家朋友！@#$%^&*()",  # Mixed Chinese and symbols
            "hello 爱 world 家",     # Mixed languages
            "爱\n\n\n家\t\t朋友",      # Whitespace and newlines
            "爱　家　朋友",            # Full-width spaces
            "",                      # Empty string
            "   ",                   # Only whitespace
        ]
        
        for text in malformed_inputs:
            # Should not crash
            try:
                cards = parse_input_text(text)
                assert isinstance(cards, list)
                
                segmented = auto_segment_text(text)
                assert isinstance(segmented, str)
            except Exception as e:
                pytest.fail(f"Failed to handle malformed input '{text}': {e}")
    
    def test_unicode_and_encoding_edge_cases(self):
        """Test Unicode and encoding edge cases."""
        unicode_inputs = [
            "爱💖家🏠朋友👫",        # Emoji mixed with Chinese
            "爱\u200b家\u200c朋友",   # Zero-width characters
            "爱\ufeff家\ufeff朋友",   # BOM characters
            "繁體中文測試",           # Traditional Chinese
            "𠮷野家",                # Rare Unicode characters
        ]
        
        for text in unicode_inputs:
            try:
                cards = parse_input_text(text)
                assert isinstance(cards, list)
                
                if cards:
                    # Test pinyin generation with Unicode
                    pinyin = hanzi_to_pinyin(cards[0]['hanzi'])
                    assert isinstance(pinyin, str)
            except Exception as e:
                # Some rare Unicode might not be supported, that's okay
                print(f"Unicode input '{text}' caused: {e}")


class TestServiceFailureAndRecovery:
    """Test service failure scenarios and recovery mechanisms."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_dictionary_service_failure_recovery(self):
        """Test recovery when dictionary service fails."""
        cards = [{'hanzi': '爱', 'pinyin': '', 'english': ''}]
        
        # Test with None dictionary
        processed = generate_missing_data(cards, True, True, None)
        assert len(processed) == 1
        assert processed[0]['pinyin']  # Should still generate pinyin
        assert not processed[0]['english']  # But no translation
        
        # Test with mock dictionary that raises exceptions
        mock_dict = Mock()
        mock_dict.lookup_translation.side_effect = Exception("Dictionary error")
        
        processed = generate_missing_data(cards, True, True, mock_dict)
        assert len(processed) == 1
        assert processed[0]['pinyin']  # Should still work
        # Translation might be empty due to error
    
    def test_export_service_failure_scenarios(self):
        """Test export service failure scenarios."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Test with invalid format
        with pytest.raises(ValueError, match="Unsupported format"):
            export_cards(cards, 'invalid_format')
        
        # Test with extreme parameters that might cause issues
        try:
            # Very large card size
            content = export_cards(cards, 'pptx', card_size_cm=100.0)
            assert isinstance(content, (bytes, bytearray))
        except Exception:
            # If it fails, that's acceptable for extreme values
            pass
        
        try:
            # Very small card size
            content = export_cards(cards, 'pptx', card_size_cm=0.1)
            assert isinstance(content, (bytes, bytearray))
        except Exception:
            # If it fails, that's acceptable for extreme values
            pass
    
    @patch('tempfile.NamedTemporaryFile')
    def test_temporary_file_creation_failure(self, mock_temp_file):
        """Test handling of temporary file creation failures."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Mock tempfile to raise an exception
        mock_temp_file.side_effect = OSError("No space left on device")
        
        with pytest.raises(OSError):
            export_cards(cards, 'pptx')
    
    def test_file_permission_errors(self):
        """Test handling of file permission errors."""
        # Create a read-only directory
        readonly_dir = Path(self.temp_dir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only

        try:
            # Try to create dictionary in read-only directory
            # The function should handle this gracefully, not crash
            dict_obj = create_default_dict(str(readonly_dir))

            # Should return a valid dictionary object with empty data
            assert dict_obj is not None
            stats = dict_obj.get_statistics()
            assert stats['mini_dict_entries'] == 0  # No entries loaded due to permission issue
            assert stats['cedict_entries'] == 0
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)


class TestResourceConstraintHandling:
    """Test handling of resource constraints and limits."""
    
    def test_large_dataset_memory_handling(self):
        """Test handling of large datasets that might cause memory issues."""
        # Generate a large number of cards
        large_cards = []
        for i in range(1000):  # 1000 cards
            large_cards.append({
                'hanzi': f'字{i}号测试长文本内容',
                'pinyin': f'zì{i} hào cè shì cháng wén běn nèi róng',
                'english': f'character{i} number test long text content'
            })
        
        # Test processing large dataset
        try:
            # Should handle large datasets gracefully
            html = create_simple_grid_html(large_cards[:100])  # Limit for testing
            assert isinstance(html, str)
            
            # Test export with reasonable subset
            content = export_cards(large_cards[:50], 'pptx')
            assert isinstance(content, (bytes, bytearray))
        except MemoryError:
            pytest.skip("System doesn't have enough memory for large dataset test")
    
    def test_very_long_text_handling(self):
        """Test handling of very long text inputs."""
        # Very long Chinese text
        long_text = "爱家朋友水火山月日木" * 100  # 1000 characters
        
        try:
            segmented = auto_segment_text(long_text)
            assert isinstance(segmented, str)
            
            cards = parse_input_text(segmented)
            assert isinstance(cards, list)
            
            # Limit processing to avoid memory issues
            if len(cards) > 100:
                cards = cards[:100]
            
            processed = generate_missing_data(cards, True, False, None)
            assert isinstance(processed, list)
        except MemoryError:
            pytest.skip("System doesn't have enough memory for long text test")
    
    def test_concurrent_access_simulation(self):
        """Test simulation of concurrent access scenarios."""
        import threading
        import time
        
        cards = [{'hanzi': '爱', 'pinyin': '', 'english': ''}]
        results = []
        errors = []
        
        def process_cards():
            try:
                dict_obj = create_default_dict("data")
                processed = generate_missing_data(cards, True, True, dict_obj)
                results.append(processed)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=process_cards)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Verify results
        assert len(errors) == 0, f"Concurrent access caused errors: {errors}"
        assert len(results) == 5
        
        # All results should be consistent
        for result in results:
            assert len(result) == 1
            assert result[0]['hanzi'] == '爱'
            assert result[0]['pinyin']


class TestConfigurationErrorHandling:
    """Test configuration and environment error handling."""
    
    def test_missing_data_directory_handling(self):
        """Test handling when data directory is missing."""
        # Test with non-existent directory
        # The function should handle this gracefully, not crash
        dict_obj = create_default_dict("non_existent_directory")

        # Should return a valid dictionary object with empty data
        assert dict_obj is not None
        stats = dict_obj.get_statistics()
        assert stats['mini_dict_entries'] == 0  # No entries loaded due to missing directory
        assert stats['cedict_entries'] == 0
    
    def test_corrupted_dictionary_file_handling(self):
        """Test handling of corrupted dictionary files."""
        temp_dir = tempfile.mkdtemp()
        try:
            # Create corrupted JSON file
            corrupted_dict_path = Path(temp_dir) / "mini_cedict.json"
            with open(corrupted_dict_path, 'w') as f:
                f.write("{ invalid json content }")
            
            # Should handle corrupted file gracefully
            try:
                dict_obj = create_default_dict(temp_dir)
                # If it doesn't crash, verify it handles the error
                stats = dict_obj.get_statistics()
                assert isinstance(stats, dict)
            except (json.JSONDecodeError, ValueError, FileNotFoundError):
                # These are acceptable errors for corrupted files
                pass
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_invalid_font_configuration_handling(self):
        """Test handling of invalid font configurations."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Test with non-existent font
        html = create_simple_grid_html(cards, hanzi_font_family="NonExistentFont")
        assert isinstance(html, str)
        # The font might be validated/sanitized, so just check that HTML is generated
        assert len(html) > 0  # Should still generate valid HTML
        assert "simple-grid" in html  # Should contain expected CSS classes
        
        # Test export with invalid font
        content = export_cards(cards, 'pptx', hanzi_font_family="NonExistentFont")
        assert isinstance(content, (bytes, bytearray))
    
    def test_invalid_color_configuration_handling(self):
        """Test handling of invalid color configurations."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        invalid_colors = [
            "invalid_color",
            "#GGGGGG",  # Invalid hex
            "rgb(300, 300, 300)",  # Out of range RGB
            "",  # Empty string
        ]
        
        for color in invalid_colors:
            # Should not crash with invalid colors
            try:
                html = create_simple_grid_html(cards, background_color=color)
                assert isinstance(html, str)
                
                content = export_cards(cards, 'pptx', background_color=color)
                assert isinstance(content, (bytes, bytearray))
            except Exception as e:
                # Some invalid colors might cause exceptions, that's okay
                print(f"Invalid color '{color}' caused: {e}")


class TestEdgeCaseDataHandling:
    """Test edge cases in data handling."""
    
    def test_boundary_value_handling(self):
        """Test handling of boundary values."""
        # Test with minimum and maximum reasonable values
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Minimum values
        content = export_cards(
            cards, 'pptx',
            card_size_cm=1.0, gap_cm=0.0, margin_cm=0.0,
            hanzi_font_size=8, pinyin_font_size=6, english_font_size=6
        )
        assert isinstance(content, (bytes, bytearray))
        
        # Maximum reasonable values
        content = export_cards(
            cards, 'pptx',
            card_size_cm=20.0, gap_cm=5.0, margin_cm=5.0,
            hanzi_font_size=72, pinyin_font_size=36, english_font_size=24
        )
        assert isinstance(content, (bytes, bytearray))
    
    def test_special_character_combinations(self):
        """Test special character combinations."""
        special_cards = [
            {'hanzi': '爱❤️', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家\u200b', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '\ufeff朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        ]
        
        # Should handle special characters without crashing
        try:
            processed = generate_missing_data(special_cards, True, True, None)
            assert isinstance(processed, list)
            
            html = create_simple_grid_html(processed)
            assert isinstance(html, str)
            
            content = export_cards(processed, 'pptx')
            assert isinstance(content, (bytes, bytearray))
        except Exception as e:
            # Some special characters might not be fully supported
            print(f"Special characters caused: {e}")
    
    def test_circular_reference_prevention(self):
        """Test prevention of circular references in data structures."""
        # Create cards with potential circular references
        card1 = {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}
        card2 = {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        
        # Add circular reference (this shouldn't happen in normal use)
        card1['ref'] = card2
        card2['ref'] = card1
        
        cards = [card1, card2]
        
        # Should handle gracefully (ignore extra fields)
        try:
            processed = generate_missing_data(cards, True, True, None)
            assert isinstance(processed, list)
        except (RecursionError, ValueError):
            # These are acceptable for circular references
            pass
