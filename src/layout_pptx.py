"""
PPTX layout generator for 3x3 Chinese character learning cards.
"""

from pptx import Presentation
from pptx.util import Cm, Pt, Inches
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor
from typing import List, Dict, Tuple
import math


class PPTXCardGenerator:
    """Generator for PPTX format learning cards."""
    
    def __init__(self, page_size: str = "A4", card_size_cm: float = 6.0, 
                 gap_cm: float = 0.6, margin_cm: float = 1.0):
        """
        Initialize the PPTX generator.
        
        Args:
            page_size: Page size ("A4" or "Letter")
            card_size_cm: Size of each card in cm
            gap_cm: Gap between cards in cm
            margin_cm: Page margin in cm
        """
        self.page_size = page_size
        self.card_size_cm = card_size_cm
        self.gap_cm = gap_cm
        self.margin_cm = margin_cm
        
        # Set page dimensions
        if page_size.upper() == "A4":
            self.page_width = Cm(21.0)   # A4 width
            self.page_height = Cm(29.7)  # A4 height
        elif page_size.upper() == "LETTER":
            self.page_width = Inches(8.5)   # Letter width
            self.page_height = Inches(11.0) # Letter height
        else:
            raise ValueError(f"Unsupported page size: {page_size}")
        
        # Calculate grid layout
        self.grid_width = card_size_cm * 3 + gap_cm * 2
        self.grid_height = card_size_cm * 3 + gap_cm * 2
        
        # Check if grid fits on page
        page_width_cm = self.page_width.cm if hasattr(self.page_width, 'cm') else self.page_width / 914400 * 2.54
        page_height_cm = self.page_height.cm if hasattr(self.page_height, 'cm') else self.page_height / 914400 * 2.54

        # Add small tolerance for rounding errors
        tolerance = 0.1
        if self.grid_width + 2 * margin_cm > page_width_cm + tolerance:
            raise ValueError(f"Grid too wide for page: {self.grid_width + 2 * margin_cm}cm > {page_width_cm}cm")
        if self.grid_height + 2 * margin_cm > page_height_cm + tolerance:
            raise ValueError(f"Grid too tall for page: {self.grid_height + 2 * margin_cm}cm > {page_height_cm}cm")
    
    def create_presentation(self) -> Presentation:
        """Create a new presentation with custom page size."""
        prs = Presentation()
        
        # Set slide size
        prs.slide_width = int(self.page_width)
        prs.slide_height = int(self.page_height)
        
        return prs
    
    def add_cards_page(self, prs: Presentation, cards: List[Dict[str, str]], 
                      font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14) -> None:
        """
        Add a page with up to 9 cards in 3x3 grid.
        
        Args:
            prs: Presentation object
            cards: List of card dictionaries with 'hanzi', 'pinyin', 'english' keys
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        # Use blank slide layout
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)
        
        # Add up to 9 cards
        for i, card in enumerate(cards[:9]):
            row, col = divmod(i, 3)
            self._add_single_card(slide, card, row, col, font_hanzi, font_pinyin, font_english)
    
    def _add_single_card(self, slide, card: Dict[str, str], row: int, col: int,
                        font_hanzi: int, font_pinyin: int, font_english: int) -> None:
        """
        Add a single card to the slide.
        
        Args:
            slide: Slide object
            card: Card data dictionary
            row: Grid row (0-2)
            col: Grid column (0-2)
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        # Calculate position
        left = Cm(self.margin_cm + col * (self.card_size_cm + self.gap_cm))
        top = Cm(self.margin_cm + row * (self.card_size_cm + self.gap_cm))
        width = Cm(self.card_size_cm)
        height = Cm(self.card_size_cm)
        
        # Create rectangle shape
        shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, left, top, width, height
        )
        
        # Set border
        shape.line.color.rgb = RGBColor(0, 0, 0)  # Black border
        shape.line.width = Pt(2)
        
        # Set fill to white
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(255, 255, 255)
        
        # Configure text frame
        text_frame = shape.text_frame
        # Avoid potential python-pptx clear() issues on some Office versions
        text_frame.text = ""
        text_frame.margin_left = Cm(0.2)
        text_frame.margin_right = Cm(0.2)
        text_frame.margin_top = Cm(0.2)
        text_frame.margin_bottom = Cm(0.2)
        text_frame.vertical_anchor = MSO_ANCHOR.MIDDLE
        text_frame.word_wrap = True
        
        # Add text content
        self._add_card_text(text_frame, card, font_hanzi, font_pinyin, font_english)
    
    def _add_card_text(self, text_frame, card: Dict[str, str],
                      font_hanzi: int, font_pinyin: int, font_english: int) -> None:
        """
        Add formatted text to a card's text frame.

        Args:
            text_frame: Text frame object
            card: Card data dictionary
            font_hanzi: Font size for Chinese characters
            font_pinyin: Font size for pinyin
            font_english: Font size for English
        """
        # Get text content
        hanzi = card.get('hanzi', '').strip()
        pinyin = card.get('pinyin', '').strip()
        english = card.get('english', '').strip()

        # Do NOT clear here; it was cleared by caller
        # Calculate spacing for even distribution
        total_elements = sum([1 for x in [hanzi, pinyin, english] if x])
        if total_elements == 0:
            return

        # Decide where to put the first line (use the default paragraph)
        para = text_frame.paragraphs[0]
        first_used = False

        # Add hanzi (Chinese characters)
        if hanzi:
            p = para if not first_used else text_frame.add_paragraph()
            first_used = True
            p.text = hanzi
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(font_hanzi)
            p.font.bold = True
            p.font.color.rgb = RGBColor(0, 0, 0)
            # Use a more reliable font for Chinese characters
            try:
                p.font.name = "Microsoft YaHei"  # Better Unicode support
            except:
                try:
                    p.font.name = "SimSun"
                except:
                    p.font.name = "Arial Unicode MS"
            p.line_spacing = 1.0
            if total_elements > 1:
                p.space_after = Pt(8)

        # Add pinyin
        if pinyin:
            p = para if not first_used else text_frame.add_paragraph()
            first_used = True
            p.text = pinyin
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(font_pinyin)
            p.font.italic = True
            p.font.color.rgb = RGBColor(0, 0, 0)
            # Use fonts that handle pinyin tone marks well
            try:
                p.font.name = "Calibri"  # Good for pinyin tone marks
            except:
                try:
                    p.font.name = "Arial"
                except:
                    p.font.name = "Times New Roman"
            p.line_spacing = 1.0
            if english:  # Add space only if there's English text below
                p.space_after = Pt(8)

        # Add English translation
        if english:
            p = para if not first_used else text_frame.add_paragraph()
            first_used = True
            p.text = english
            p.alignment = PP_ALIGN.CENTER
            p.font.size = Pt(font_english)
            p.font.name = "Arial"
            p.font.color.rgb = RGBColor(0, 0, 0)
            p.line_spacing = 1.0
    
    def generate_pptx(self, cards: List[Dict[str, str]], output_path: str,
                     font_hanzi: int = 48, font_pinyin: int = 18, font_english: int = 14) -> bool:
        """
        Generate complete PPTX file with all cards.
        
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
            prs = self.create_presentation()
            
            # Split cards into pages of 9
            for i in range(0, len(cards), 9):
                page_cards = cards[i:i+9]
                self.add_cards_page(prs, page_cards, font_hanzi, font_pinyin, font_english)
            
            # Save presentation
            prs.save(output_path)
            return True
            
        except Exception as e:
            print(f"Error generating PPTX: {e}")
            return False
    
    def get_layout_info(self) -> Dict[str, any]:
        """Get layout information for debugging."""
        return {
            'page_size': self.page_size,
            'page_width_cm': self.page_width.cm if hasattr(self.page_width, 'cm') else self.page_width / 914400 * 2.54,
            'page_height_cm': self.page_height.cm if hasattr(self.page_height, 'cm') else self.page_height / 914400 * 2.54,
            'card_size_cm': self.card_size_cm,
            'gap_cm': self.gap_cm,
            'margin_cm': self.margin_cm,
            'grid_width_cm': self.grid_width,
            'grid_height_cm': self.grid_height,
            'cards_per_page': 9
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
    # Test the PPTX generator
    print("Testing PPTX generator...")
    
    generator = PPTXCardGenerator(page_size="A4", card_size_cm=6.0, gap_cm=0.6, margin_cm=1.0)
    
    print("Layout info:")
    layout_info = generator.get_layout_info()
    for key, value in layout_info.items():
        print(f"  {key}: {value}")
    
    # Generate sample PPTX
    sample_cards = create_sample_cards()
    output_path = "../out/test_cards.pptx"
    
    success = generator.generate_pptx(sample_cards, output_path)
    if success:
        print(f"\nSample PPTX generated: {output_path}")
    else:
        print("\nFailed to generate PPTX")
