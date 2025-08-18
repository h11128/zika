#!/usr/bin/env python3
"""
Cross-Module Integration Tests for Chinese Learning Cards Application

Tests integration between different modules and services:
1. Services integration (processing + export + cache)
2. Core state management integration
3. UI components integration with services
4. Data flow between modules
5. Configuration and constants integration
"""

import os
import sys
import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Any

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, generate_missing_data
from services.export import export_cards
from services.cache import create_page_preview_html, create_simple_grid_html
from src.dict_utils import create_default_dict
from core.constants import (
    DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE, DEFAULT_GAP, DEFAULT_MARGIN,
    DEFAULT_FONT_HANZI, DEFAULT_FONT_PINYIN, DEFAULT_FONT_ENGLISH,
    DEFAULT_HANZI_FONT, DEFAULT_BACKGROUND_COLOR, PRESET_COLORS
)


class TestServicesIntegration:
    """Test integration between different service modules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': '', 'english': ''},
            {'hanzi': '朋友', 'pinyin': '', 'english': ''}
        ]
    
    def test_processing_to_cache_integration(self):
        """Test integration between processing service and cache service."""
        # Process cards
        processed_cards = generate_missing_data(
            self.sample_cards, auto_pinyin=True, auto_translate=True, 
            dictionary=self.dictionary
        )
        
        # Generate cached HTML with processed data
        simple_html = create_simple_grid_html(
            processed_cards, 
            hanzi_font=DEFAULT_HANZI_FONT,
            background_color=DEFAULT_BACKGROUND_COLOR
        )
        
        # Verify integration
        assert simple_html
        for card in processed_cards:
            assert card['hanzi'] in simple_html
            assert card['pinyin'] in simple_html
            assert card['english'] in simple_html
        
        # Test page preview integration
        page_html = create_page_preview_html(
            processed_cards, page_num=0,
            card_size=DEFAULT_CARD_SIZE, gap=DEFAULT_GAP, margin=DEFAULT_MARGIN,
            font_hanzi=DEFAULT_FONT_HANZI, font_pinyin=DEFAULT_FONT_PINYIN,
            font_english=DEFAULT_FONT_ENGLISH, page_size=DEFAULT_PAGE_SIZE
        )
        
        assert page_html
        assert 'page-card' in page_html
        assert '第 1 页' in page_html
    
    def test_processing_to_export_integration(self):
        """Test integration between processing service and export service."""
        # Process cards
        processed_cards = generate_missing_data(
            self.sample_cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Export processed cards to both formats
        pptx_content = export_cards(
            processed_cards, 'pptx',
            page_size=DEFAULT_PAGE_SIZE,
            card_size=DEFAULT_CARD_SIZE,
            gap=DEFAULT_GAP,
            margin=DEFAULT_MARGIN,
            font_hanzi=DEFAULT_FONT_HANZI,
            font_pinyin=DEFAULT_FONT_PINYIN,
            font_english=DEFAULT_FONT_ENGLISH,
            hanzi_font=DEFAULT_HANZI_FONT,
            background_color=DEFAULT_BACKGROUND_COLOR
        )
        
        pdf_content = export_cards(
            processed_cards, 'pdf',
            page_size=DEFAULT_PAGE_SIZE,
            card_size=DEFAULT_CARD_SIZE,
            gap=DEFAULT_GAP,
            margin=DEFAULT_MARGIN,
            font_hanzi=DEFAULT_FONT_HANZI,
            font_pinyin=DEFAULT_FONT_PINYIN,
            font_english=DEFAULT_FONT_ENGLISH
        )
        
        # Verify both exports work with processed data
        assert isinstance(pptx_content, (bytes, bytearray))
        assert isinstance(pdf_content, (bytes, bytearray))
        assert len(pptx_content) > 1000
        assert len(pdf_content) > 1000
    
    def test_cache_consistency_across_calls(self):
        """Test cache consistency when called with same parameters."""
        processed_cards = generate_missing_data(
            self.sample_cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Generate HTML multiple times with same parameters
        html1 = create_simple_grid_html(
            processed_cards, hanzi_font='SimHei', background_color='#E3F2FD'
        )
        html2 = create_simple_grid_html(
            processed_cards, hanzi_font='SimHei', background_color='#E3F2FD'
        )
        
        # Should be identical (cache working)
        assert html1 == html2
        
        # Different parameters should produce different results
        html3 = create_simple_grid_html(
            processed_cards, hanzi_font='Microsoft YaHei', background_color='#FFEBEE'
        )
        
        assert html1 != html3
        assert '#E3F2FD' in html1
        assert '#FFEBEE' in html3


class TestConstantsIntegration:
    """Test integration of constants across modules."""
    
    def test_constants_used_consistently_across_modules(self):
        """Test that constants are used consistently across all modules."""
        # Test that export service uses constants correctly
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Export with default constants
        content = export_cards(cards, 'pptx')
        assert isinstance(content, (bytes, bytearray))
        
        # Test that cache service uses constants correctly
        html = create_simple_grid_html(cards)
        assert DEFAULT_HANZI_FONT in html or 'font-family' in html
        assert DEFAULT_BACKGROUND_COLOR in html
    
    def test_preset_colors_integration(self):
        """Test that preset colors work across modules."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]

        # Test each preset color in cache service
        for color_value in PRESET_COLORS[:5]:  # Test first 5 colors for speed
            html = create_simple_grid_html(cards, background_color=color_value)
            assert color_value in html

            # Test in page preview
            page_html = create_page_preview_html(
                cards, page_num=0, card_size=5.5, gap=0.5, margin=1.0,
                font_hanzi=48, font_pinyin=18, font_english=14,
                background_color=color_value
            )
            assert color_value in page_html


class TestDataFlowIntegration:
    """Test data flow between modules."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.dictionary = create_default_dict("data")
    
    def test_complete_data_flow_pipeline(self):
        """Test complete data flow from input to output."""
        # Input text
        input_text = "爱 家 朋友"
        
        # Step 1: Parse input
        cards = parse_input_text(input_text)
        assert len(cards) == 3
        
        # Step 2: Process with dictionary
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Verify data enrichment
        for card in processed_cards:
            assert card['pinyin']
            assert card['english']
        
        # Step 3: Generate preview
        preview_html = create_simple_grid_html(processed_cards)
        assert preview_html
        
        # Step 4: Export
        export_content = export_cards(processed_cards, 'pptx')
        assert isinstance(export_content, (bytes, bytearray))
        
        # Verify data integrity throughout pipeline
        hanzi_values = [card['hanzi'] for card in processed_cards]
        assert '爱' in hanzi_values
        assert '家' in hanzi_values
        assert '朋友' in hanzi_values
    
    def test_data_transformation_consistency(self):
        """Test that data transformations are consistent across modules."""
        original_cards = [
            {'hanzi': '爱', 'pinyin': '', 'english': ''},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}  # Partial data
        ]
        
        # Process cards
        processed_cards = generate_missing_data(
            original_cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Verify existing data is preserved
        home_card = next(card for card in processed_cards if card['hanzi'] == '家')
        assert home_card['pinyin'] == 'jiā'  # Should preserve existing
        assert home_card['english'] == 'home'  # Should preserve existing
        
        # Verify missing data is generated
        love_card = next(card for card in processed_cards if card['hanzi'] == '爱')
        assert love_card['pinyin']  # Should be generated
        assert love_card['english']  # Should be generated
    
    def test_error_propagation_through_pipeline(self):
        """Test how errors propagate through the data pipeline."""
        # Test with invalid input
        invalid_cards = [{'hanzi': '', 'pinyin': '', 'english': ''}]
        
        # Should handle gracefully
        processed_cards = generate_missing_data(
            invalid_cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Should not crash preview generation
        html = create_simple_grid_html(processed_cards)
        assert isinstance(html, str)
        
        # Should not crash export (though may produce empty/minimal file)
        content = export_cards(processed_cards, 'pptx')
        assert isinstance(content, (bytes, bytearray))


class TestConfigurationIntegration:
    """Test configuration integration across modules."""
    
    def test_font_configuration_integration(self):
        """Test font configuration across modules."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Test different font configurations
        fonts = ['SimHei', 'Microsoft YaHei', 'NSimSun']
        
        for font in fonts:
            # Test in cache service
            html = create_simple_grid_html(cards, hanzi_font=font)
            assert font in html or 'font-family' in html
            
            # Test in export service
            content = export_cards(cards, 'pptx', hanzi_font=font)
            assert isinstance(content, (bytes, bytearray))
    
    def test_layout_configuration_integration(self):
        """Test layout configuration across modules."""
        cards = [{'hanzi': str(i), 'pinyin': f'p{i}', 'english': f'e{i}'} 
                for i in range(12)]  # More than one page
        
        # Test different layout configurations
        layouts = [
            {'rows': 2, 'cols': 2, 'card_size': 4.0},
            {'rows': 3, 'cols': 3, 'card_size': 5.5},
            {'rows': 4, 'cols': 3, 'card_size': 3.5}
        ]
        
        for layout in layouts:
            # Test in preview
            html = create_page_preview_html(
                cards, page_num=0, card_size=layout['card_size'],
                gap=0.5, margin=1.0, font_hanzi=48, font_pinyin=18,
                font_english=14, rows=layout['rows'], cols=layout['cols']
            )
            assert html
            
            # Test in export
            content = export_cards(
                cards, 'pptx', 
                card_size=layout['card_size'],
                rows=layout['rows'], 
                cols=layout['cols']
            )
            assert isinstance(content, (bytes, bytearray))
    
    def test_page_size_configuration_integration(self):
        """Test page size configuration across modules."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        page_sizes = ['A4', 'Letter']
        
        for page_size in page_sizes:
            # Test in preview
            html = create_page_preview_html(
                cards, page_num=0, card_size=5.5, gap=0.5, margin=1.0,
                font_hanzi=48, font_pinyin=18, font_english=14,
                page_size=page_size
            )
            assert html
            
            # Test in export
            for format_type in ['pptx', 'pdf']:
                content = export_cards(cards, format_type, page_size=page_size)
                assert isinstance(content, (bytes, bytearray))
