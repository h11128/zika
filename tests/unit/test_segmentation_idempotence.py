"""
Unit tests for segmentation idempotence.
Tests that text segmentation operations are idempotent and produce consistent results.
"""

import pytest
from services.processing import auto_segment_text, parse_input_text


class TestSegmentationIdempotence:
    """Test that segmentation operations are idempotent."""
    
    def test_auto_segment_text_idempotent(self):
        """Test that auto_segment_text is idempotent."""
        # Original text with mixed content
        original_text = "你好世界学习中文编程很有趣"
        
        # First segmentation
        segmented_once = auto_segment_text(original_text)
        
        # Second segmentation of the result
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
    
    def test_auto_segment_text_with_spaces_idempotent(self):
        """Test idempotence with text that already has spaces."""
        # Text that's already segmented
        pre_segmented = "你好 世界 学习 中文"
        
        # Segmentation should not change it
        segmented = auto_segment_text(pre_segmented)
        
        # Should be identical or equivalent (normalized spacing)
        assert segmented == pre_segmented or segmented == "你好 世界 学习 中文"
    
    def test_auto_segment_text_with_punctuation_idempotent(self):
        """Test idempotence with punctuation."""
        # Text with punctuation
        text_with_punct = "你好，世界！学习中文。"
        
        # First segmentation
        segmented_once = auto_segment_text(text_with_punct)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
    
    def test_parse_input_text_idempotent(self):
        """Test that parse_input_text is idempotent for valid input."""
        # Space-separated Chinese text
        input_text = "你好 世界 学习 中文"
        
        # First parsing
        cards_once = parse_input_text(input_text)
        
        # Convert back to text and parse again
        reconstructed_text = " ".join(card['hanzi'] for card in cards_once)
        cards_twice = parse_input_text(reconstructed_text)
        
        # Should produce the same cards
        assert len(cards_once) == len(cards_twice)
        for card1, card2 in zip(cards_once, cards_twice):
            assert card1['hanzi'] == card2['hanzi']
    
    def test_segmentation_pipeline_idempotent(self):
        """Test that the full segmentation pipeline is idempotent."""
        # Original continuous text
        original_text = "你好世界学习中文编程很有趣"
        
        # Full pipeline: segment -> parse -> reconstruct -> segment -> parse
        segmented1 = auto_segment_text(original_text)
        cards1 = parse_input_text(segmented1)
        reconstructed = " ".join(card['hanzi'] for card in cards1)
        segmented2 = auto_segment_text(reconstructed)
        cards2 = parse_input_text(segmented2)
        
        # Final result should be the same as first iteration
        assert len(cards1) == len(cards2)
        for card1, card2 in zip(cards1, cards2):
            assert card1['hanzi'] == card2['hanzi']
    
    def test_empty_text_idempotent(self):
        """Test idempotence with empty text."""
        empty_text = ""
        
        segmented = auto_segment_text(empty_text)
        cards = parse_input_text(segmented)
        
        # Should handle empty input gracefully
        assert segmented == "" or segmented is None
        assert cards == []
    
    def test_whitespace_only_idempotent(self):
        """Test idempotence with whitespace-only text."""
        whitespace_text = "   \n\t  "
        
        segmented = auto_segment_text(whitespace_text)
        cards = parse_input_text(segmented)
        
        # Should handle whitespace gracefully
        assert cards == []
    
    def test_non_chinese_text_idempotent(self):
        """Test idempotence with non-Chinese text."""
        english_text = "hello world"
        
        # First segmentation
        segmented_once = auto_segment_text(english_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical (likely empty or unchanged)
        assert segmented_once == segmented_twice
    
    def test_mixed_language_idempotent(self):
        """Test idempotence with mixed language text."""
        mixed_text = "你好hello世界world"
        
        # First segmentation
        segmented_once = auto_segment_text(mixed_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice


class TestSegmentationConsistency:
    """Test consistency of segmentation results."""
    
    def test_segmentation_deterministic(self):
        """Test that segmentation is deterministic."""
        text = "你好世界学习中文"
        
        # Multiple segmentations should produce identical results
        results = [auto_segment_text(text) for _ in range(5)]
        
        # All results should be identical
        assert all(result == results[0] for result in results)
    
    def test_parsing_deterministic(self):
        """Test that parsing is deterministic."""
        text = "你好 世界 学习 中文"
        
        # Multiple parsings should produce identical results
        results = [parse_input_text(text) for _ in range(5)]
        
        # All results should be identical
        for i in range(1, len(results)):
            assert len(results[i]) == len(results[0])
            for j in range(len(results[i])):
                assert results[i][j]['hanzi'] == results[0][j]['hanzi']
    
    def test_order_preservation(self):
        """Test that segmentation preserves character order."""
        text = "一二三四五六七八九十"
        
        segmented = auto_segment_text(text)
        cards = parse_input_text(segmented)
        
        # Reconstruct the text
        reconstructed = "".join(card['hanzi'] for card in cards)
        
        # Should preserve the original character sequence
        # (allowing for potential filtering of non-Chinese characters)
        original_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
        reconstructed_chars = [c for c in reconstructed if '\u4e00' <= c <= '\u9fff']
        
        assert reconstructed_chars == original_chars
    
    def test_deduplication_consistency(self):
        """Test that deduplication is consistent."""
        # Text with duplicates
        text_with_dups = "你好你好世界世界学习学习"
        
        # Segment multiple times
        results = [auto_segment_text(text_with_dups) for _ in range(3)]
        
        # All should produce the same deduplication
        assert all(result == results[0] for result in results)
        
        # Parse and check for duplicates
        cards = parse_input_text(results[0])
        hanzi_list = [card['hanzi'] for card in cards]
        
        # Should not have duplicates (or have consistent duplicates)
        unique_hanzi = list(dict.fromkeys(hanzi_list))
        assert len(hanzi_list) == len(unique_hanzi) or hanzi_list == unique_hanzi


class TestSegmentationEdgeCases:
    """Test edge cases in segmentation."""
    
    def test_very_long_text_idempotent(self):
        """Test idempotence with very long text."""
        # Create a long text
        long_text = "你好世界学习中文编程很有趣" * 100
        
        # First segmentation
        segmented_once = auto_segment_text(long_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
    
    def test_single_character_idempotent(self):
        """Test idempotence with single character."""
        single_char = "你"
        
        # Multiple segmentations
        segmented_once = auto_segment_text(single_char)
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
        
        # Should parse to single card
        cards = parse_input_text(segmented_once)
        assert len(cards) == 1
        assert cards[0]['hanzi'] == "你"
    
    def test_special_characters_idempotent(self):
        """Test idempotence with special characters."""
        special_text = "你好！@#$%^&*()世界？？？"
        
        # First segmentation
        segmented_once = auto_segment_text(special_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
    
    def test_numbers_and_chinese_idempotent(self):
        """Test idempotence with numbers and Chinese."""
        mixed_text = "你好123世界456学习789"
        
        # First segmentation
        segmented_once = auto_segment_text(mixed_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice
    
    def test_unicode_edge_cases_idempotent(self):
        """Test idempotence with Unicode edge cases."""
        # Text with various Unicode ranges
        unicode_text = "你好🌍世界😊学习💻中文"
        
        # First segmentation
        segmented_once = auto_segment_text(unicode_text)
        
        # Second segmentation
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical
        assert segmented_once == segmented_twice


class TestSegmentationRobustness:
    """Test robustness of segmentation operations."""
    
    def test_malformed_input_handling(self):
        """Test handling of malformed input."""
        malformed_inputs = [
            None,
            123,
            [],
            {},
            "\x00\x01\x02",  # Control characters
        ]
        
        for malformed_input in malformed_inputs:
            try:
                # Should either handle gracefully or raise appropriate exception
                result = auto_segment_text(str(malformed_input) if malformed_input is not None else "")
                # If it doesn't raise an exception, result should be consistent
                if result is not None:
                    second_result = auto_segment_text(result)
                    assert result == second_result
            except (TypeError, ValueError, AttributeError):
                # These exceptions are acceptable for malformed input
                pass
    
    def test_encoding_consistency(self):
        """Test that different encodings produce consistent results."""
        # Same text in different representations
        text_utf8 = "你好世界"
        text_unicode = "\u4f60\u597d\u4e16\u754c"
        
        # Should produce the same segmentation
        segmented_utf8 = auto_segment_text(text_utf8)
        segmented_unicode = auto_segment_text(text_unicode)
        
        assert segmented_utf8 == segmented_unicode
    
    def test_normalization_idempotent(self):
        """Test that normalization is idempotent."""
        # Text that might need normalization
        text_with_variants = "你好　世界"  # Contains full-width space
        
        # Multiple segmentations
        segmented_once = auto_segment_text(text_with_variants)
        segmented_twice = auto_segment_text(segmented_once)
        
        # Should be identical after normalization
        assert segmented_once == segmented_twice


if __name__ == "__main__":
    pytest.main([__file__])
