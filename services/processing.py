"""
Processing service for the Chinese Character Learning Cards application.
Pure functions for text parsing and data generation without UI dependencies.
"""

import re
import jieba
from typing import List, Dict
from src.pinyin_utils import hanzi_to_pinyin, contains_chinese


def parse_input_text(text: str) -> List[Dict[str, str]]:
    """Parse space-separated Chinese characters into card data."""
    if not text.strip():
        return []

    cards = []
    words = [word.strip() for word in text.split() if word.strip()]

    for word in words:
        if contains_chinese(word):
            cards.append({
                'hanzi': word,
                'pinyin': '',
                'english': ''
            })

    return cards


def auto_segment_text(text: str) -> str:
    """Automatically segment Chinese text into words/characters."""
    if not text.strip():
        return ""

    # Remove existing spaces and punctuation
    text = re.sub(r'[^\u4e00-\u9fff]', '', text)

    if not text:
        return ""

    # Use jieba for initial segmentation
    segments = list(jieba.cut(text, cut_all=False))

    # Post-process: split long words and handle single characters
    final_segments = []
    for segment in segments:
        if len(segment) == 1:
            # Single character - keep as is
            final_segments.append(segment)
        elif len(segment) == 2:
            # Two characters - usually a word, keep as is
            final_segments.append(segment)
        elif len(segment) >= 3:
            # Long segment - check if it should be split
            # For learning cards, prefer shorter segments
            if len(segment) <= 4:
                # Keep 3-4 character words
                final_segments.append(segment)
            else:
                # Split longer segments into smaller parts
                # Try to split into 2-character words first
                for i in range(0, len(segment), 2):
                    if i + 1 < len(segment):
                        final_segments.append(segment[i:i+2])
                    else:
                        final_segments.append(segment[i])

    # Remove duplicates while preserving order
    seen = set()
    unique_segments = []
    for segment in final_segments:
        if segment not in seen:
            seen.add(segment)
            unique_segments.append(segment)

    return " ".join(unique_segments)


def generate_missing_data(cards: List[Dict[str, str]], auto_pinyin: bool, auto_translate: bool, dictionary=None) -> List[Dict[str, str]]:
    """Generate missing pinyin and translations."""
    processed_cards = []

    for card in cards:
        processed_card = card.copy()

        # Generate pinyin if missing and enabled
        if auto_pinyin and not processed_card['pinyin']:
            pinyin = hanzi_to_pinyin(processed_card['hanzi'])
            processed_card['pinyin'] = pinyin

        # Generate translation if missing and enabled
        if auto_translate and not processed_card['english'] and dictionary:
            translation = dictionary.lookup_translation(processed_card['hanzi'])
            if translation:
                processed_card['english'] = translation

        processed_cards.append(processed_card)

    return processed_cards
