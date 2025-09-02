"""
Configuration objects for the Chinese Character Learning Cards application.
Provides structured configuration classes to replace long parameter lists.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class UIConfig:
    """Configuration for UI appearance and behavior."""
    hanzi_font_family: str = 'SimHei'
    background_color: str = '#ffffff'
    preview_mode: str = '📄 完整页面'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIConfig':
        """Create UIConfig from dictionary with validation."""
        def safe_get_str(key: str, default: str) -> str:
            value = data.get(key)
            return value if isinstance(value, str) and value else default

        return cls(
            hanzi_font_family=safe_get_str('hanzi_font_family', 'SimHei'),
            background_color=safe_get_str('background_color', '#ffffff'),
            preview_mode=safe_get_str('preview_mode', '📄 完整页面')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert UIConfig to dictionary."""
        return {
            'hanzi_font_family': self.hanzi_font_family,
            'background_color': self.background_color,
            'preview_mode': self.preview_mode
        }


@dataclass
class LayoutConfig:
    """Configuration for layout and typography."""
    card_size_cm: float = 5.5
    gap_cm: float = 0.5
    margin_cm: float = 1.0
    hanzi_font_size: int = 48
    pinyin_font_size: int = 18
    english_font_size: int = 14
    page_size: str = 'A4'
    layout_rows: int = 2
    layout_cols: int = 3
    layout_auto_fill: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutConfig':
        """Create LayoutConfig from dictionary with validation."""
        try:
            return cls(
                card_size_cm=float(data.get('card_size_cm') or 5.5),
                gap_cm=float(data.get('gap_cm') or 0.5),
                margin_cm=float(data.get('margin_cm') or 1.0),
                hanzi_font_size=int(data.get('hanzi_font_size') or 48),
                pinyin_font_size=int(data.get('pinyin_font_size') or 18),
                english_font_size=int(data.get('english_font_size') or 14),
                page_size=str(data.get('page_size') or 'A4'),
                layout_rows=max(1, int(data.get('layout_rows') or 2)),  # Ensure positive
                layout_cols=max(1, int(data.get('layout_cols') or 3)),  # Ensure positive
                layout_auto_fill=bool(data.get('layout_auto_fill', True))
            )
        except (ValueError, TypeError):
            # Return default config if conversion fails
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert LayoutConfig to dictionary."""
        return {
            'card_size_cm': self.card_size_cm,
            'gap_cm': self.gap_cm,
            'margin_cm': self.margin_cm,
            'hanzi_font_size': self.hanzi_font_size,
            'pinyin_font_size': self.pinyin_font_size,
            'english_font_size': self.english_font_size,
            'page_size': self.page_size,
            'layout_rows': self.layout_rows,
            'layout_cols': self.layout_cols,
            'layout_auto_fill': self.layout_auto_fill
        }


@dataclass
class AppConfig:
    """Combined application configuration."""
    ui: UIConfig
    layout: LayoutConfig
    
    @classmethod
    def from_dicts(cls, ui_data: Dict[str, Any], layout_data: Dict[str, Any]) -> 'AppConfig':
        """Create AppConfig from separate dictionaries."""
        return cls(
            ui=UIConfig.from_dict(ui_data),
            layout=LayoutConfig.from_dict(layout_data)
        )
    
    @classmethod
    def default(cls) -> 'AppConfig':
        """Create default application configuration."""
        return cls(
            ui=UIConfig(),
            layout=LayoutConfig()
        )
    
    def to_dicts(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """Convert AppConfig to separate dictionaries."""
        return self.ui.to_dict(), self.layout.to_dict()


def create_config_from_params(card_size_cm: float, gap_cm: float, margin_cm: float, page_size: str,
                             hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                             hanzi_font_family: str, background_color: str, preview_mode: str,
                             layout_rows: int, layout_cols: int, layout_auto_fill: bool) -> AppConfig:
    """Create AppConfig from individual parameters (for migration)."""
    ui_config = UIConfig(
        hanzi_font_family=hanzi_font_family,
        background_color=background_color,
        preview_mode=preview_mode
    )
    
    layout_config = LayoutConfig(
        card_size_cm=card_size_cm,
        gap_cm=gap_cm,
        margin_cm=margin_cm,
        hanzi_font_size=hanzi_font_size,
        pinyin_font_size=pinyin_font_size,
        english_font_size=english_font_size,
        page_size=page_size,
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=layout_auto_fill
    )

    return AppConfig(ui=ui_config, layout=layout_config)
