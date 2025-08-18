"""
PDF layout generator for 3x3 Chinese character learning cards.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import cm, inch
from reportlab.lib.colors import black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from typing import List, Dict, Tuple, Optional
import os


class PDFCardGenerator:
    """Generator for PDF format learning cards (rows x cols grid)."""

    def __init__(self, page_size: str = "A4", card_size_cm: float = 6.0,
                 gap_cm: float = 0.6, margin_cm: float = 1.0, inner_padding_cm: float = 0.6,
                 rows: int = 3, cols: int = 3, auto_fill: bool = True):
        """
        Initialize the PDF generator.

        Args:
            page_size: Page size ("A4" or "Letter")
            card_size_cm: Size of each card in cm (used when auto_fill is False)
            gap_cm: Gap between cards in cm
            margin_cm: Page margin in cm
        """
        self.page_size = page_size
        self.gap_cm = gap_cm
        self.margin_cm = margin_cm
        self.rows = max(1, int(rows or 3))
        self.cols = max(1, int(cols or 3))
        self.inner_padding = inner_padding_cm * cm  # inner padding inside each card
        self.auto_fill = bool(auto_fill)

        # Set page dimensions
        if page_size.upper() == "A4":
            self.page_width, self.page_height = A4
        elif page_size.upper() == "LETTER":
            self.page_width, self.page_height = letter
        else:
            raise ValueError(f"Unsupported page size: {page_size}")

        # Convert to points (ReportLab uses points)
        self.gap = gap_cm * cm
        self.margin = margin_cm * cm

        # Available area in points
        max_w = self.page_width - 2 * self.margin
        max_h = self.page_height - 2 * self.margin

        # Determine card size (points)
        if self.auto_fill:
            size_w = (max_w - max(0, self.cols - 1) * self.gap) / self.cols if self.cols > 0 else 0
            size_h = (max_h - max(0, self.rows - 1) * self.gap) / self.rows if self.rows > 0 else 0
            self.card_size = max(0, min(size_w, size_h))
        else:
            self.card_size = card_size_cm * cm

        # Calculate grid layout
        self.grid_width = self.cols * self.card_size + max(0, self.cols - 1) * self.gap
        self.grid_height = self.rows * self.card_size + max(0, self.rows - 1) * self.gap

        # Ensure grid fits within margins; if not, shrink card size slightly to fit
        tolerance = 0.1 * cm
        if self.grid_width > max_w + tolerance or self.grid_height > max_h + tolerance:
            # Compute the scale factor needed to fit and apply to card_size
            scale_w = max_w / self.grid_width if self.grid_width > 0 else 1.0
            scale_h = max_h / self.grid_height if self.grid_height > 0 else 1.0
            scale = min(scale_w, scale_h) * 0.995  # small safety margin
            self.card_size *= scale
            self.grid_width = self.cols * self.card_size + max(0, self.cols - 1) * self.gap
            self.grid_height = self.rows * self.card_size + max(0, self.rows - 1) * self.gap

        # Try to register Chinese fonts
        self._register_fonts()

    def _register_fonts(self):
        """Register fonts for Chinese characters."""
        self.chinese_font = "Helvetica"  # Fallback
        self.pinyin_font = "Helvetica"   # Fallback for pinyin
        self.english_font = "Helvetica"

        # Try to register common fonts that support Chinese and pinyin
        font_configs = [
            # Windows fonts (common)
            ("C:/Windows/Fonts/msyh.ttc", "Microsoft YaHei"),   # Chinese UI font (TTC)
            ("C:/Windows/Fonts/msyh.ttf", "Microsoft YaHei"),   # Some systems have TTF
            ("C:/Windows/Fonts/msyhbd.ttc", "Microsoft YaHei Bold"),
            ("C:/Windows/Fonts/simsun.ttc", "SimSun"),          # Chinese fallback (TTC)
            ("C:/Windows/Fonts/simhei.ttf", "SimHei"),          # Chinese black
            ("C:/Windows/Fonts/arialuni.ttf", "Arial Unicode MS"),
            ("C:/Windows/Fonts/calibri.ttf", "Calibri"),        # Good for pinyin
            ("C:/Windows/Fonts/arial.ttf", "Arial"),            # English fallback
            # macOS fonts
            ("/System/Library/Fonts/PingFang.ttc", "PingFang"),
            ("/Library/Fonts/Arial Unicode MS.ttf", "Arial Unicode MS"),
            # Linux fonts
            ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK"),
            ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVu Sans"),
            ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "Liberation Sans")
        ]

        def try_register(name_hint: str, path: str):
            """Attempt to register a font (handles TTC indices). Returns registered name or None."""
            try:
                safe_name = name_hint.replace(" ", "")
                if path.lower().endswith('.ttc'):
                    # Try first few indices commonly used in TTC collections
                    for idx in range(0, 6):
                        try:
                            pdfmetrics.registerFont(TTFont(f"{safe_name}{idx}", path, subfontIndex=idx))
                            return f"{safe_name}{idx}"
                        except Exception:
                            continue
                    return None
                else:
                    pdfmetrics.registerFont(TTFont(safe_name, path))
                    return safe_name
            except Exception:
                return None

        for font_path, font_name in font_configs:
            if os.path.exists(font_path):
                reg_name = try_register(font_name, font_path)
                if not reg_name:
                    continue

                # Set preferred fonts
                if ("YaHei" in font_name or "PingFang" in font_name or "Noto Sans CJK" in font_name or "SimSun" in font_name or "SimHei" in font_name):
                    self.chinese_font = reg_name
                elif "Calibri" in font_name:
                    self.pinyin_font = reg_name
                elif "Arial" in font_name and self.pinyin_font == "Helvetica":
                    self.pinyin_font = reg_name

        # If no specific pinyin font found, use the same as Chinese
        if self.pinyin_font == "Helvetica" and self.chinese_font != "Helvetica":
            self.pinyin_font = self.chinese_font
    
    def _draw_card_border(self, c: canvas.Canvas, x: float, y: float) -> None:
        """
        Draw card border.
        
        Args:
            c: Canvas object
            x: Left position
            y: Bottom position
        """
        c.setStrokeColor(black)
        c.setLineWidth(2)
        c.rect(x, y, self.card_size, self.card_size, stroke=1, fill=0)
    
    def _draw_card_text(self, c: canvas.Canvas, card: Dict[str, str], x: float, y: float,
                       font_hanzi: int, font_pinyin: int, font_english: int) -> None:
        """
        Draw text content for a single card with improved vertical spacing.

        Args:
            c: Canvas object
            card: Card data dictionary
            x: Left position
            y: Bottom position
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        # Get text content
        hanzi = card.get('hanzi', '').strip()
        pinyin = card.get('pinyin', '').strip()
        english = card.get('english', '').strip()

        # Calculate center positions
        center_x = x + self.card_size / 2

        # Count non-empty elements for better spacing
        elements = [hanzi, pinyin, english]
        non_empty_elements = [elem for elem in elements if elem]
        num_elements = len(non_empty_elements)

        if num_elements == 0:
            return

        # Calculate vertical positions with even spacing and inner padding
        inner_top = y + self.card_size - self.inner_padding
        inner_bottom = y + self.inner_padding
        usable_height = inner_top - inner_bottom

        # Calculate positions based on number of elements (evenly spaced in inner area)
        if num_elements == 1:
            positions = [inner_bottom + usable_height / 2]
        elif num_elements == 2:
            spacing = usable_height / 3
            positions = [inner_bottom + 2 * spacing, inner_bottom + spacing]
        else:  # 3 elements
            spacing = usable_height / 4
            positions = [inner_bottom + 3 * spacing, inner_bottom + 2 * spacing, inner_bottom + spacing]

        pos_index = 0

        # Draw hanzi (Chinese characters)
        if hanzi:
            c.setFont(self.chinese_font, font_hanzi)
            c.setFillColor(black)

            # Calculate text width for centering
            text_width = c.stringWidth(hanzi, self.chinese_font, font_hanzi)
            text_x = center_x - text_width / 2

            c.drawString(text_x, positions[pos_index], hanzi)
            pos_index += 1

        # Draw pinyin
        if pinyin:
            c.setFont(self.pinyin_font, font_pinyin)
            c.setFillColor(black)

            # Calculate text width for centering
            text_width = c.stringWidth(pinyin, self.pinyin_font, font_pinyin)
            text_x = center_x - text_width / 2

            c.drawString(text_x, positions[pos_index], pinyin)
            pos_index += 1

        # Draw English translation
        if english:
            c.setFont(self.english_font, font_english)
            c.setFillColor(black)

            # Handle long text by wrapping
            max_width = self.card_size - 0.4 * cm  # Leave some margin

            if c.stringWidth(english, self.english_font, font_english) <= max_width:
                # Single line
                text_width = c.stringWidth(english, self.english_font, font_english)
                text_x = center_x - text_width / 2
                c.drawString(text_x, positions[pos_index], english)
            else:
                # Multi-line text
                words = english.split()
                lines = []
                current_line = ""

                for word in words:
                    test_line = current_line + (" " if current_line else "") + word
                    if c.stringWidth(test_line, self.english_font, font_english) <= max_width:
                        current_line = test_line
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word

                if current_line:
                    lines.append(current_line)

                # Draw lines centered around the position
                line_height = font_english * 1.2
                start_y = positions[pos_index] + (len(lines) - 1) * line_height / 2

                for i, line in enumerate(lines):
                    text_width = c.stringWidth(line, self.english_font, font_english)
                    text_x = center_x - text_width / 2
                    c.drawString(text_x, start_y - i * line_height, line)
    
    def _add_single_card(self, c: canvas.Canvas, card: Dict[str, str], row: int, col: int,
                        font_hanzi: int, font_pinyin: int, font_english: int) -> None:
        """
        Add a single card to the page.
        
        Args:
            c: Canvas object
            card: Card data dictionary
            row: Grid row (0-2)
            col: Grid column (0-2)
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        # Calculate centered grid origin (ReportLab uses bottom-left origin)
        avail_w = self.page_width - 2 * self.margin
        avail_h = self.page_height - 2 * self.margin
        start_x = self.margin + max(0, (avail_w - self.grid_width) / 2)
        start_y = self.margin + max(0, (avail_h - self.grid_height) / 2)

        # Position for this cell
        x = start_x + col * (self.card_size + self.gap)
        # Row 0 is top row -> its bottom = start_y + 2*(card+gap)
        y = start_y + (2 - row) * (self.card_size + self.gap)
        
        # Draw border
        self._draw_card_border(c, x, y)
        
        # Draw text
        self._draw_card_text(c, card, x, y, font_hanzi, font_pinyin, font_english)
    
    def add_cards_page(self, c: canvas.Canvas, cards: List[Dict[str, str]],
                      font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14) -> None:
        """
        Add a page with up to rows*cols cards in a grid.

        Args:
            c: Canvas object
            cards: List of card dictionaries with 'hanzi', 'pinyin', 'english' keys
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        max_cards = self.rows * self.cols
        for i, card in enumerate(cards[:max_cards]):
            row = i // self.cols
            col = i % self.cols
            self._add_single_card(c, card, row, col, font_hanzi, font_pinyin, font_english)

        # Finish the page
        c.showPage()

    def generate_pdf(self, cards: List[Dict[str, str]], output_path: str,
                    font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14) -> bool:
        """
        Generate complete PDF file with all cards.

        Args:
            cards: List of all card data
            output_path: Output file path
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English

        Returns:
            True if successful
        """
        try:
            # Create canvas
            c = canvas.Canvas(output_path, pagesize=(self.page_width, self.page_height))

            # Split cards into pages of rows*cols
            page_size = max(1, self.rows * self.cols)
            for i in range(0, len(cards), page_size):
                page_cards = cards[i:i+page_size]
                self.add_cards_page(c, page_cards, font_hanzi, font_pinyin, font_english)

            # Save PDF
            c.save()
            return True

        except Exception as e:
            print(f"Error generating PDF: {e}")
            return False

    def get_layout_info(self) -> Dict[str, any]:
        """Get layout information for debugging."""
        return {
            'page_size': self.page_size,
            'page_width_cm': self.page_width / cm,
            'page_height_cm': self.page_height / cm,
            'card_size_cm': self.card_size / cm,
            'gap_cm': self.gap / cm,
            'margin_cm': self.margin / cm,
            'rows': self.rows,
            'cols': self.cols,
            'grid_width_cm': self.grid_width / cm,
            'grid_height_cm': self.grid_height / cm,
            'cards_per_page': self.rows * self.cols,
            'chinese_font': self.chinese_font,
            'english_font': self.english_font
        }


def create_sample_cards() -> List[Dict[str, str]]:
    """Create sample cards for testing."""
    return [
        {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
        {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home; family'},
        {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        {'hanzi': '水', 'pinyin': 'shuǐ', 'english': 'water'},
        {'hanzi': '火', 'pinyin': 'huǒ', 'english': 'fire'},
        {'hanzi': '山', 'pinyin': 'shān', 'english': 'mountain'},
        {'hanzi': '月', 'pinyin': 'yuè', 'english': 'moon; month'},
        {'hanzi': '日', 'pinyin': 'rì', 'english': 'sun; day'},
        {'hanzi': '木', 'pinyin': 'mù', 'english': 'wood; tree'},
    ]


if __name__ == "__main__":
    # Test the PDF generator
    print("Testing PDF generator...")
    
    generator = PDFCardGenerator(page_size="A4", card_size_cm=6.0, gap_cm=0.6, margin_cm=1.0)
    
    print("Layout info:")
    layout_info = generator.get_layout_info()
    for key, value in layout_info.items():
        print(f"  {key}: {value}")
    
    # Generate sample PDF
    sample_cards = create_sample_cards()
    output_path = "../out/test_cards.pdf"
    
    success = generator.generate_pdf(sample_cards, output_path)
    if success:
        print(f"\nSample PDF generated: {output_path}")
    else:
        print("\nFailed to generate PDF")
