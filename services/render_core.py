"""
Shared Render Core - Unified rendering logic for preview and export.
Extracts common rendering functionality from cache_v2.py and export.py
"""

from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass
import logging

from core.constants import HANZI_FONT_OPTIONS
from services.layout import paginate, PaginateInfo


@dataclass
class RenderOptions:
    """Unified render options for all output formats."""
    # Layout options
    card_size_cm: float = 5.5
    gap_cm: float = 0.5
    margin_cm: float = 1.0
    layout_rows: int = 2
    layout_cols: int = 3
    layout_auto_fill: bool = True
    page_size: str = 'A4'
    
    # Typography options
    font_hanzi_pt: int = 48
    font_pinyin_pt: int = 18
    font_english_pt: int = 14
    hanzi_font_family: str = 'SimHei'
    
    # Visual options
    background_color: str = '#ffffff'
    
    # Output options
    include_page_numbers: bool = True
    optimize_for_print: bool = True
    
    def __post_init__(self):
        """Validate render options."""
        if self.hanzi_font_family not in HANZI_FONT_OPTIONS:
            self.hanzi_font_family = 'SimHei'
        
        if self.page_size not in ['A4', 'Letter']:
            self.page_size = 'A4'
        
        # Ensure positive values
        self.card_size_cm = max(0.1, self.card_size_cm)
        self.gap_cm = max(0.0, self.gap_cm)
        self.margin_cm = max(0.0, self.margin_cm)
        self.layout_rows = max(1, self.layout_rows)
        self.layout_cols = max(1, self.layout_cols)
        self.font_hanzi_pt = max(8, self.font_hanzi_pt)
        self.font_pinyin_pt = max(6, self.font_pinyin_pt)
        self.font_english_pt = max(6, self.font_english_pt)


@dataclass
class RenderResult:
    """Result of rendering operation."""
    content: str  # HTML content or other format
    page_count: int
    card_count: int
    pagination_info: PaginateInfo
    success: bool = True
    error_message: Optional[str] = None
    
    @classmethod
    def error(cls, message: str) -> 'RenderResult':
        """Create error result."""
        return cls(
            content="",
            page_count=0,
            card_count=0,
            pagination_info=PaginateInfo(0, 0, 0),
            success=False,
            error_message=message
        )


def render_page(cards: List[Dict[str, str]], options: RenderOptions) -> RenderResult:
    """
    Core rendering function that generates content for a page of cards.

    Args:
        cards: List of card dictionaries with hanzi, pinyin, english
        options: Rendering options

    Returns:
        RenderResult with rendered content and metadata
    """
    import time
    start_time = time.time()

    try:
        if not cards:
            result = RenderResult(
                content=_render_empty_page(options),
                page_count=1,
                card_count=0,
                pagination_info=PaginateInfo(0, 0, 0)
            )
            _record_render_metrics(start_time, "empty_page", True)
            return result

        # Calculate pagination
        pagination_info = paginate(len(cards), options.layout_rows, options.layout_cols)

        # Generate HTML content
        html_content = _generate_html_content(cards, options, pagination_info)

        result = RenderResult(
            content=html_content,
            page_count=pagination_info.total_pages,
            card_count=len(cards),
            pagination_info=pagination_info
        )

        _record_render_metrics(start_time, "html_page", True)
        return result

    except Exception as e:
        _record_render_metrics(start_time, "html_page", False, str(e))
        logging.error(f"Render error: {e}")
        return RenderResult.error(f"渲染失败: {str(e)}")


def _record_render_metrics(start_time: float, render_type: str, success: bool, error_msg: str = "") -> None:
    """Record render performance metrics."""
    try:
        import time
        from services.observability import record_render_time, record_error
        duration_ms = (time.time() - start_time) * 1000
        record_render_time(duration_ms, render_type)

        if not success:
            record_error(f"render_{render_type}", error_msg)
    except ImportError:
        pass


def _render_empty_page(options: RenderOptions) -> str:
    """Render empty page placeholder."""
    return f"""
    <div style="
        width_cm: 100%;
        height_cm: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: {options.background_color};
        border: 2px dashed #ccc;
        border-radius: 8px;
        font-family: {options.hanzi_font_family}, sans-serif;
        font-size: {options.font_hanzi_pt}px;
        color: #666;
    ">
        <div style="text-align: center;">
            <div style="font-size: 48px; margin-bottom: 16px;">📝</div>
            <div>请输入文本以生成卡片预览</div>
        </div>
    </div>
    """


def _generate_html_content(cards: List[Dict[str, str]],
                          options: RenderOptions,
                          pagination_info: PaginateInfo) -> str:
    """Generate HTML content for cards."""
    # Page dimensions
    if options.page_size == 'A4':
        page_width_cm, page_height_cm = 21.0, 29.7
    else:  # Letter
        page_width_cm, page_height_cm = 21.59, 27.94
    
    # Calculate actual card size if auto_fill is enabled
    if options.layout_auto_fill:
        available_width = page_width_cm - 2 * options.margin_cm
        available_height = page_height_cm - 2 * options.margin_cm
        
        card_width = (available_width - (options.layout_cols - 1) * options.gap_cm) / options.layout_cols
        card_height = (available_height - (options.layout_rows - 1) * options.gap_cm) / options.layout_rows
        
        actual_card_size = min(card_width, card_height)
    else:
        actual_card_size = options.card_size_cm
    
    # Generate CSS
    css = _generate_css(options, actual_card_size, page_width_cm, page_height_cm)
    
    # Generate card HTML
    cards_html = _generate_cards_html(cards, options, actual_card_size)
    
    # Combine into full HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Chinese Learning Cards</title>
        <style>{css}</style>
    </head>
    <body>
        <div class="page">
            <div class="cards-container">
                {cards_html}
            </div>
            {_generate_page_footer(options, pagination_info)}
        </div>
    </body>
    </html>
    """
    
    return html


def _generate_css(options: RenderOptions, card_size_cm: float, 
                 page_width_cm: float, page_height_cm: float) -> str:
    """Generate CSS styles for the page."""
    return f"""
        @page {{
            size: {options.page_size};
            margin_cm: {options.margin_cm}cm;
        }}
        
        body {{
            margin_cm: 0;
            padding: 0;
            font-family: {options.hanzi_font_family}, sans-serif;
            background-color: {options.background_color};
        }}
        
        .page {{
            width_cm: {page_width_cm}cm;
            height_cm: {page_height_cm}cm;
            margin_cm: 0 auto;
            padding: {options.margin_cm}cm;
            box-sizing: border-box;
            background-color: {options.background_color};
        }}
        
        .cards-container {{
            display: grid;
            grid-template-columns: repeat({options.layout_cols}, 1fr);
            grid-template-layout_rows: repeat({options.layout_rows}, 1fr);
            gap_cm: {options.gap_cm}cm;
            width_cm: 100%;
            height_cm: calc(100% - 2cm);
        }}
        
        .card {{
            width_cm: {card_size_cm}cm;
            height_cm: {card_size_cm}cm;
            border: 2px solid #333;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 0.5cm;
            box-sizing: border-box;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .hanzi {{
            font-size: {options.font_hanzi_pt}pt;
            font-weight: bold;
            color: #000;
            margin-bottom: 0.2cm;
            line-height_cm: 1.2;
        }}
        
        .pinyin {{
            font-size: {options.font_pinyin_pt}pt;
            color: #666;
            margin-bottom: 0.2cm;
            line-height_cm: 1.2;
        }}
        
        .english {{
            font-size: {options.font_english_pt}pt;
            color: #333;
            line-height_cm: 1.2;
        }}
        
        .page-footer {{
            position: absolute;
            bottom: 0.5cm;
            left: 50%;
            transform: translateX(-50%);
            font-size: 10pt;
            color: #666;
        }}
        
        @media print {{
            .page {{
                page-break-after: always;
            }}
            
            .page:last-child {{
                page-break-after: avoid;
            }}
        }}
    """


def _generate_cards_html(cards: List[Dict[str, str]], 
                        options: RenderOptions, 
                        card_size_cm: float) -> str:
    """Generate HTML for individual cards."""
    cards_html = []
    
    for card in cards:
        hanzi = card.get('hanzi', '').strip()
        pinyin = card.get('pinyin', '').strip()
        english = card.get('english', '').strip()
        
        card_html = f"""
        <div class="card">
            <div class="hanzi">{hanzi}</div>
            <div class="pinyin">{pinyin}</div>
            <div class="english">{english}</div>
        </div>
        """
        cards_html.append(card_html)
    
    # Fill remaining slots with empty cards if needed
    total_slots = options.layout_rows * options.layout_cols
    while len(cards_html) < total_slots:
        cards_html.append('<div class="card"></div>')
    
    return '\n'.join(cards_html)


def _generate_page_footer(options: RenderOptions,
                         pagination_info: PaginateInfo) -> str:
    """Generate page footer with page numbers if enabled."""
    if not options.include_page_numbers:
        return ""
    
    return f"""
    <div class="page-footer">
        第 1 页，共 {pagination_info.total_pages} 页
    </div>
    """


def create_render_options_from_legacy(card_size_cm: float, gap_cm: float, margin_cm: float,
                                    hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                                    page_size: str, hanzi_font_family: str, background_color: str,
                                    layout_rows: int, layout_cols: int, layout_auto_fill: bool,
                                    **kwargs) -> RenderOptions:
    """Create RenderOptions from legacy parameter format."""
    return RenderOptions(
        card_size_cm=card_size,
        gap_cm=gap,
        margin_cm=margin,
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=layout_auto_fill,
        page_size=page_size,
        font_hanzi_pt=hanzi_font_size,
        font_pinyin_pt=pinyin_font_size,
        font_english_pt=english_font_size,
        hanzi_font_family=hanzi_font_family,
        background_color=background_color,
        include_page_numbers=kwargs.get('include_page_numbers', True),
        optimize_for_print=kwargs.get('optimize_for_print', True)
    )


def render_cards_unified(cards: List[Dict[str, str]], options: RenderOptions,
                        output_format: str = 'html') -> RenderResult:
    """
    Unified rendering function for all output formats.
    This is the main entry point for all rendering operations.

    Args:
        cards: List of card dictionaries
        options: Render options
        output_format: Output format ('html', 'pdf', 'pptx')

    Returns:
        RenderResult with content appropriate for the format
    """
    try:
        if output_format.lower() == 'html':
            # HTML rendering for preview
            return render_page(cards, options)
        elif output_format.lower() == 'pdf':
            # PDF rendering
            return render_pdf_unified(cards, options)
        elif output_format.lower() == 'pptx':
            # PPTX rendering
            return render_pptx_unified(cards, options)
        else:
            return RenderResult.error(f"Unsupported output format: {output_format}")

    except Exception as e:
        logging.error(f"Unified render error: {e}")
        return RenderResult.error(f"渲染失败: {str(e)}")


def render_cards_unified_legacy(cards: List[Dict[str, str]], **kwargs) -> RenderResult:
    """
    Legacy compatibility function that accepts old parameter format.
    """
    try:
        # Convert legacy parameters to RenderOptions
        options = create_render_options_from_legacy(**kwargs)

        # Use core rendering function
        return render_page(cards, options)

    except Exception as e:
        logging.error(f"Unified render error: {e}")
        return RenderResult.error(f"渲染失败: {str(e)}")


def render_pdf_unified(cards: List[Dict[str, str]], options: RenderOptions) -> RenderResult:
    """
    Unified PDF rendering using shared render core.
    """
    try:
        import tempfile
        from src.layout_pdf import PDFCardGenerator

        # Create temporary file
        tmp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        tmp_file_path = tmp_file.name
        tmp_file.close()

        # Create PDF generator with unified options
        generator = PDFCardGenerator(
            page_size=options.page_size,
            card_size_cm=options.card_size_cm,
            gap_cm=options.gap_cm,
            margin_cm=options.margin_cm,
            layout_rows=options.layout_rows,
            layout_cols=options.layout_cols,
            layout_auto_fill=options.layout_auto_fill
        )

        # Generate PDF
        success = generator.generate_pdf(
            cards, tmp_file_path,
            hanzi_font_size=options.font_hanzi_pt,
            pinyin_font_size=options.font_pinyin_pt,
            english_font_size=options.font_english_pt
        )

        if not success:
            return RenderResult.error("PDF生成失败")

        # Read file content
        with open(tmp_file_path, 'rb') as f:
            content = f.read()

        # Clean up
        import os
        os.unlink(tmp_file_path)

        # Calculate pagination info
        pagination_info = paginate(len(cards), options.layout_rows, options.layout_cols)

        return RenderResult(
            content=content,  # Binary content for PDF
            page_count=pagination_info.total_pages,
            card_count=len(cards),
            pagination_info=pagination_info
        )

    except Exception as e:
        logging.error(f"PDF render error: {e}")
        return RenderResult.error(f"PDF渲染失败: {str(e)}")


def render_pptx_unified(cards: List[Dict[str, str]], options: RenderOptions) -> RenderResult:
    """
    Unified PPTX rendering using shared render core.
    """
    try:
        import tempfile
        from src.layout_pptx import PPTXCardGenerator

        # Create temporary file
        tmp_file = tempfile.NamedTemporaryFile(suffix='.pptx', delete=False)
        tmp_file_path = tmp_file.name
        tmp_file.close()

        # Create PPTX generator with unified options
        generator = PPTXCardGenerator(
            page_size=options.page_size,
            card_size_cm=options.card_size_cm,
            gap_cm=options.gap_cm,
            margin_cm=options.margin_cm,
            layout_rows=options.layout_rows,
            layout_cols=options.layout_cols,
            layout_auto_fill=options.layout_auto_fill
        )

        # Generate PPTX
        success = generator.generate_pptx(
            cards, tmp_file_path,
            hanzi_font_size=options.font_hanzi_pt,
            pinyin_font_size=options.font_pinyin_pt,
            english_font_size=options.font_english_pt
        )

        if not success:
            return RenderResult.error("PPTX生成失败")

        # Read file content
        with open(tmp_file_path, 'rb') as f:
            content = f.read()

        # Clean up
        import os
        os.unlink(tmp_file_path)

        # Calculate pagination info
        pagination_info = paginate(len(cards), options.layout_rows, options.layout_cols)

        return RenderResult(
            content=content,  # Binary content for PPTX
            page_count=pagination_info.total_pages,
            card_count=len(cards),
            pagination_info=pagination_info
        )

    except Exception as e:
        logging.error(f"PPTX render error: {e}")
        return RenderResult.error(f"PPTX渲染失败: {str(e)}")


# Export main functions
__all__ = [
    'RenderOptions',
    'RenderResult',
    'render_page',
    'render_cards_unified',
    'render_cards_unified_legacy',
    'render_pdf_unified',
    'render_pptx_unified',
    'create_render_options_from_legacy'
]
