"""
Pinyin generation utilities using pypinyin library.
"""

from pypinyin import pinyin, Style
from typing import List, Optional


def hanzi_to_pinyin(text: str, heteronym: bool = False) -> str:
    """
    Convert Chinese characters to pinyin with tone marks, with fallback for compatibility.

    Args:
        text: Chinese text to convert
        heteronym: If True, return multiple pronunciations for polyphonic characters

    Returns:
        Pinyin string with tone marks or numeric tones as fallback
    """
    if not text or not text.strip():
        return ""

    def clean_pinyin_result(py_result, heteronym_mode):
        """Clean and format pinyin result."""
        if heteronym_mode:
            syllables = []
            for syll_list in py_result:
                if len(syll_list) > 1:
                    syllables.append("/".join(syll_list))
                else:
                    syllables.append(syll_list[0])
            return " ".join(syllables)
        else:
            return " ".join(syll[0] for syll in py_result)

    # Try different pinyin styles in order of preference
    styles_to_try = [
        (Style.TONE, "tone marks"),
        (Style.TONE3, "numeric tones"),
        (Style.NORMAL, "no tones")
    ]

    for style, description in styles_to_try:
        try:
            py_result = pinyin(text, style=style, heteronym=heteronym, errors='default')
            result = clean_pinyin_result(py_result, heteronym)

            # Validate result doesn't contain problematic characters
            if result and not any(ord(c) > 65535 for c in result):  # Avoid high Unicode
                return result

        except Exception:
            continue

    # Final fallback: try with strict=False and ignore errors
    try:
        py_result = pinyin(text, style=Style.NORMAL, heteronym=False, strict=False, errors='ignore')
        result = " ".join(syll[0] for syll in py_result if syll)
        if result:
            return result
    except Exception:
        pass

    # Last resort: return original text
    return text


def get_pinyin_variants(text: str) -> List[str]:
    """
    Get all possible pinyin pronunciations for polyphonic characters.
    
    Args:
        text: Chinese text to analyze
        
    Returns:
        List of all possible pinyin combinations
    """
    if not text or not text.strip():
        return []
    
    try:
        py_result = pinyin(text, style=Style.TONE, heteronym=True, errors='default')
        
        # Generate all combinations
        def generate_combinations(syllable_lists):
            if not syllable_lists:
                return [""]
            
            first_list = syllable_lists[0]
            rest_combinations = generate_combinations(syllable_lists[1:])
            
            combinations = []
            for syllable in first_list:
                for rest in rest_combinations:
                    if rest:
                        combinations.append(f"{syllable} {rest}")
                    else:
                        combinations.append(syllable)
            
            return combinations
        
        return generate_combinations(py_result)
        
    except Exception:
        return [hanzi_to_pinyin(text, heteronym=False)]


def is_chinese_char(char: str) -> bool:
    """
    Check if a character is a Chinese character.
    
    Args:
        char: Single character to check
        
    Returns:
        True if the character is Chinese
    """
    if not char:
        return False
    
    # Unicode ranges for Chinese characters
    code = ord(char)
    return (
        0x4e00 <= code <= 0x9fff or  # CJK Unified Ideographs
        0x3400 <= code <= 0x4dbf or  # CJK Extension A
        0x20000 <= code <= 0x2a6df or  # CJK Extension B
        0x2a700 <= code <= 0x2b73f or  # CJK Extension C
        0x2b740 <= code <= 0x2b81f or  # CJK Extension D
        0x2b820 <= code <= 0x2ceaf or  # CJK Extension E
        0xf900 <= code <= 0xfaff or  # CJK Compatibility Ideographs
        0x2f800 <= code <= 0x2fa1f  # CJK Compatibility Supplement
    )


def contains_chinese(text: str) -> bool:
    """
    Check if text contains any Chinese characters.
    
    Args:
        text: Text to check
        
    Returns:
        True if text contains Chinese characters
    """
    return any(is_chinese_char(char) for char in text)


def validate_pinyin(pinyin_text: str) -> bool:
    """
    Basic validation of pinyin text.
    
    Args:
        pinyin_text: Pinyin text to validate
        
    Returns:
        True if the pinyin appears valid
    """
    if not pinyin_text or not pinyin_text.strip():
        return False
    
    # Check for common pinyin patterns
    # Should contain only letters, spaces, tone marks, and numbers
    import re
    pattern = r'^[a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùüǖǘǚǜ\s\d/]+$'
    return bool(re.match(pattern, pinyin_text.strip()))


if __name__ == "__main__":
    # Test the functions
    test_words = ["爱", "家", "朋友", "水火", "你好"]
    
    print("Testing pinyin conversion:")
    for word in test_words:
        py = hanzi_to_pinyin(word)
        py_hetero = hanzi_to_pinyin(word, heteronym=True)
        variants = get_pinyin_variants(word)
        
        print(f"{word}: {py}")
        if py != py_hetero:
            print(f"  Heteronym: {py_hetero}")
        if len(variants) > 1:
            print(f"  Variants: {variants}")
        print()
