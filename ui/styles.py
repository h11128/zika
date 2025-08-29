"""
Centralized CSS and styling system for the UI refactor.
Provides theme management, responsive design, and component styling.
Legacy functions preserved for backward compatibility.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import streamlit as st

from core.feature_flags import get_feature_flag


class ThemeMode(Enum):
    """Theme mode options."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"


@dataclass
class ColorPalette:
    """Color palette for theming."""
    primary: str
    secondary: str
    background: str
    surface: str
    text_primary: str
    text_secondary: str
    accent: str
    success: str
    warning: str
    error: str
    border: str
    shadow: str


@dataclass
class Typography:
    """Typography configuration."""
    font_family_primary: str
    font_family_secondary: str
    font_size_base: str
    font_size_small: str
    font_size_large: str
    font_size_xlarge: str
    line_height_base: str
    font_weight_normal: str
    font_weight_bold: str


@dataclass
class Spacing:
    """Spacing configuration."""
    xs: str
    sm: str
    md: str
    lg: str
    xl: str
    xxl: str


@dataclass
class BorderRadius:
    """Border radius configuration."""
    none: str
    sm: str
    md: str
    lg: str
    full: str


@dataclass
class Theme:
    """Complete theme configuration."""
    name: str
    mode: ThemeMode
    colors: ColorPalette
    typography: Typography
    spacing: Spacing
    border_radius: BorderRadius


# Predefined themes
LIGHT_THEME = Theme(
    name="light",
    mode=ThemeMode.LIGHT,
    colors=ColorPalette(
        primary="#1f77b4",
        secondary="#ff7f0e",
        background="#ffffff",
        surface="#f8f9fa",
        text_primary="#212529",
        text_secondary="#6c757d",
        accent="#17a2b8",
        success="#28a745",
        warning="#ffc107",
        error="#dc3545",
        border="#dee2e6",
        shadow="rgba(0, 0, 0, 0.1)"
    ),
    typography=Typography(
        font_family_primary="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        font_family_secondary="'Courier New', Courier, monospace",
        font_size_base="16px",
        font_size_small="14px",
        font_size_large="18px",
        font_size_xlarge="24px",
        line_height_base="1.5",
        font_weight_normal="400",
        font_weight_bold="600"
    ),
    spacing=Spacing(
        xs="0.25rem",
        sm="0.5rem",
        md="1rem",
        lg="1.5rem",
        xl="2rem",
        xxl="3rem"
    ),
    border_radius=BorderRadius(
        none="0",
        sm="0.25rem",
        md="0.5rem",
        lg="1rem",
        full="50%"
    )
)

DARK_THEME = Theme(
    name="dark",
    mode=ThemeMode.DARK,
    colors=ColorPalette(
        primary="#4dabf7",
        secondary="#ffa94d",
        background="#1a1a1a",
        surface="#2d2d2d",
        text_primary="#ffffff",
        text_secondary="#b0b0b0",
        accent="#20c997",
        success="#51cf66",
        warning="#ffd43b",
        error="#ff6b6b",
        border="#404040",
        shadow="rgba(0, 0, 0, 0.3)"
    ),
    typography=Typography(
        font_family_primary="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        font_family_secondary="'Courier New', Courier, monospace",
        font_size_base="16px",
        font_size_small="14px",
        font_size_large="18px",
        font_size_xlarge="24px",
        line_height_base="1.5",
        font_weight_normal="400",
        font_weight_bold="600"
    ),
    spacing=Spacing(
        xs="0.25rem",
        sm="0.5rem",
        md="1rem",
        lg="1.5rem",
        xl="2rem",
        xxl="3rem"
    ),
    border_radius=BorderRadius(
        none="0",
        sm="0.25rem",
        md="0.5rem",
        lg="1rem",
        full="50%"
    )
)


class StyleManager:
    """Manages application styling and themes."""

    def __init__(self):
        self.current_theme: Theme = LIGHT_THEME
        self.custom_css: List[str] = []

    def set_theme(self, theme: Theme) -> None:
        """Set the current theme."""
        self.current_theme = theme

    def get_theme(self) -> Theme:
        """Get the current theme."""
        return self.current_theme

    def add_custom_css(self, css: str) -> None:
        """Add custom CSS."""
        self.custom_css.append(css)

    def clear_custom_css(self) -> None:
        """Clear all custom CSS."""
        self.custom_css.clear()

    def apply_styles(self) -> None:
        """Apply styles to Streamlit app."""
        if not get_feature_flag('centralized_styles', False):
            # Fall back to legacy styles
            apply_global_styles()
            return

        # Generate CSS variables from theme
        theme = self.current_theme
        css_vars = f"""
        :root {{
            --color-primary: {theme.colors.primary};
            --color-background: {theme.colors.background};
            --color-surface: {theme.colors.surface};
            --color-text-primary: {theme.colors.text_primary};
            --color-border: {theme.colors.border};
        }}
        """

        # Combine with custom CSS
        custom_css = "\n".join(self.custom_css)

        full_css = f"""
        {css_vars}

        /* Legacy styles for backward compatibility */
        .preview-sticky {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: var(--color-background, #ffffff);
            max-height: 100vh;
            overflow-y: auto;
            align-self: start;
        }}

        /* Custom CSS */
        {custom_css}
        """

        st.markdown(f"<style>{full_css}</style>", unsafe_allow_html=True)


# Global style manager
_style_manager: Optional[StyleManager] = None


def get_style_manager() -> StyleManager:
    """Get or create the global style manager."""
    global _style_manager
    if _style_manager is None:
        _style_manager = StyleManager()
    return _style_manager


def set_theme(theme_name: str) -> None:
    """Set theme by name."""
    manager = get_style_manager()

    if theme_name == "light":
        manager.set_theme(LIGHT_THEME)
    elif theme_name == "dark":
        manager.set_theme(DARK_THEME)
    else:
        raise ValueError(f"Unknown theme: {theme_name}")


def get_current_theme() -> Theme:
    """Get current theme."""
    return get_style_manager().get_theme()


def apply_app_styles() -> None:
    """Apply application styles (new or legacy)."""
    get_style_manager().apply_styles()


def add_custom_css(css: str) -> None:
    """Add custom CSS to the application."""
    get_style_manager().add_custom_css(css)


def apply_global_styles() -> None:
    """Apply global CSS styles to the application."""
    st.markdown(
        """
        <style>
        .preview-sticky { 
            position: sticky; 
            top: 0; 
            z-index: 100; 
            background: #ffffff; 
            max-height: 100vh; 
            overflow-y: auto; 
            align-self: start; 
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sticky_wrapper_start() -> None:
    """Render the start of a sticky wrapper div."""
    st.markdown('<div class="preview-sticky">', unsafe_allow_html=True)


def render_sticky_wrapper_end() -> None:
    """Render the end of a sticky wrapper div."""
    st.markdown('</div>', unsafe_allow_html=True)
