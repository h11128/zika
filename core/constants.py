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
