"""
Preview dataclasses for services boundary.
Provides type-safe, frozen dataclasses for preview rendering parameters.
"""

from dataclasses import dataclass
from typing import Dict, Any
import json
from core.field_migration import resolve_field_value


@dataclass(frozen=True)
class LayoutOptions:
    """Layout configuration for preview rendering."""
    layout_rows: int
    layout_cols: int
    layout_auto_fill: bool
    card_size_cm: float
    gap_cm: float
    margin_cm: float
    page_size: str  # e.g., "A4", "Letter"
    
    def __post_init__(self):
        """Validate and normalize values."""
        # Ensure positive values
        if self.layout_rows <= 0 or self.layout_cols <= 0:
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
        # Use field migration system for backward compatibility
        config_data = {
            attr: getattr(layout_config, attr, None)
            for attr in ['gap_cm', 'gap_cm', 'margin_cm', 'margin_cm', 'layout_rows', 'layout_cols', 'layout_auto_fill', 'card_size_cm', 'page_size']
            if hasattr(layout_config, attr)
        }

        gap_cm = resolve_field_value(config_data, 'gap_cm', 0.5)
        margin_cm = resolve_field_value(config_data, 'margin_cm', 1.0)

        return cls(
            layout_rows=layout_config.layout_rows,
            layout_cols=layout_config.layout_cols,
            layout_auto_fill=layout_config.layout_auto_fill,
            card_size_cm=layout_config.card_size_cm,
            gap_cm=gap_cm,
            margin_cm=margin_cm,
            page_size=layout_config.page_size
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'layout_rows': self.layout_rows,
            'layout_cols': self.layout_cols,
            'layout_auto_fill': self.layout_auto_fill,
            'card_size_cm': self.card_size_cm,
            'gap_cm': self.gap_cm,
            'margin_cm': self.margin_cm,
            'page_size': self.page_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutOptions':
        """Create from dictionary."""
        return cls(
            layout_rows=int(data['layout_rows']),
            layout_cols=int(data['layout_cols']),
            layout_auto_fill=bool(data['layout_auto_fill']),
            card_size_cm=float(data['card_size_cm']),
            gap_cm=float(data['gap_cm']),
            margin_cm=float(data['margin_cm']),
            page_size=str(data['page_size'])
        )


@dataclass(frozen=True)
class Typography:
    """Typography configuration for preview rendering."""
    hanzi_font_size_pt: int
    pinyin_font_size_pt: int
    english_font_size_pt: int
    hanzi_font_family: str
    
    def __post_init__(self):
        """Validate values."""
        if self.hanzi_font_size_pt <= 0 or self.pinyin_font_size_pt <= 0 or self.english_font_size_pt <= 0:
            raise ValueError("Font sizes must be positive")
        if not self.hanzi_font_family:
            raise ValueError("Hanzi font must not be empty")
    
    @classmethod
    def from_layout_config(cls, layout_config) -> 'Typography':
        """Create from LayoutConfig object."""
        return cls(
            hanzi_font_size_pt=layout_config.hanzi_font_size,
            pinyin_font_size_pt=layout_config.pinyin_font_size,
            english_font_size_pt=layout_config.english_font_size,
            hanzi_font_family=getattr(layout_config, 'hanzi_font_family', 'SimHei')  # May be in UI config
        )
    
    @classmethod
    def from_configs(cls, layout_config, ui_config) -> 'Typography':
        """Create from both LayoutConfig and UIConfig."""
        return cls(
            hanzi_font_size_pt=layout_config.hanzi_font_size,
            pinyin_font_size_pt=layout_config.pinyin_font_size,
            english_font_size_pt=layout_config.english_font_size,
            hanzi_font_family=ui_config.hanzi_font_family
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'hanzi_font_size_pt': self.hanzi_font_size_pt,
            'pinyin_font_size_pt': self.pinyin_font_size_pt,
            'english_font_size_pt': self.english_font_size_pt,
            'hanzi_font_family': self.hanzi_font_family
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Typography':
        """Create from dictionary."""
        return cls(
            hanzi_font_size_pt=int(data['hanzi_font_size_pt']),
            pinyin_font_size_pt=int(data['pinyin_font_size_pt']),
            english_font_size_pt=int(data['english_font_size_pt']),
            hanzi_font_family=str(data['hanzi_font_family'])
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
    card_size_cm: float, gap_cm: float, margin_cm: float, page_size: str,
    hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
    hanzi_font_family: str, background_color: str, preview_mode: str,
    layout_rows: int, layout_cols: int, layout_auto_fill: bool
) -> PreviewParams:
    """Convert legacy individual parameters to PreviewParams."""
    layout = LayoutOptions(
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=layout_auto_fill,
        card_size_cm=card_size,
        gap_cm=gap,
        margin_cm=margin,
        page_size=page_size
    )
    
    typography = Typography(
        hanzi_font_size_pt=hanzi_font_size,
        pinyin_font_size_pt=pinyin_font_size,
        english_font_size_pt=english_font_size,
        hanzi_font_family=hanzi_font_family
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
        params.layout.layout_rows,
        params.layout.layout_cols,
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
        'card_size_cm': params.layout.card_size_cm,
        'gap_cm': params.layout.gap_cm,
        'margin_cm': params.layout.margin_cm,
        'page_size': params.layout.page_size,
        'hanzi_font_size': params.typography.hanzi_font_size_pt,
        'pinyin_font_size': params.typography.pinyin_font_size_pt,
        'english_font_size': params.typography.english_font_size_pt,
        'hanzi_font_family': params.typography.hanzi_font_family,
        'background_color': params.visual.background_color,
        'preview_mode': params.visual.preview_mode,
        'layout_rows': params.layout.layout_rows,
        'layout_cols': params.layout.layout_cols,
        'layout_auto_fill': params.layout.layout_auto_fill
    }


def convert_preview_params_to_render_options(params: PreviewParams) -> 'RenderOptions':
    """
    Convert PreviewParams to RenderOptions for shared render core.

    Args:
        params: Preview parameters

    Returns:
        RenderOptions compatible with shared render core
    """
    from services.render_core import RenderOptions

    return RenderOptions(
        # Layout options
        card_size_cm=params.layout.card_size_cm,
        gap_cm=params.layout.gap_cm,
        margin_cm=params.layout.margin_cm,
        page_size=params.layout.page_size,
        layout_rows=params.layout.layout_rows,
        layout_cols=params.layout.layout_cols,
        layout_auto_fill=params.layout.layout_auto_fill,

        # Typography options
        hanzi_font_size_pt=params.typography.hanzi_font_size_pt,
        pinyin_font_size_pt=params.typography.pinyin_font_size_pt,
        english_font_size_pt=params.typography.english_font_size_pt,
        hanzi_font_family=params.typography.hanzi_font_family,

        # Visual options
        background_color=params.visual.background_color
    )
