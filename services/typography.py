"""
Typography and pagination consistency module.
Implements font fallback matrix, measurement strategy, and renderer-specific adjustments.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import math


class FontType(Enum):
    """Font type classification for fallback handling."""
    HANZI = "hanzi"
    PINYIN = "pinyin"
    ENGLISH = "english"


class RenderTarget(Enum):
    """Render target for typography adjustments."""
    SCREEN = "screen"
    PDF = "pdf"
    POWERPOINT = "powerpoint"


@dataclass(frozen=True)
class FontFallbackConfig:
    """Font fallback configuration for a specific font type."""
    primary: str
    fallbacks: List[str]
    system_fallback: str
    
    def get_font_stack(self) -> str:
        """Get CSS font stack string."""
        fonts = [f"'{self.primary}'"] + [f"'{fb}'" for fb in self.fallbacks] + [self.system_fallback]
        return ", ".join(fonts)


@dataclass(frozen=True)
class LineHeightConfig:
    """Line height configuration for consistent spacing."""
    hanzi_multiplier: float = 1.1
    pinyin_multiplier: float = 1.2
    english_multiplier: float = 1.2
    safety_padding_px: int = 2
    
    def get_line_height_px(self, font_size_px: int, font_type: FontType) -> int:
        """Calculate line height in pixels for given font size and type."""
        multiplier = {
            FontType.HANZI: self.hanzi_multiplier,
            FontType.PINYIN: self.pinyin_multiplier,
            FontType.ENGLISH: self.english_multiplier
        }[font_type]
        
        return math.ceil(font_size_px * multiplier) + self.safety_padding_px


@dataclass(frozen=True)
class TypographyMeasurement:
    """Typography measurement results for layout calculations."""
    font_size_px: int
    line_height_px: int
    char_width_px: float
    margin_px: int
    font_type: FontType
    
    @property
    def effective_height_px(self) -> int:
        """Get effective height including margins."""
        return self.line_height_px + self.margin_px


class TypographyManager:
    """Manages typography consistency across all render targets."""
    
    def __init__(self):
        self._font_fallbacks = self._init_font_fallbacks()
        self._line_height_config = LineHeightConfig()
        self._render_adjustments = self._init_render_adjustments()
    
    def _init_font_fallbacks(self) -> Dict[FontType, FontFallbackConfig]:
        """Initialize font fallback configurations."""
        return {
            FontType.HANZI: FontFallbackConfig(
                primary="Noto Sans CJK SC",
                fallbacks=["Source Han Sans SC", "Microsoft YaHei", "SimHei", "SimSun"],
                system_fallback="sans-serif"
            ),
            FontType.PINYIN: FontFallbackConfig(
                primary="Noto Sans",
                fallbacks=["Noto Serif", "Calibri", "Arial"],
                system_fallback="serif"
            ),
            FontType.ENGLISH: FontFallbackConfig(
                primary="system-ui",
                fallbacks=["Arial", "Helvetica"],
                system_fallback="sans-serif"
            )
        }
    
    def _init_render_adjustments(self) -> Dict[RenderTarget, Dict[str, float]]:
        """Initialize renderer-specific adjustments."""
        return {
            RenderTarget.SCREEN: {
                "font_scale": 1.0,
                "line_height_scale": 1.0,
                "margin_scale": 1.0
            },
            RenderTarget.PDF: {
                "font_scale": 0.95,  # PDF fonts render slightly larger
                "line_height_scale": 1.05,  # More spacing for print
                "margin_scale": 1.2
            },
            RenderTarget.POWERPOINT: {
                "font_scale": 0.98,
                "line_height_scale": 1.0,
                "margin_scale": 1.1
            }
        }
    
    def get_font_stack(self, font_type: FontType, custom_primary: Optional[str] = None) -> str:
        """Get font stack for given font type with optional custom primary font."""
        config = self._font_fallbacks[font_type]
        
        if custom_primary:
            # Use custom primary font but keep fallbacks
            fonts = [f"'{custom_primary}'"] + [f"'{fb}'" for fb in config.fallbacks] + [config.system_fallback]
            return ", ".join(fonts)
        
        return config.get_font_stack()
    
    def measure_typography(
        self, 
        font_size_pt: int, 
        font_type: FontType, 
        render_target: RenderTarget = RenderTarget.SCREEN
    ) -> TypographyMeasurement:
        """Measure typography for layout calculations."""
        # Convert points to pixels (assuming 96 DPI)
        font_size_px = math.ceil(font_size_pt * 96 / 72)
        
        # Apply render target adjustments
        adjustments = self._render_adjustments[render_target]
        adjusted_font_size = math.ceil(font_size_px * adjustments["font_scale"])
        
        # Calculate line height
        line_height_px = self._line_height_config.get_line_height_px(adjusted_font_size, font_type)
        line_height_px = math.ceil(line_height_px * adjustments["line_height_scale"])
        
        # Estimate character width (rough approximation)
        char_width_px = self._estimate_char_width(adjusted_font_size, font_type)
        
        # Calculate margin
        margin_px = self._calculate_margin(adjusted_font_size, font_type)
        margin_px = math.ceil(margin_px * adjustments["margin_scale"])
        
        return TypographyMeasurement(
            font_size_px=adjusted_font_size,
            line_height_px=line_height_px,
            char_width_px=char_width_px,
            margin_px=margin_px,
            font_type=font_type
        )
    
    def _estimate_char_width(self, font_size_px: int, font_type: FontType) -> float:
        """Estimate average character width for given font size and type."""
        # These are rough estimates based on typical font metrics
        width_ratios = {
            FontType.HANZI: 1.0,      # CJK characters are typically square
            FontType.PINYIN: 0.6,     # Latin characters are narrower
            FontType.ENGLISH: 0.55    # English text is slightly narrower
        }
        
        return font_size_px * width_ratios[font_type]
    
    def _calculate_margin(self, font_size_px: int, font_type: FontType) -> int:
        """Calculate appropriate margin for font size and type."""
        # Margin as percentage of font size
        margin_ratios = {
            FontType.HANZI: 0.2,
            FontType.PINYIN: 0.2,
            FontType.ENGLISH: 0.15
        }
        
        base_margin = font_size_px * margin_ratios[font_type]
        return max(4, math.ceil(base_margin))  # Minimum 4px margin
    
    def normalize_typography_params(
        self, 
        font_hanzi_pt: int, 
        font_pinyin_pt: int, 
        font_english_pt: int,
        hanzi_font_family: str,
        render_target: RenderTarget = RenderTarget.SCREEN
    ) -> Dict[str, Any]:
        """Normalize typography parameters for consistent rendering."""
        # Measure each font type
        hanzi_measurement = self.measure_typography(font_hanzi_pt, FontType.HANZI, render_target)
        pinyin_measurement = self.measure_typography(font_pinyin_pt, FontType.PINYIN, render_target)
        english_measurement = self.measure_typography(font_english_pt, FontType.ENGLISH, render_target)
        
        # Get font stacks
        hanzi_stack = self.get_font_stack(FontType.HANZI, hanzi_font)
        pinyin_stack = self.get_font_stack(FontType.PINYIN)
        english_stack = self.get_font_stack(FontType.ENGLISH)
        
        return {
            # Font sizes (adjusted for render target)
            "hanzi_px": hanzi_measurement.font_size_px,
            "pinyin_px": pinyin_measurement.font_size_px,
            "english_px": english_measurement.font_size_px,
            
            # Line heights
            "hanzi_line_height_px": hanzi_measurement.line_height_px,
            "pinyin_line_height_px": pinyin_measurement.line_height_px,
            "english_line_height_px": english_measurement.line_height_px,
            
            # Margins
            "hanzi_margin_px": hanzi_measurement.margin_px,
            "pinyin_margin_px": pinyin_measurement.margin_px,
            "english_margin_px": english_measurement.margin_px,
            
            # Font stacks
            "hanzi_font_stack": hanzi_stack,
            "pinyin_font_stack": pinyin_stack,
            "english_font_stack": english_stack,
            
            # Character width estimates (for layout calculations)
            "hanzi_char_width_px": hanzi_measurement.char_width_px,
            "pinyin_char_width_px": pinyin_measurement.char_width_px,
            "english_char_width_px": english_measurement.char_width_px,
            
            # Total heights (for card sizing)
            "hanzi_total_height_px": hanzi_measurement.effective_height_px,
            "pinyin_total_height_px": pinyin_measurement.effective_height_px,
            "english_total_height_px": english_measurement.effective_height_px
        }
    
    def validate_typography_consistency(
        self, 
        screen_params: Dict[str, Any], 
        pdf_params: Dict[str, Any], 
        ppt_params: Dict[str, Any]
    ) -> List[str]:
        """Validate typography consistency across render targets."""
        issues = []
        
        # Check font size ratios are maintained
        screen_ratio = screen_params["hanzi_px"] / screen_params["pinyin_px"]
        pdf_ratio = pdf_params["hanzi_px"] / pdf_params["pinyin_px"]
        ppt_ratio = ppt_params["hanzi_px"] / ppt_params["pinyin_px"]
        
        if abs(screen_ratio - pdf_ratio) > 0.1 or abs(screen_ratio - ppt_ratio) > 0.1:
            issues.append("Font size ratios inconsistent across render targets")
        
        # Check line height consistency
        for target, params in [("PDF", pdf_params), ("PPT", ppt_params)]:
            if params["hanzi_line_height_px"] < params["hanzi_px"]:
                issues.append(f"{target}: Hanzi line height smaller than font size")
        
        return issues


# Global typography manager instance
_typography_manager = None


def get_typography_manager() -> TypographyManager:
    """Get global typography manager instance."""
    global _typography_manager
    if _typography_manager is None:
        _typography_manager = TypographyManager()
    return _typography_manager


def normalize_typography_for_render_target(
    font_hanzi_pt: int,
    font_pinyin_pt: int, 
    font_english_pt: int,
    hanzi_font_family: str,
    render_target: RenderTarget = RenderTarget.SCREEN
) -> Dict[str, Any]:
    """Convenience function to normalize typography for a specific render target."""
    manager = get_typography_manager()
    return manager.normalize_typography_params(
        font_hanzi_pt, font_pinyin_pt, font_english_pt, hanzi_font_family, render_target
    )
