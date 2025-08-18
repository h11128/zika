"""
Configuration objects for the Chinese Character Learning Cards application.
Provides structured configuration classes to replace long parameter lists.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class UIConfig:
    """Configuration for UI appearance and behavior."""
    hanzi_font: str = 'SimHei'
    background_color: str = '#ffffff'
    preview_mode: str = '📄 完整页面'
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIConfig':
        """Create UIConfig from dictionary with validation."""
        def safe_get_str(key: str, default: str) -> str:
            value = data.get(key)
            return value if isinstance(value, str) and value else default

        return cls(
            hanzi_font=safe_get_str('hanzi_font', 'SimHei'),
            background_color=safe_get_str('background_color', '#ffffff'),
            preview_mode=safe_get_str('preview_mode', '📄 完整页面')
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert UIConfig to dictionary."""
        return {
            'hanzi_font': self.hanzi_font,
            'background_color': self.background_color,
            'preview_mode': self.preview_mode
        }


@dataclass
class LayoutConfig:
    """Configuration for layout and typography."""
    card_size: float = 5.5
    gap: float = 0.5
    margin: float = 1.0
    font_hanzi: int = 48
    font_pinyin: int = 18
    font_english: int = 14
    page_size: str = 'A4'
    rows: int = 2
    cols: int = 3
    auto_fill: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LayoutConfig':
        """Create LayoutConfig from dictionary with validation."""
        try:
            return cls(
                card_size=float(data.get('card_size') or 5.5),
                gap=float(data.get('gap') or 0.5),
                margin=float(data.get('margin') or 1.0),
                font_hanzi=int(data.get('font_hanzi') or 48),
                font_pinyin=int(data.get('font_pinyin') or 18),
                font_english=int(data.get('font_english') or 14),
                page_size=str(data.get('page_size') or 'A4'),
                rows=max(1, int(data.get('rows') or 2)),  # Ensure positive
                cols=max(1, int(data.get('cols') or 3)),  # Ensure positive
                auto_fill=bool(data.get('auto_fill', True))
            )
        except (ValueError, TypeError):
            # Return default config if conversion fails
            return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert LayoutConfig to dictionary."""
        return {
            'card_size': self.card_size,
            'gap': self.gap,
            'margin': self.margin,
            'font_hanzi': self.font_hanzi,
            'font_pinyin': self.font_pinyin,
            'font_english': self.font_english,
            'page_size': self.page_size,
            'rows': self.rows,
            'cols': self.cols,
            'auto_fill': self.auto_fill
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


def create_config_from_params(card_size: float, gap: float, margin: float, page_size: str,
                             font_hanzi: int, font_pinyin: int, font_english: int,
                             hanzi_font: str, background_color: str, preview_mode: str,
                             rows: int, cols: int, auto_fill: bool) -> AppConfig:
    """Create AppConfig from individual parameters (for migration)."""
    ui_config = UIConfig(
        hanzi_font=hanzi_font,
        background_color=background_color,
        preview_mode=preview_mode
    )
    
    layout_config = LayoutConfig(
        card_size=card_size,
        gap=gap,
        margin=margin,
        font_hanzi=font_hanzi,
        font_pinyin=font_pinyin,
        font_english=font_english,
        page_size=page_size,
        rows=rows,
        cols=cols,
        auto_fill=auto_fill
    )
    
    return AppConfig(ui=ui_config, layout=layout_config)
