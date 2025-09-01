#!/usr/bin/env python3
"""
End-to-End Integration Tests for Chinese Learning Cards Application

Tests complete user workflows from input to export, covering:
1. Text input processing workflow
2. CSV upload and processing workflow  
3. Complete export workflow (PPTX/PDF)
4. Real-time preview generation workflow
5. Error handling and recovery workflows
"""

import os
import sys
import tempfile
import pytest
import csv
from io import StringIO
from pathlib import Path

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, auto_segment_text, generate_missing_data
from services.export import export_cards
from services.cache_v2 import create_page_preview_html_v2, create_simple_grid_html_v2
from services.preview_types import LayoutOptions, Typography, VisualOptions

# Helper functions for v2 API compatibility
def create_page_preview_html(cards, page_num=0, card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
                           hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
                           layout_rows=2, layout_cols=3, hanzi_font_family="SimSun",
                           background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=layout_rows,
        layout_cols=layout_cols,
        layout_auto_fill=True,
        card_size_cm=card_size_cm,
        gap_cm=gap_cm,
        margin_cm=margin_cm,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=hanzi_font_size,
        pinyin_font_size_pt=pinyin_font_size,
        english_font_size_pt=english_font_size,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='📄 完整页面'
    )
    return create_page_preview_html_v2(cards, page_num, layout, typography, visual)

def create_simple_grid_html(cards, hanzi_font_family="SimSun", background_color="#FFFFFF", **kwargs):
    """Compatibility wrapper for v2 API."""
    layout = LayoutOptions(
        layout_rows=2,
        layout_cols=3,
        layout_auto_fill=True,
        card_size_cm=5.5,
        gap_cm=0.5,
        margin_cm=1.0,
        page_size="A4"
    )
    typography = Typography(
        hanzi_font_size_pt=48,
        pinyin_font_size_pt=18,
        english_font_size_pt=14,
        hanzi_font_family=hanzi_font_family
    )
    visual = VisualOptions(
        background_color=background_color,
        preview_mode='🔲 简单网格'
    )
    return create_simple_grid_html_v2(cards, layout, typography, visual)
from src.dict_utils import create_default_dict
from src.pinyin_utils import hanzi_to_pinyin
from core.constants import DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN


class TestEndToEndTextInputWorkflow:
    """Test complete text input to export workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
        self.sample_text = "爱 家 朋友 水 火"
        self.expected_cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': '', 'english': ''},
            {'hanzi': '朋友', 'pinyin': '', 'english': ''},
            {'hanzi': '水', 'pinyin': '', 'english': ''},
            {'hanzi': '火', 'pinyin': '', 'english': ''}
        ]
    
    def test_complete_text_input_to_processed_cards_workflow(self):
        """Test complete workflow from text input to processed cards."""
        # Step 1: Parse input text
        cards = parse_input_text(self.sample_text)
        assert len(cards) == 5
        assert all(card['hanzi'] in ['爱', '家', '朋友', '水', '火'] for card in cards)
        
        # Step 2: Generate missing data
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )
        
        # Verify all cards have pinyin and translations
        for card in processed_cards:
            assert card['pinyin'], f"Missing pinyin for {card['hanzi']}"
            assert card['english'], f"Missing translation for {card['hanzi']}"
            
        # Verify specific expected results
        hanzi_to_card = {card['hanzi']: card for card in processed_cards}
        assert '爱' in hanzi_to_card
        assert 'love' in hanzi_to_card['爱']['english'].lower()
        assert 'ài' in hanzi_to_card['爱']['pinyin']
    
    def test_complete_text_input_to_export_workflow(self):
        """Test complete workflow from text input to file export."""
        # Step 1: Parse and process
        cards = parse_input_text(self.sample_text)
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )
        
        # Step 2: Export to PPTX
        pptx_content = export_cards(
            processed_cards, 'pptx',
            page_size=DEFAULT_PAGE_SIZE,
            card_size_cm=DEFAULT_CARD_SIZE,
            gap_cm=DEFAULT_GAP,
            margin_cm=DEFAULT_MARGIN
        )
        
        assert isinstance(pptx_content, (bytes, bytearray))
        assert len(pptx_content) > 1000  # Reasonable minimum size for PPTX
        
        # Step 3: Export to PDF
        pdf_content = export_cards(
            processed_cards, 'pdf',
            page_size=DEFAULT_PAGE_SIZE,
            card_size_cm=DEFAULT_CARD_SIZE,
            gap_cm=DEFAULT_GAP,
            margin_cm=DEFAULT_MARGIN
        )
        
        assert isinstance(pdf_content, (bytes, bytearray))
        assert len(pdf_content) > 1000  # Reasonable minimum size for PDF
    
    def test_complete_text_input_to_preview_workflow(self):
        """Test complete workflow from text input to HTML preview."""
        # Step 1: Parse and process
        cards = parse_input_text(self.sample_text)
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )
        
        # Step 2: Generate simple grid preview
        simple_html = create_simple_grid_html(
            processed_cards, 
            hanzi_font_family='Microsoft YaHei',
            background_color='#E3F2FD'
        )
        
        assert '<div class="simple-card">' in simple_html
        assert '#E3F2FD' in simple_html
        for card in processed_cards:
            assert card['hanzi'] in simple_html
            assert card['pinyin'] in simple_html
            assert card['english'] in simple_html
        
        # Step 3: Generate page preview
        page_html = create_page_preview_html(
            processed_cards, page_num=0,
            card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0,
            hanzi_font_size=48, pinyin_font_size=18, english_font_size=14,
            page_size='A4', hanzi_font_family='Microsoft YaHei',
            background_color='#E3F2FD'
        )
        
        assert '<div class="page-card">' in page_html
        assert '#E3F2FD' in page_html
        assert '第 1 页' in page_html


class TestEndToEndCSVWorkflow:
    """Test complete CSV upload and processing workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
        self.csv_content = """hanzi,pinyin,english
爱,,love
家,jiā,home
朋友,,friend
水,,
火,huǒ,fire"""
    
    def test_complete_csv_to_processed_cards_workflow(self):
        """Test complete workflow from CSV to processed cards."""
        # Step 1: Parse CSV content
        csv_file = StringIO(self.csv_content)
        reader = csv.DictReader(csv_file)
        cards = []
        
        for row in reader:
            cards.append({
                'hanzi': row.get('hanzi', '').strip(),
                'pinyin': row.get('pinyin', '').strip(),
                'english': row.get('english', '').strip()
            })
        
        assert len(cards) == 5
        
        # Step 2: Generate missing data (respecting existing data)
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )
        
        # Verify existing data is preserved
        hanzi_to_card = {card['hanzi']: card for card in processed_cards}
        
        # Should preserve existing pinyin
        assert hanzi_to_card['家']['pinyin'] == 'jiā'
        assert hanzi_to_card['火']['pinyin'] == 'huǒ'
        
        # Should preserve existing translations
        assert hanzi_to_card['爱']['english'] == 'love'
        assert hanzi_to_card['家']['english'] == 'home'
        assert hanzi_to_card['朋友']['english'] == 'friend'
        assert hanzi_to_card['火']['english'] == 'fire'
        
        # Should generate missing data
        assert hanzi_to_card['朋友']['pinyin']  # Should be generated
        assert hanzi_to_card['水']['pinyin']    # Should be generated
        assert hanzi_to_card['水']['english']   # Should be generated
    
    def test_csv_with_malformed_data_workflow(self):
        """Test CSV workflow with malformed or incomplete data."""
        malformed_csv = """hanzi,pinyin,english
爱,ài,love
,jiā,home
朋友,,
hello,world,english
水
火,huǒ"""
        
        csv_file = StringIO(malformed_csv)
        reader = csv.DictReader(csv_file)
        cards = []
        
        for row in reader:
            hanzi = (row.get('hanzi') or '').strip()
            if hanzi and any('\u4e00' <= char <= '\u9fff' for char in hanzi):
                cards.append({
                    'hanzi': hanzi,
                    'pinyin': (row.get('pinyin') or '').strip(),
                    'english': (row.get('english') or '').strip()
                })
        
        # Should filter out invalid entries (hello, empty hanzi)
        # Valid entries: 爱, 朋友, 水, 火
        assert len(cards) == 4
        hanzi_list = [card['hanzi'] for card in cards]
        assert '爱' in hanzi_list
        assert '朋友' in hanzi_list
        assert '水' in hanzi_list
        assert '火' in hanzi_list
        assert 'hello' not in hanzi_list

        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )

        # All valid cards should be processed
        assert len(processed_cards) == 4
        for card in processed_cards:
            assert card['hanzi'] in ['爱', '朋友', '水', '火']
            assert card['pinyin']
            # English might be empty if not in dictionary


class TestEndToEndSegmentationWorkflow:
    """Test complete text segmentation workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
        self.continuous_text = "我爱我的家人朋友们"
    
    def test_complete_segmentation_to_export_workflow(self):
        """Test complete workflow from continuous text to export."""
        # Step 1: Auto-segment continuous text
        segmented_text = auto_segment_text(self.continuous_text)
        assert segmented_text
        assert ' ' in segmented_text  # Should be space-separated
        
        # Step 2: Parse segmented text
        cards = parse_input_text(segmented_text)
        assert len(cards) > 0
        
        # Step 3: Generate missing data
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=self.dictionary
        )
        
        # Step 4: Export to verify complete pipeline
        export_content = export_cards(
            processed_cards, 'pptx',
            page_size='A4', card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0
        )
        
        assert isinstance(export_content, (bytes, bytearray))
        assert len(export_content) > 1000


class TestEndToEndErrorHandlingWorkflow:
    """Test error handling and recovery in complete workflows."""
    
    def test_empty_input_workflow(self):
        """Test workflow with empty inputs."""
        # Empty text input
        cards = parse_input_text("")
        assert cards == []
        
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=None
        )
        assert processed_cards == []
        
        # Empty segmentation
        segmented = auto_segment_text("")
        assert segmented == ""
    
    def test_invalid_export_format_workflow(self):
        """Test workflow with invalid export format."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        with pytest.raises(ValueError, match="Unsupported format"):
            export_cards(cards, 'invalid_format')
    
    def test_missing_dictionary_workflow(self):
        """Test workflow with missing dictionary."""
        cards = [{'hanzi': '爱', 'pinyin': '', 'english': ''}]
        
        # Should not crash with missing dictionary
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True, dictionary=None
        )
        
        # Should still generate pinyin but not translations
        assert processed_cards[0]['pinyin']  # Pinyin should be generated
        assert not processed_cards[0]['english']  # Translation should remain empty
