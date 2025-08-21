"""
Processing service for the Chinese Character Learning Cards application.
Pure functions for text parsing and data generation without UI dependencies.
"""

import re
import jieba
from typing import List, Dict
from src.pinyin_utils import hanzi_to_pinyin, contains_chinese
from .translation import translate_with_google, clean_english_text



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
        if auto_translate and not processed_card['english']:
            hanzi = processed_card.get('hanzi', '')
            translation = None

            # 1) Local dictionary first
            if dictionary is not None:
                try:
                    translation = dictionary.lookup_translation(hanzi)
                except Exception:
                    translation = None

            translation = clean_english_text(translation) if translation else None

            # 2) Fallback to Google Translate if needed
            if not translation:
                google_trans = translate_with_google(hanzi)
                if google_trans:
                    translation = google_trans

            if translation:
                processed_card['english'] = translation

        processed_cards.append(processed_card)

    return processed_cards


def generate_missing_data_ordered(cards: List[Dict[str, str]], auto_pinyin: bool, auto_translate: bool, dictionary=None, translate_order: str = 'local_first') -> List[Dict[str, str]]:
    """Generate missing pinyin and translations with configurable translate order.

    translate_order options:
      - 'local_first' (default): local dict -> Google
      - 'google_first': Google -> local dict
      - 'local_only': local dict only
      - 'google_only': Google only
      - 'mixed': local + Google, combined result
    """
    order = (translate_order or 'local_first').lower()
    processed_cards = []

    for card in cards:
        processed_card = card.copy()

        # Pinyin
        if auto_pinyin and not processed_card.get('pinyin'):
            processed_card['pinyin'] = hanzi_to_pinyin(processed_card.get('hanzi', ''))

        # Translation
        if auto_translate and not processed_card.get('english'):
            hanzi = processed_card.get('hanzi', '')
            translation = None

            def try_local():
                if dictionary is None:
                    return None
                try:
                    t = dictionary.lookup_translation(hanzi)
                    return clean_english_text(t) if t else None
                except Exception:
                    return None

            def try_google():
                t = translate_with_google(hanzi)
                return t if t else None

            if order == 'google_first':
                translation = try_google() or try_local()
            elif order == 'local_only':
                translation = try_local()
            elif order == 'google_only':
                translation = try_google()
            elif order == 'mixed':
                # Combine both sources
                local_trans = try_local()
                google_trans = try_google()
                if local_trans and google_trans and local_trans != google_trans:
                    translation = f"{local_trans} | {google_trans}"
                else:
                    translation = local_trans or google_trans
            else:  # local_first
                translation = try_local() or try_google()

            if translation:
                processed_card['english'] = translation

        processed_cards.append(processed_card)

    return processed_cards

