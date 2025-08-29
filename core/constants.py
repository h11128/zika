"""
Constants for the Chinese Character Learning Cards application.
Centralized location for colors, fonts, and default values.
"""

# Default font and color values
DEFAULT_HANZI_FONT = "Microsoft YaHei"
DEFAULT_BACKGROUND_COLOR = "#FFFFFF"

# Font options for Chinese characters
HANZI_FONT_OPTIONS = [
    "Microsoft YaHei",
    "SimSun",
    "SimHei",
    "KaiTi",
    "FangSong",
    "STSong",
    "STKaiti",
    "STHeiti",
    "PingFang SC",
    "Hiragino Sans GB"
]

# Preset color palette for background selection
PRESET_COLORS = [
    # Row 1: Dark colors
    "#000000", "#333333", "#FF4444", "#FF8800", "#FFDD00",
    "#44FF44", "#00DDDD", "#4488FF", "#8844FF", "#FF44FF",
    # Row 2: Light colors
    "#FFFFFF", "#CCCCCC", "#FFB3B3", "#FFCC99", "#FFEE99",
    "#B3FFB3", "#99FFFF", "#B3CCFF", "#CCB3FF", "#FFB3FF"
]

# Default layout values
DEFAULT_ROWS = 3
DEFAULT_COLS = 2
DEFAULT_AUTO_FILL = True

# Default font sizes
DEFAULT_FONT_HANZI = 48
DEFAULT_FONT_PINYIN = 18
DEFAULT_FONT_ENGLISH = 14

# Default page settings
DEFAULT_PAGE_SIZE = "A4"
DEFAULT_CARD_SIZE = 5.5
DEFAULT_GAP = 0.5
DEFAULT_MARGIN = 1.0


# --- Unit conversions ---
# Pixels-per-millimeter at ~96 DPI. Used to convert page sizes, margins, gaps from mm/cm to px for on-screen preview fidelity.
MM_TO_PX: float = 3.78
# Centimeters to millimeters conversion factor (cm → mm)
CM_TO_MM: float = 10.0
# Pixels-per-point at 96 DPI (1pt = 1/72 inch). Used to map typographic sizes to CSS pixels.
PT_TO_PX: float = 96 / 72

# --- Page sizes (mm) ---
# Physical page dimensions in millimeters for common sizes.
PAGE_SIZE_MM = {
    "A4": (210, 297),
    "Letter": (216, 279),
}
# Default logical page key used throughout the app.
DEFAULT_PAGE_SIZE_KEY = "A4"
# Fallback key if an unknown page size is requested.
FALLBACK_PAGE_SIZE_KEY = "Letter"

# --- Preview scale maxima (px) ---
# Max preview width/height in pixels used to scale the page container for screen previews (no effect on export sizing).
PREVIEW_MAX_WIDTH_PX: int = 600
PREVIEW_MAX_HEIGHT_PX: int = 800

# --- Simple grid layout constants ---
# Grid gap between cards in the simple preview (px), matches UI expectations.
SIMPLE_GRID_GAP_PX: int = 15
# Minimum card size enforced in responsive simple grid to keep content readable (px).
SIMPLE_MIN_CARD_SIZE_PX: int = 120
# When auto_fill is enabled, we allow smaller min size to fit more cards responsively.
AUTO_FILL_MIN_FACTOR: float = 0.5
# When manual card size is provided, we allow reduction but not below this factor of requested size.
MANUAL_SIZE_MIN_FACTOR: float = 0.7
# Max width of grid container to avoid overflow in constrained containers.
CSS_CONTAINER_MAX_WIDTH: str = "100%"

# --- Font/margin ratios (px) ---
# Page-mode: margin below hanzi/pinyin as a fraction of font size; ensures visual spacing scales with font.
PAGE_MARGIN_RATIO: float = 0.1
# Minimum margin in pixels to avoid collapsing to zero at small sizes.
PAGE_MARGIN_MIN_PX: int = 2
# Simple grid: slightly larger default margins to match UI style.
SIMPLE_MARGIN_RATIO: float = 0.2
SIMPLE_MARGIN_MIN_HANZI_PX: int = 6
SIMPLE_MARGIN_MIN_PINYIN_PX: int = 4

# --- Card padding (px) ---
# Page-mode: padding as a fraction of card size (scaled with preview scale), with a minimum.
PAGE_PADDING_RATIO: float = 0.1
PAGE_PADDING_MIN_PX: int = 5
# Simple grid: padding computed from baseline card size used for aspect-preserving cards.
SIMPLE_PADDING_RATIO: float = 0.1
SIMPLE_PADDING_MIN_PX: int = 10
