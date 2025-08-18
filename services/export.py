"""
Export service for the Chinese Character Learning Cards application.
Handles exporting cards to different formats (PPTX, PDF).
"""

import tempfile
import os
from typing import List, Dict
from src.layout_pptx import PPTXCardGenerator
from src.layout_pdf import PDFCardGenerator
from core.constants import (
    DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN,
    DEFAULT_ROWS, DEFAULT_COLS, DEFAULT_AUTO_FILL,
    DEFAULT_FONT_HANZI, DEFAULT_FONT_PINYIN, DEFAULT_FONT_ENGLISH,
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR
)


def export_cards(cards: List[Dict[str, str]], format_type: str, **options) -> bytes:
    """Export cards to specified format and return file content."""
    with tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False) as tmp_file:
        try:
            if format_type == 'pptx':
                generator = PPTXCardGenerator(
                    page_size=options.get('page_size', DEFAULT_PAGE_SIZE),
                    card_size_cm=options.get('card_size', DEFAULT_CARD_SIZE),
                    gap_cm=options.get('gap', DEFAULT_GAP),
                    margin_cm=options.get('margin', DEFAULT_MARGIN),
                    rows=options.get('rows', DEFAULT_ROWS),
                    cols=options.get('cols', DEFAULT_COLS),
                    auto_fill=options.get('auto_fill', DEFAULT_AUTO_FILL)
                )
                success = generator.generate_pptx(
                    cards, tmp_file.name,
                    font_hanzi=options.get('font_hanzi', DEFAULT_FONT_HANZI),
                    font_pinyin=options.get('font_pinyin', DEFAULT_FONT_PINYIN),
                    font_english=options.get('font_english', DEFAULT_FONT_ENGLISH),
                    hanzi_font=options.get('hanzi_font', DEFAULT_HANZI_FONT),
                    background_color=options.get('background_color', DEFAULT_BACKGROUND_COLOR)
                )
            elif format_type == 'pdf':
                generator = PDFCardGenerator(
                    page_size=options.get('page_size', DEFAULT_PAGE_SIZE),
                    card_size_cm=options.get('card_size', DEFAULT_CARD_SIZE),
                    gap_cm=options.get('gap', DEFAULT_GAP),
                    margin_cm=options.get('margin', DEFAULT_MARGIN),
                    rows=options.get('rows', DEFAULT_ROWS),
                    cols=options.get('cols', DEFAULT_COLS),
                    auto_fill=options.get('auto_fill', DEFAULT_AUTO_FILL)
                )
                success = generator.generate_pdf(
                    cards, tmp_file.name,
                    font_hanzi=options.get('font_hanzi', DEFAULT_FONT_HANZI),
                    font_pinyin=options.get('font_pinyin', DEFAULT_FONT_PINYIN),
                    font_english=options.get('font_english', DEFAULT_FONT_ENGLISH)
                )
            else:
                raise ValueError(f"Unsupported format: {format_type}")

            if success:
                with open(tmp_file.name, 'rb') as f:
                    return f.read()
            else:
                raise Exception(f"{format_type.upper()} generation failed")
                
        finally:
            try:
                os.unlink(tmp_file.name)
            except:
                pass
