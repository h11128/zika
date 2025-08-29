"""
Preview dataclasses for services boundary.
Provides type-safe, frozen dataclasses for preview rendering parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any
import json


@dataclass(frozen=True)
class LayoutOptions:
    """Layout configuration for preview rendering."""
    rows: int
    cols: int
    auto_fill: bool
    card_size_cm: float
    gap_cm: float
    margin_cm: float
    page_size: str  # e.g., "A4", "Letter"
    
    def __post_init__(self):
        """Validate and normalize values."""
        # Ensure positive values
        if self.rows <= 0 or self.cols <= 0:
            raise ValueError("Rows and cols must be positive")
        if self.card_size_cm <= 0:
            raise ValueError("Card size must be positive")
        if self.gap_cm < 0 or self.margin_cm < 0:
            raise ValueError("Gap and margin must be non-negative")
        
        # Normalize float precision for stable hashing
        object.__setattr__(self, 'card_size_cm', round(self.card_size_cm, 4))
        object.__setattr__(self, 'gap_cm', round(self.gap_cm, 4))
        object.__setattr__(self, 'margin_cm', round(self.margin_cm, 4))
    
    @classmethod
    def from_layout_config(cls, layout_config) -> 'LayoutOptions':
        """Create from LayoutConfig object."""
        # Support both old and new field names
        gap_cm = getattr(layout_config, 'gap_cm', None)
        if gap_cm is None:
            gap_cm = getattr(layout_config, 'gap', 0.5)

        margin_cm = getattr(layout_config, 'margin_cm', None)
        if margin_cm is None:
            margin_cm = getattr(layout_config, 'margin', 1.0)

        return cls(
            rows=layout_config.rows,
            cols=layout_config.cols,
            auto_fill=layout_config.auto_fill,
            card_size_cm=layout_config.card_size,
            gap_cm=gap_cm,
            margin_cm=margin_cm,
            page_size=layout_config.page_size
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'rows': self.rows,
            'cols': self.cols,
            'auto_fill': self.auto_fill,
            'card_size_cm': self.card_size_cm,
            'gap_cm': self.gap_cm,
            'margin_cm': self.margin_cm,
            'page_size': self.page_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutOptions':
        """Create from dictionary."""
        return cls(
            rows=int(data['rows']),
            cols=int(data['cols']),
            auto_fill=bool(data['auto_fill']),
            card_size_cm=float(data['card_size_cm']),
            gap_cm=float(data['gap_cm']),
            margin_cm=float(data['margin_cm']),
            page_size=str(data['page_size'])
        )


@dataclass(frozen=True)
class Typography:
    """Typography configuration for preview rendering."""
    font_hanzi_pt: int
    font_pinyin_pt: int
    font_english_pt: int
    hanzi_font: str
    
    def __post_init__(self):
        """Validate values."""
        if self.font_hanzi_pt <= 0 or self.font_pinyin_pt <= 0 or self.font_english_pt <= 0:
            raise ValueError("Font sizes must be positive")
        if not self.hanzi_font:
            raise ValueError("Hanzi font must not be empty")
    
    @classmethod
    def from_layout_config(cls, layout_config) -> 'Typography':
        """Create from LayoutConfig object."""
        return cls(
            font_hanzi_pt=layout_config.font_hanzi,
            font_pinyin_pt=layout_config.font_pinyin,
            font_english_pt=layout_config.font_english,
            hanzi_font=getattr(layout_config, 'hanzi_font', 'SimHei')  # May be in UI config
        )
    
    @classmethod
    def from_configs(cls, layout_config, ui_config) -> 'Typography':
        """Create from both LayoutConfig and UIConfig."""
        return cls(
            font_hanzi_pt=layout_config.font_hanzi,
            font_pinyin_pt=layout_config.font_pinyin,
            font_english_pt=layout_config.font_english,
            hanzi_font=ui_config.hanzi_font
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'font_hanzi_pt': self.font_hanzi_pt,
            'font_pinyin_pt': self.font_pinyin_pt,
            'font_english_pt': self.font_english_pt,
            'hanzi_font': self.hanzi_font
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Typography':
        """Create from dictionary."""
        return cls(
            font_hanzi_pt=int(data['font_hanzi_pt']),
            font_pinyin_pt=int(data['font_pinyin_pt']),
            font_english_pt=int(data['font_english_pt']),
            hanzi_font=str(data['hanzi_font'])
        )


@dataclass(frozen=True)
class VisualOptions:
    """Visual styling configuration for preview rendering."""
    background_color: str
    preview_mode: str = '📄 完整页面'
    
    def __post_init__(self):
        """Validate values."""
        if not self.background_color:
            raise ValueError("Background color must not be empty")
        if self.preview_mode not in ['📄 完整页面', '🔲 简单网格']:
            raise ValueError(f"Invalid preview mode: {self.preview_mode}")
    
    @classmethod
    def from_ui_config(cls, ui_config) -> 'VisualOptions':
        """Create from UIConfig object."""
        return cls(
            background_color=ui_config.background_color,
            preview_mode=ui_config.preview_mode
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'background_color': self.background_color,
            'preview_mode': self.preview_mode
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VisualOptions':
        """Create from dictionary."""
        return cls(
            background_color=str(data['background_color']),
            preview_mode=str(data.get('preview_mode', '📄 完整页面'))
        )


@dataclass(frozen=True)
class PreviewParams:
    """Complete preview parameters for rendering."""
    layout: LayoutOptions
    typography: Typography
    visual: VisualOptions
    
    @classmethod
    def from_app_config(cls, app_config) -> 'PreviewParams':
        """Create from AppConfig object."""
        return cls(
            layout=LayoutOptions.from_layout_config(app_config.layout),
            typography=Typography.from_configs(app_config.layout, app_config.ui),
            visual=VisualOptions.from_ui_config(app_config.ui)
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'layout': self.layout.to_dict(),
            'typography': self.typography.to_dict(),
            'visual': self.visual.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreviewParams':
        """Create from dictionary."""
        return cls(
            layout=LayoutOptions.from_dict(data['layout']),
            typography=Typography.from_dict(data['typography']),
            visual=VisualOptions.from_dict(data['visual'])
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PreviewParams':
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


def convert_app_config_to_preview_params(app_config) -> PreviewParams:
    """Convert AppConfig to PreviewParams at services boundary."""
    return PreviewParams.from_app_config(app_config)


def convert_legacy_params_to_preview_params(
    card_size: float, gap: float, margin: float, page_size: str,
    font_hanzi: int, font_pinyin: int, font_english: int,
    hanzi_font: str, background_color: str, preview_mode: str,
    rows: int, cols: int, auto_fill: bool
) -> PreviewParams:
    """Convert legacy individual parameters to PreviewParams."""
    layout = LayoutOptions(
        rows=rows,
        cols=cols,
        auto_fill=auto_fill,
        card_size_cm=card_size,
        gap_cm=gap,
        margin_cm=margin,
        page_size=page_size
    )
    
    typography = Typography(
        font_hanzi_pt=font_hanzi,
        font_pinyin_pt=font_pinyin,
        font_english_pt=font_english,
        hanzi_font=hanzi_font
    )
    
    visual = VisualOptions(
        background_color=background_color,
        preview_mode=preview_mode
    )
    
    return PreviewParams(
        layout=layout,
        typography=typography,
        visual=visual
    )


# Validation functions
def validate_preview_params(params: PreviewParams) -> PreviewParams:
    """Validate and normalize preview parameters."""
    # The dataclasses already validate in __post_init__
    # This function can add additional cross-field validation if needed
    
    # Example: Check if card size fits on page
    from services.layout import validate_layout_params
    
    validation_result = validate_layout_params(
        params.layout.rows,
        params.layout.cols,
        params.layout.card_size_cm,
        params.layout.gap_cm,
        params.layout.margin_cm,
        params.layout.page_size
    )
    
    if not validation_result['fits_on_page']:
        # Could log warning or adjust parameters
        pass
    
    return params


# Helper functions for backward compatibility
def extract_legacy_params(params: PreviewParams) -> Dict[str, Any]:
    """Extract legacy parameter format from PreviewParams."""
    return {
        'card_size': params.layout.card_size_cm,
        'gap': params.layout.gap_cm,
        'margin': params.layout.margin_cm,
        'page_size': params.layout.page_size,
        'font_hanzi': params.typography.font_hanzi_pt,
        'font_pinyin': params.typography.font_pinyin_pt,
        'font_english': params.typography.font_english_pt,
        'hanzi_font': params.typography.hanzi_font,
        'background_color': params.visual.background_color,
        'preview_mode': params.visual.preview_mode,
        'rows': params.layout.rows,
        'cols': params.layout.cols,
        'auto_fill': params.layout.auto_fill
    }
