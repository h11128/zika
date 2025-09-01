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
    DEFAULT_HANZI_FONT_SIZE, DEFAULT_PINYIN_FONT_SIZE, DEFAULT_ENGLISH_FONT_SIZE,
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
                card_size_cm=options.get('card_size_cm', DEFAULT_CARD_SIZE),
                gap_cm=options.get('gap_cm', DEFAULT_GAP),
                margin_cm=options.get('margin_cm', DEFAULT_MARGIN),
                hanzi_font_size=options.get('hanzi_font_size', DEFAULT_HANZI_FONT_SIZE),
                pinyin_font_size=options.get('pinyin_font_size', DEFAULT_PINYIN_FONT_SIZE),
                english_font_size=options.get('english_font_size', DEFAULT_ENGLISH_FONT_SIZE),
                page_size=options.get('page_size', DEFAULT_PAGE_SIZE),
                hanzi_font_family=options.get('hanzi_font_family', DEFAULT_HANZI_FONT),
                background_color=options.get('background_color', DEFAULT_BACKGROUND_COLOR),
                layout_rows=options.get('layout_rows', DEFAULT_ROWS),
                layout_cols=options.get('layout_cols', DEFAULT_COLS),
                layout_auto_fill=options.get('layout_auto_fill', DEFAULT_AUTO_FILL)
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
                card_size_cm=options.get('card_size_cm', DEFAULT_CARD_SIZE),
                gap_cm=options.get('gap_cm', DEFAULT_GAP),
                margin_cm=options.get('margin_cm', DEFAULT_MARGIN),
                layout_rows=options.get('layout_rows', DEFAULT_ROWS),
                layout_cols=options.get('layout_cols', DEFAULT_COLS),
                layout_auto_fill=options.get('layout_auto_fill', DEFAULT_AUTO_FILL)
            )
            success = generator.generate_pptx(
                cards, tmp_file_path,
                hanzi_font_size=options.get('hanzi_font_size', DEFAULT_HANZI_FONT_SIZE),
                pinyin_font_size=options.get('pinyin_font_size', DEFAULT_PINYIN_FONT_SIZE),
                english_font_size=options.get('english_font_size', DEFAULT_ENGLISH_FONT_SIZE),
                hanzi_font_family=options.get('hanzi_font_family', DEFAULT_HANZI_FONT),
                background_color=options.get('background_color', DEFAULT_BACKGROUND_COLOR)
            )
        elif format_type == 'pdf':
            generator = PDFCardGenerator(
                page_size=options.get('page_size', DEFAULT_PAGE_SIZE),
                card_size_cm=options.get('card_size_cm', DEFAULT_CARD_SIZE),
                gap_cm=options.get('gap_cm', DEFAULT_GAP),
                margin_cm=options.get('margin_cm', DEFAULT_MARGIN),
                layout_rows=options.get('layout_rows', DEFAULT_ROWS),
                layout_cols=options.get('layout_cols', DEFAULT_COLS),
                layout_auto_fill=options.get('layout_auto_fill', DEFAULT_AUTO_FILL)
            )
            success = generator.generate_pdf(
                cards, tmp_file_path,
                hanzi_font_size=options.get('hanzi_font_size', DEFAULT_HANZI_FONT_SIZE),
                pinyin_font_size=options.get('pinyin_font_size', DEFAULT_PINYIN_FONT_SIZE),
                english_font_size=options.get('english_font_size', DEFAULT_ENGLISH_FONT_SIZE)
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
