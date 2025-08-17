#!/usr/bin/env python3
"""
Chinese Character Learning Cards Generator

Main CLI script for generating printable learning cards from Chinese word lists.
Supports automatic pinyin and translation generation, outputs to PPTX/PDF formats.
"""

import argparse
import csv
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pinyin_utils import hanzi_to_pinyin, contains_chinese
from dict_utils import create_default_dict
from layout_pptx import PPTXCardGenerator
from layout_pdf import PDFCardGenerator


class CardGenerator:
    """Main card generation orchestrator."""
    
    def __init__(self, dict_path: Optional[str] = None):
        """
        Initialize the card generator.
        
        Args:
            dict_path: Path to dictionary file (optional)
        """
        # Initialize dictionary
        if dict_path and os.path.exists(dict_path):
            data_dir = os.path.dirname(dict_path)
            self.dictionary = create_default_dict(data_dir)
        else:
            # Use default data directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(os.path.dirname(script_dir), "data")
            self.dictionary = create_default_dict(data_dir)
    
    def read_input_file(self, input_path: str) -> List[Dict[str, str]]:
        """
        Read input file (CSV/TSV) and return list of word entries.
        
        Args:
            input_path: Path to input file
            
        Returns:
            List of dictionaries with 'hanzi', 'pinyin', 'english' keys
        """
        cards = []
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                # Detect delimiter
                sample = f.read(1024)
                f.seek(0)
                
                if '\t' in sample:
                    delimiter = '\t'
                else:
                    delimiter = ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                # Handle different column name variations
                fieldnames = reader.fieldnames or []
                hanzi_col = self._find_column(fieldnames, ['hanzi', 'chinese', 'word', 'character'])
                pinyin_col = self._find_column(fieldnames, ['pinyin', 'pronunciation', 'reading'])
                english_col = self._find_column(fieldnames, ['english', 'translation', 'meaning', 'definition'])
                
                if not hanzi_col:
                    # If no headers found, assume first column is hanzi
                    if len(fieldnames) >= 1:
                        hanzi_col = fieldnames[0]
                    else:
                        raise ValueError("Could not determine hanzi column")
                
                for row_num, row in enumerate(reader, 1):
                    hanzi = row.get(hanzi_col, '').strip()
                    
                    if not hanzi:
                        continue
                    
                    # Validate that hanzi contains Chinese characters
                    if not contains_chinese(hanzi):
                        print(f"Warning: Row {row_num} does not contain Chinese characters: {hanzi}")
                        continue
                    
                    card = {
                        'hanzi': hanzi,
                        'pinyin': row.get(pinyin_col, '').strip() if pinyin_col else '',
                        'english': row.get(english_col, '').strip() if english_col else ''
                    }
                    
                    cards.append(card)
                    
        except Exception as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)
        
        return cards
    
    def _find_column(self, fieldnames: List[str], candidates: List[str]) -> Optional[str]:
        """Find column name from candidates."""
        fieldnames_lower = [f.lower() for f in fieldnames]
        for candidate in candidates:
            if candidate.lower() in fieldnames_lower:
                idx = fieldnames_lower.index(candidate.lower())
                return fieldnames[idx]
        return None
    
    def process_cards(self, cards: List[Dict[str, str]], auto_pinyin: bool = True, 
                     auto_translate: bool = True, heteronym: bool = False) -> List[Dict[str, str]]:
        """
        Process cards by adding missing pinyin and translations.
        
        Args:
            cards: List of card dictionaries
            auto_pinyin: Whether to auto-generate pinyin
            auto_translate: Whether to auto-generate translations
            heteronym: Whether to show multiple pronunciations
            
        Returns:
            Processed list of cards
        """
        processed_cards = []
        
        for i, card in enumerate(cards):
            processed_card = card.copy()
            
            # Generate pinyin if missing
            if auto_pinyin and not processed_card['pinyin']:
                pinyin = hanzi_to_pinyin(processed_card['hanzi'], heteronym=heteronym)
                processed_card['pinyin'] = pinyin
                print(f"Generated pinyin for '{processed_card['hanzi']}': {pinyin}")
            
            # Generate translation if missing
            if auto_translate and not processed_card['english']:
                translation = self.dictionary.lookup_translation(processed_card['hanzi'])
                if translation:
                    processed_card['english'] = translation
                    print(f"Generated translation for '{processed_card['hanzi']}': {translation}")
                else:
                    print(f"Warning: No translation found for '{processed_card['hanzi']}'")
            
            processed_cards.append(processed_card)
        
        return processed_cards
    
    def generate_output(self, cards: List[Dict[str, str]], output_path: str, 
                       format_type: str, **layout_options) -> bool:
        """
        Generate output file in specified format.
        
        Args:
            cards: List of processed cards
            output_path: Output file path
            format_type: Output format ('pptx' or 'pdf')
            **layout_options: Layout configuration options
            
        Returns:
            True if successful
        """
        try:
            if format_type.lower() == 'pptx':
                generator = PPTXCardGenerator(
                    page_size=layout_options.get('page_size', 'A4'),
                    card_size_cm=layout_options.get('card_size', 6.0),
                    gap_cm=layout_options.get('gap', 0.6),
                    margin_cm=layout_options.get('margin', 1.0)
                )
                
                return generator.generate_pptx(
                    cards, output_path,
                    font_hanzi=layout_options.get('font_hanzi', 48),
                    font_pinyin=layout_options.get('font_pinyin', 18),
                    font_english=layout_options.get('font_english', 14)
                )
                
            elif format_type.lower() == 'pdf':
                generator = PDFCardGenerator(
                    page_size=layout_options.get('page_size', 'A4'),
                    card_size_cm=layout_options.get('card_size', 6.0),
                    gap_cm=layout_options.get('gap', 0.6),
                    margin_cm=layout_options.get('margin', 1.0)
                )
                
                return generator.generate_pdf(
                    cards, output_path,
                    font_hanzi=layout_options.get('font_hanzi', 48),
                    font_pinyin=layout_options.get('font_pinyin', 18),
                    font_english=layout_options.get('font_english', 14)
                )
            
            else:
                print(f"Unsupported format: {format_type}")
                return False
                
        except Exception as e:
            print(f"Error generating {format_type.upper()}: {e}")
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate Chinese character learning cards",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate PPTX with auto pinyin and translation
  python gen_cards.py --in words.csv --out cards.pptx --format pptx --auto-pinyin --auto-translate
  
  # Generate PDF with custom layout
  python gen_cards.py --in words.csv --out cards.pdf --format pdf --card-size 5 --gap 0.8
  
  # Show multiple pronunciations for polyphonic characters
  python gen_cards.py --in words.csv --out cards.pptx --format pptx --heteronym
        """
    )
    
    # Input/Output options
    parser.add_argument('--in', '--input', dest='input_file', required=True,
                       help='Input CSV/TSV file with Chinese words')
    parser.add_argument('--out', '--output', dest='output_file', required=True,
                       help='Output file path')
    parser.add_argument('--format', choices=['pptx', 'pdf'], default='pptx',
                       help='Output format (default: pptx)')
    
    # Processing options
    parser.add_argument('--auto-pinyin', action='store_true',
                       help='Auto-generate pinyin for missing entries')
    parser.add_argument('--auto-translate', action='store_true',
                       help='Auto-generate English translations for missing entries')
    parser.add_argument('--heteronym', action='store_true',
                       help='Show multiple pronunciations for polyphonic characters')
    parser.add_argument('--dict', dest='dict_path',
                       help='Path to dictionary file (default: data/mini_cedict.json)')
    
    # Layout options
    parser.add_argument('--page', choices=['A4', 'Letter'], default='A4',
                       help='Page size (default: A4)')
    parser.add_argument('--card-size', type=float, default=5.5,
                       help='Card size in cm (default: 5.5)')
    parser.add_argument('--gap', type=float, default=0.5,
                       help='Gap between cards in cm (default: 0.5)')
    parser.add_argument('--margin', type=float, default=1.0,
                       help='Page margin in cm (default: 1.0)')
    
    # Font options
    parser.add_argument('--font-hanzi', type=int, default=48,
                       help='Font size for Chinese characters (default: 48)')
    parser.add_argument('--font-pinyin', type=int, default=18,
                       help='Font size for pinyin (default: 18)')
    parser.add_argument('--font-en', '--font-english', dest='font_english', type=int, default=14,
                       help='Font size for English (default: 14)')
    
    args = parser.parse_args()
    
    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    
    # Create output directory if needed
    output_dir = os.path.dirname(args.output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Initialize generator
    generator = CardGenerator(args.dict_path)
    
    print(f"Reading input file: {args.input_file}")
    cards = generator.read_input_file(args.input_file)
    print(f"Loaded {len(cards)} cards")
    
    if not cards:
        print("No valid cards found in input file")
        sys.exit(1)
    
    # Process cards
    print("Processing cards...")
    processed_cards = generator.process_cards(
        cards, 
        auto_pinyin=args.auto_pinyin,
        auto_translate=args.auto_translate,
        heteronym=args.heteronym
    )
    
    # Generate output
    layout_options = {
        'page_size': args.page,
        'card_size': args.card_size,
        'gap': args.gap,
        'margin': args.margin,
        'font_hanzi': args.font_hanzi,
        'font_pinyin': args.font_pinyin,
        'font_english': args.font_english
    }
    
    print(f"Generating {args.format.upper()} output: {args.output_file}")
    success = generator.generate_output(processed_cards, args.output_file, args.format, **layout_options)
    
    if success:
        print(f"Successfully generated {len(processed_cards)} cards in {args.format.upper()} format")
        print(f"Output saved to: {args.output_file}")
    else:
        print("Failed to generate output")
        sys.exit(1)


if __name__ == "__main__":
    main()
