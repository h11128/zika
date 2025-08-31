"""
Unit tests for typography consistency system.
Tests font fallback matrix, measurement strategy, and renderer-specific adjustments.
"""

import pytest
from unittest.mock import patch
import math

from services.typography import (
    TypographyManager, FontType, RenderTarget, FontFallbackConfig,
    LineHeightConfig, TypographyMeasurement, get_typography_manager,
    normalize_typography_for_render_target
)


class TestFontFallbackConfig:
    """Test font fallback configuration."""
    
    def test_font_fallback_config_creation(self):
        """Test creating font fallback config."""
        config = FontFallbackConfig(
            primary="Noto Sans CJK SC",
            fallbacks=["Source Han Sans SC", "Microsoft YaHei"],
            system_fallback="sans-serif"
        )
        
        assert config.primary == "Noto Sans CJK SC"
        assert config.fallbacks == ["Source Han Sans SC", "Microsoft YaHei"]
        assert config.system_fallback == "sans-serif"
    
    def test_get_font_stack(self):
        """Test font stack generation."""
        config = FontFallbackConfig(
            primary="Noto Sans CJK SC",
            fallbacks=["Source Han Sans SC", "Microsoft YaHei"],
            system_fallback="sans-serif"
        )
        
        stack = config.get_font_stack()
        expected = "'Noto Sans CJK SC', 'Source Han Sans SC', 'Microsoft YaHei', sans-serif"
        assert stack == expected


class TestLineHeightConfig:
    """Test line height configuration."""
    
    def test_line_height_calculation(self):
        """Test line height calculation for different font types."""
        config = LineHeightConfig(
            hanzi_multiplier=1.1,
            pinyin_multiplier=1.2,
            english_multiplier=1.2,
            safety_padding_px=2
        )
        
        # Test hanzi line height
        hanzi_height = config.get_line_height_px(48, FontType.HANZI)
        expected_hanzi = math.ceil(48 * 1.1) + 2
        assert hanzi_height == expected_hanzi
        
        # Test pinyin line height
        pinyin_height = config.get_line_height_px(18, FontType.PINYIN)
        expected_pinyin = math.ceil(18 * 1.2) + 2
        assert pinyin_height == expected_pinyin
        
        # Test english line height
        english_height = config.get_line_height_px(14, FontType.ENGLISH)
        expected_english = math.ceil(14 * 1.2) + 2
        assert english_height == expected_english


class TestTypographyMeasurement:
    """Test typography measurement dataclass."""
    
    def test_typography_measurement_creation(self):
        """Test creating typography measurement."""
        measurement = TypographyMeasurement(
            font_size_px=48,
            line_height_px=55,
            char_width_px=48.0,
            margin_px=10,
            font_type=FontType.HANZI
        )
        
        assert measurement.font_size_px == 48
        assert measurement.line_height_px == 55
        assert measurement.char_width_px == 48.0
        assert measurement.margin_px == 10
        assert measurement.font_type == FontType.HANZI
    
    def test_effective_height_calculation(self):
        """Test effective height calculation."""
        measurement = TypographyMeasurement(
            font_size_px=48,
            line_height_px=55,
            char_width_px=48.0,
            margin_px=10,
            font_type=FontType.HANZI
        )
        
        assert measurement.effective_height_px == 65  # 55 + 10


class TestTypographyManager:
    """Test typography manager functionality."""
    
    def test_typography_manager_initialization(self):
        """Test typography manager initialization."""
        manager = TypographyManager()
        
        # Check font fallbacks are initialized
        assert FontType.HANZI in manager._font_fallbacks
        assert FontType.PINYIN in manager._font_fallbacks
        assert FontType.ENGLISH in manager._font_fallbacks
        
        # Check line height config is initialized
        assert manager._line_height_config is not None
        
        # Check render adjustments are initialized
        assert RenderTarget.SCREEN in manager._render_adjustments
        assert RenderTarget.PDF in manager._render_adjustments
        assert RenderTarget.POWERPOINT in manager._render_adjustments
    
    def test_get_font_stack_default(self):
        """Test getting default font stack."""
        manager = TypographyManager()
        
        hanzi_stack = manager.get_font_stack(FontType.HANZI)
        assert "Noto Sans CJK SC" in hanzi_stack
        assert "sans-serif" in hanzi_stack
        
        pinyin_stack = manager.get_font_stack(FontType.PINYIN)
        assert "Noto Sans" in pinyin_stack
        assert "serif" in pinyin_stack
        
        english_stack = manager.get_font_stack(FontType.ENGLISH)
        assert "system-ui" in english_stack
        assert "sans-serif" in english_stack
    
    def test_get_font_stack_custom_primary(self):
        """Test getting font stack with custom primary font."""
        manager = TypographyManager()
        
        custom_stack = manager.get_font_stack(FontType.HANZI, "SimHei")
        assert "'SimHei'" in custom_stack
        assert "Source Han Sans SC" in custom_stack
        assert "sans-serif" in custom_stack
    
    def test_measure_typography_screen(self):
        """Test typography measurement for screen rendering."""
        manager = TypographyManager()
        
        measurement = manager.measure_typography(48, FontType.HANZI, RenderTarget.SCREEN)
        
        # Check basic properties
        assert measurement.font_type == FontType.HANZI
        assert measurement.font_size_px > 0
        assert measurement.line_height_px > measurement.font_size_px
        assert measurement.char_width_px > 0
        assert measurement.margin_px > 0
    
    def test_measure_typography_pdf_adjustments(self):
        """Test typography measurement with PDF adjustments."""
        manager = TypographyManager()
        
        screen_measurement = manager.measure_typography(48, FontType.HANZI, RenderTarget.SCREEN)
        pdf_measurement = manager.measure_typography(48, FontType.HANZI, RenderTarget.PDF)
        
        # PDF should have adjustments applied
        assert pdf_measurement.font_size_px != screen_measurement.font_size_px
        assert pdf_measurement.line_height_px != screen_measurement.line_height_px
        assert pdf_measurement.margin_px != screen_measurement.margin_px
    
    def test_normalize_typography_params(self):
        """Test typography parameter normalization."""
        manager = TypographyManager()
        
        normalized = manager.normalize_typography_params(
            font_hanzi_pt=48,
            font_pinyin_pt=18,
            font_english_pt=14,
            hanzi_font_family="SimHei",
            render_target=RenderTarget.SCREEN
        )
        
        # Check all required keys are present
        required_keys = [
            "hanzi_px", "pinyin_px", "english_px",
            "hanzi_line_height_px", "pinyin_line_height_px", "english_line_height_px",
            "hanzi_margin_px", "pinyin_margin_px", "english_margin_px",
            "hanzi_font_stack", "pinyin_font_stack", "english_font_stack",
            "hanzi_char_width_px", "pinyin_char_width_px", "english_char_width_px",
            "hanzi_total_height_px", "pinyin_total_height_px", "english_total_height_px"
        ]
        
        for key in required_keys:
            assert key in normalized
            assert normalized[key] is not None
        
        # Check font stacks contain custom hanzi font
        assert "SimHei" in normalized["hanzi_font_stack"]
    
    def test_validate_typography_consistency(self):
        """Test typography consistency validation."""
        manager = TypographyManager()
        
        # Create consistent parameters
        screen_params = manager.normalize_typography_params(48, 18, 14, "SimHei", RenderTarget.SCREEN)
        pdf_params = manager.normalize_typography_params(48, 18, 14, "SimHei", RenderTarget.PDF)
        ppt_params = manager.normalize_typography_params(48, 18, 14, "SimHei", RenderTarget.POWERPOINT)
        
        issues = manager.validate_typography_consistency(screen_params, pdf_params, ppt_params)
        
        # Should have no major consistency issues
        assert len(issues) == 0 or all("ratio" not in issue.lower() for issue in issues)


class TestGlobalFunctions:
    """Test global typography functions."""
    
    def test_get_typography_manager_singleton(self):
        """Test that get_typography_manager returns singleton."""
        manager1 = get_typography_manager()
        manager2 = get_typography_manager()
        
        assert manager1 is manager2
    
    def test_normalize_typography_for_render_target(self):
        """Test convenience function for typography normalization."""
        normalized = normalize_typography_for_render_target(
            font_hanzi_pt=48,
            font_pinyin_pt=18,
            font_english_pt=14,
            hanzi_font_family="SimHei",
            render_target=RenderTarget.PDF
        )
        
        # Should return normalized parameters
        assert "hanzi_px" in normalized
        assert "pinyin_px" in normalized
        assert "english_px" in normalized
        assert normalized["hanzi_font_stack"] is not None


class TestTypographyIntegration:
    """Test typography integration with existing systems."""
    
    def test_font_size_ratios_maintained(self):
        """Test that font size ratios are maintained across render targets."""
        manager = TypographyManager()
        
        # Test with different render targets
        screen_params = manager.normalize_typography_params(48, 18, 14, "SimHei", RenderTarget.SCREEN)
        pdf_params = manager.normalize_typography_params(48, 18, 14, "SimHei", RenderTarget.PDF)
        
        # Calculate ratios
        screen_ratio = screen_params["hanzi_px"] / screen_params["pinyin_px"]
        pdf_ratio = pdf_params["hanzi_px"] / pdf_params["pinyin_px"]
        
        # Ratios should be similar (within 10% tolerance)
        ratio_diff = abs(screen_ratio - pdf_ratio) / screen_ratio
        assert ratio_diff < 0.1
    
    def test_line_height_consistency(self):
        """Test that line heights are consistent and reasonable."""
        manager = TypographyManager()
        
        normalized = manager.normalize_typography_params(48, 18, 14, "SimHei")
        
        # Line heights should be larger than font sizes
        assert normalized["hanzi_line_height_px"] > normalized["hanzi_px"]
        assert normalized["pinyin_line_height_px"] > normalized["pinyin_px"]
        assert normalized["english_line_height_px"] > normalized["english_px"]
        
        # Line heights should be reasonable (not too large)
        assert normalized["hanzi_line_height_px"] < normalized["hanzi_px"] * 2
        assert normalized["pinyin_line_height_px"] < normalized["pinyin_px"] * 2
        assert normalized["english_line_height_px"] < normalized["english_px"] * 2
    
    def test_margin_calculations(self):
        """Test that margin calculations are reasonable."""
        manager = TypographyManager()
        
        normalized = manager.normalize_typography_params(48, 18, 14, "SimHei")
        
        # Margins should be positive
        assert normalized["hanzi_margin_px"] > 0
        assert normalized["pinyin_margin_px"] > 0
        assert normalized["english_margin_px"] > 0
        
        # Margins should be reasonable relative to font size
        assert normalized["hanzi_margin_px"] < normalized["hanzi_px"]
        assert normalized["pinyin_margin_px"] < normalized["pinyin_px"]
        assert normalized["english_margin_px"] < normalized["english_px"]


if __name__ == "__main__":
    pytest.main([__file__])
