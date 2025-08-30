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
    # Try to use shared render core if available
    from core.feature_flags import get_feature_flag

    if get_feature_flag('shared_render_core', False):
        try:
            from services.render_core import render_cards_unified, create_render_options_from_legacy

            # Convert legacy options to RenderOptions
            render_options = create_render_options_from_legacy(
                card_size=options.get('card_size', DEFAULT_CARD_SIZE),
                gap=options.get('gap', DEFAULT_GAP),
                margin=options.get('margin', DEFAULT_MARGIN),
                font_hanzi=options.get('font_hanzi', DEFAULT_FONT_HANZI),
                font_pinyin=options.get('font_pinyin', DEFAULT_FONT_PINYIN),
                font_english=options.get('font_english', DEFAULT_FONT_ENGLISH),
                page_size=options.get('page_size', DEFAULT_PAGE_SIZE),
                hanzi_font=options.get('hanzi_font', DEFAULT_HANZI_FONT),
                background_color=options.get('background_color', DEFAULT_BACKGROUND_COLOR),
                rows=options.get('rows', DEFAULT_ROWS),
                cols=options.get('cols', DEFAULT_COLS),
                auto_fill=options.get('auto_fill', DEFAULT_AUTO_FILL)
            )

            # Use unified rendering
            result = render_cards_unified(cards, render_options, output_format=format_type)
            if result.success:
                return result.content
        except Exception as e:
            # Log error and fall back to legacy implementation
            import logging
            logging.warning(f"Shared render core failed, falling back to legacy: {e}")
            pass

    # Legacy implementation
    tmp_file = tempfile.NamedTemporaryFile(suffix=f'.{format_type}', delete=False)
    tmp_file_path = tmp_file.name
    tmp_file.close()  # Close the file handle immediately

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
                cards, tmp_file_path,
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
                cards, tmp_file_path,
                font_hanzi=options.get('font_hanzi', DEFAULT_FONT_HANZI),
                font_pinyin=options.get('font_pinyin', DEFAULT_FONT_PINYIN),
                font_english=options.get('font_english', DEFAULT_FONT_ENGLISH)
            )
        else:
            raise ValueError(f"Unsupported format: {format_type}")

        if success:
            with open(tmp_file_path, 'rb') as f:
                content = f.read()
            return content
        else:
            raise Exception(f"{format_type.upper()} generation failed")

    finally:
        # Clean up temporary file
        try:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
        except Exception:
            # If cleanup fails, don't crash the function
            pass
