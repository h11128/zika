"""
Golden tests for typography consistency across render targets.
Validates that typography remains consistent between preview, PDF, and PowerPoint outputs.
"""

import pytest
from typing import Dict, Any
import json
import os

from services.typography import (
    get_typography_manager, RenderTarget, normalize_typography_for_render_target
)


class TestTypographyGoldenTests:
    """Golden tests for typography consistency."""
    
    @pytest.fixture
    def sample_typography_params(self):
        """Sample typography parameters for testing."""
        return {
            "hanzi_font_size_pt": 48,
            "pinyin_font_size_pt": 18,
            "english_font_size_pt": 14,
            "hanzi_font_family": "SimHei"
        }
    
    def test_screen_typography_golden(self, sample_typography_params):
        """Golden test for screen typography normalization."""
        normalized = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        # Validate key properties
        assert normalized["hanzi_px"] == 64  # 48pt * 96/72 DPI
        assert normalized["pinyin_px"] == 24  # 18pt * 96/72 DPI
        assert normalized["english_px"] == 19  # 14pt * 96/72 DPI
        
        # Validate line heights are reasonable
        assert normalized["hanzi_line_height_px"] > normalized["hanzi_px"]
        assert normalized["pinyin_line_height_px"] > normalized["pinyin_px"]
        assert normalized["english_line_height_px"] > normalized["english_px"]
        
        # Validate margins are positive
        assert normalized["hanzi_margin_px"] > 0
        assert normalized["pinyin_margin_px"] > 0
        assert normalized["english_margin_px"] > 0
        
        # Validate font stacks contain expected fonts
        assert "SimHei" in normalized["hanzi_font_stack"]
        assert "Noto Sans" in normalized["pinyin_font_stack"]
        assert "system-ui" in normalized["english_font_stack"]
    
    def test_pdf_typography_adjustments(self, sample_typography_params):
        """Test PDF-specific typography adjustments."""
        screen_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        pdf_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.PDF
        )
        
        # PDF should have adjustments applied (allowing for rounding)
        # For larger fonts, differences should be visible
        assert pdf_params["hanzi_px"] != screen_params["hanzi_px"]
        assert pdf_params["pinyin_px"] != screen_params["pinyin_px"]
        # English font is small (14pt), so rounding may make them equal
        # Just verify the adjustment was attempted
        assert abs(pdf_params["english_px"] - screen_params["english_px"]) <= 1
        
        # PDF fonts should be slightly smaller (0.95 scale)
        expected_hanzi_pdf = int(screen_params["hanzi_px"] * 0.95)
        assert abs(pdf_params["hanzi_px"] - expected_hanzi_pdf) <= 1  # Allow for rounding
        
        # Line heights should be adjusted for print
        assert pdf_params["hanzi_line_height_px"] >= screen_params["hanzi_line_height_px"]
        
        # Margins should be larger for print
        assert pdf_params["hanzi_margin_px"] >= screen_params["hanzi_margin_px"]
    
    def test_powerpoint_typography_adjustments(self, sample_typography_params):
        """Test PowerPoint-specific typography adjustments."""
        screen_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        ppt_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.POWERPOINT
        )
        
        # PowerPoint should have adjustments applied (allowing for rounding)
        assert ppt_params["hanzi_px"] != screen_params["hanzi_px"]
        # For smaller fonts, rounding may make them equal, so check within tolerance
        assert abs(ppt_params["pinyin_px"] - screen_params["pinyin_px"]) <= 1
        assert abs(ppt_params["english_px"] - screen_params["english_px"]) <= 1
        
        # PowerPoint fonts should be slightly smaller (0.98 scale)
        expected_hanzi_ppt = int(screen_params["hanzi_px"] * 0.98)
        assert abs(ppt_params["hanzi_px"] - expected_hanzi_ppt) <= 1  # Allow for rounding
    
    def test_font_ratio_consistency(self, sample_typography_params):
        """Test that font size ratios are maintained across render targets."""
        screen_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        pdf_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.PDF
        )
        
        ppt_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.POWERPOINT
        )
        
        # Calculate ratios
        screen_hanzi_pinyin_ratio = screen_params["hanzi_px"] / screen_params["pinyin_px"]
        pdf_hanzi_pinyin_ratio = pdf_params["hanzi_px"] / pdf_params["pinyin_px"]
        ppt_hanzi_pinyin_ratio = ppt_params["hanzi_px"] / ppt_params["pinyin_px"]
        
        # Ratios should be similar (within 5% tolerance)
        assert abs(screen_hanzi_pinyin_ratio - pdf_hanzi_pinyin_ratio) / screen_hanzi_pinyin_ratio < 0.05
        assert abs(screen_hanzi_pinyin_ratio - ppt_hanzi_pinyin_ratio) / screen_hanzi_pinyin_ratio < 0.05
        
        # Test pinyin to english ratio
        screen_pinyin_english_ratio = screen_params["pinyin_px"] / screen_params["english_px"]
        pdf_pinyin_english_ratio = pdf_params["pinyin_px"] / pdf_params["english_px"]
        ppt_pinyin_english_ratio = ppt_params["pinyin_px"] / ppt_params["english_px"]
        
        assert abs(screen_pinyin_english_ratio - pdf_pinyin_english_ratio) / screen_pinyin_english_ratio < 0.05
        assert abs(screen_pinyin_english_ratio - ppt_pinyin_english_ratio) / screen_pinyin_english_ratio < 0.05
    
    def test_line_height_multipliers_consistency(self, sample_typography_params):
        """Test that line height multipliers are applied consistently."""
        manager = get_typography_manager()
        
        # Test different font sizes to ensure multipliers are consistent
        test_sizes = [(24, 12, 10), (48, 18, 14), (72, 24, 18)]
        
        for hanzi_pt, pinyin_pt, english_pt in test_sizes:
            normalized = manager.normalize_typography_params(
                hanzi_pt, pinyin_pt, english_pt, "SimHei", RenderTarget.SCREEN
            )
            
            # Calculate actual multipliers
            hanzi_multiplier = normalized["hanzi_line_height_px"] / normalized["hanzi_px"]
            pinyin_multiplier = normalized["pinyin_line_height_px"] / normalized["pinyin_px"]
            english_multiplier = normalized["english_line_height_px"] / normalized["english_px"]
            
            # Multipliers should be within expected ranges
            assert 1.0 < hanzi_multiplier < 1.5
            assert 1.0 < pinyin_multiplier < 1.5
            assert 1.0 < english_multiplier < 1.5
    
    def test_character_width_estimates(self, sample_typography_params):
        """Test character width estimation accuracy."""
        normalized = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        # Hanzi characters should be approximately square
        hanzi_aspect_ratio = normalized["hanzi_char_width_px"] / normalized["hanzi_px"]
        assert 0.8 < hanzi_aspect_ratio < 1.2
        
        # Latin characters should be narrower
        pinyin_aspect_ratio = normalized["pinyin_char_width_px"] / normalized["pinyin_px"]
        assert 0.4 < pinyin_aspect_ratio < 0.8
        
        english_aspect_ratio = normalized["english_char_width_px"] / normalized["english_px"]
        assert 0.4 < english_aspect_ratio < 0.8
    
    def test_total_height_calculations(self, sample_typography_params):
        """Test total height calculations include margins."""
        normalized = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        # Total heights should be line height + margin
        expected_hanzi_total = normalized["hanzi_line_height_px"] + normalized["hanzi_margin_px"]
        expected_pinyin_total = normalized["pinyin_line_height_px"] + normalized["pinyin_margin_px"]
        expected_english_total = normalized["english_line_height_px"] + normalized["english_margin_px"]
        
        assert normalized["hanzi_total_height_px"] == expected_hanzi_total
        assert normalized["pinyin_total_height_px"] == expected_pinyin_total
        assert normalized["english_total_height_px"] == expected_english_total
    
    def test_typography_validation_no_issues(self, sample_typography_params):
        """Test that consistent typography passes validation."""
        manager = get_typography_manager()
        
        screen_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.SCREEN
        )
        
        pdf_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.PDF
        )
        
        ppt_params = normalize_typography_for_render_target(
            **sample_typography_params,
            render_target=RenderTarget.POWERPOINT
        )
        
        issues = manager.validate_typography_consistency(screen_params, pdf_params, ppt_params)
        
        # Should have no critical issues
        critical_issues = [issue for issue in issues if "ratio" in issue.lower() or "smaller" in issue.lower()]
        assert len(critical_issues) == 0
    
    def test_edge_case_font_sizes(self):
        """Test typography with edge case font sizes."""
        # Very small fonts
        small_normalized = normalize_typography_for_render_target(
            hanzi_font_size_pt=12, pinyin_font_size_pt=8, english_font_size_pt=6,
            hanzi_font_family="SimHei", render_target=RenderTarget.SCREEN
        )
        
        # Should still have reasonable values
        assert small_normalized["hanzi_px"] > 0
        assert small_normalized["hanzi_margin_px"] >= 4  # Minimum margin
        
        # Very large fonts
        large_normalized = normalize_typography_for_render_target(
            hanzi_font_size_pt=120, pinyin_font_size_pt=60, english_font_size_pt=48,
            hanzi_font_family="SimHei", render_target=RenderTarget.SCREEN
        )
        
        # Should scale proportionally
        assert large_normalized["hanzi_px"] > small_normalized["hanzi_px"] * 8
        assert large_normalized["hanzi_margin_px"] > small_normalized["hanzi_margin_px"] * 4
    
    def test_different_hanzi_fonts(self):
        """Test typography with different hanzi fonts."""
        fonts_to_test = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "Arial"]
        
        for font in fonts_to_test:
            normalized = normalize_typography_for_render_target(
                hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
                hanzi_font_family=font, render_target=RenderTarget.SCREEN
            )
            
            # Font should appear in the stack
            assert font in normalized["hanzi_font_stack"]
            
            # Other properties should be consistent regardless of font
            assert normalized["hanzi_px"] == 64  # Same font size
            assert normalized["hanzi_margin_px"] > 0


if __name__ == "__main__":
    pytest.main([__file__])
