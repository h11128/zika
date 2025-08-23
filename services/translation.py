"""
Translation utilities for the app.

- Prefer local dictionary first for quality and zero-cost.
- Fallback to Google Cloud Translation API v2 when a key is configured.
- Ensure final English output contains no Chinese characters.

Environment:
  GOOGLE_TRANSLATE_API_KEY: API key for Google Translate v2. If not set, Google
  fallback is skipped gracefully.
"""
from __future__ import annotations

import json
import os
import re
import html
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from src.pinyin_utils import is_chinese_char


# Precompiled regexes for simple structural cleaning
_PARENS_OR_BRACKETS = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_WHITESPACE_RE = re.compile(r"\s+")


def _has_chinese(s: str) -> bool:
    return any(is_chinese_char(ch) for ch in s)


def _remove_chinese(s: str) -> str:
    return "".join(ch for ch in s if not is_chinese_char(ch))


def clean_english_text(text: Optional[str]) -> Optional[str]:
    """Clean a translation string to ensure it's English-only.

    - Drops bracketed/parenthetical content if it contains Chinese
    - Removes any remaining Chinese characters
    - Cleans dictionary-specific patterns (CL:, MW:, etc.)
    - Unescapes HTML entities and trims redundant whitespace
    - Returns None if no ASCII letters remain
    """
    if not text:
        return None

    # Unescape HTML entities first (Google often returns escaped text)
    text = html.unescape(str(text))

    # Remove bracketed content that contains Chinese
    def _keep_or_drop(m: re.Match) -> str:
        seg = m.group(0)
        return "" if _has_chinese(seg) else seg

    text = _PARENS_OR_BRACKETS.sub(_keep_or_drop, text)

    # Remove any remaining Chinese characters
    text = _remove_chinese(text)

    # Clean dictionary-specific patterns
    # Remove patterns like "CL:|", "MW:|", "TW:|" etc. (classifier/measure word markers)
    text = re.sub(r';\s*[A-Z]{1,3}:\|[^;]*', '', text)
    text = re.sub(r';\s*[A-Z]{1,3}:\s*$', '', text)

    # Clean up multiple semicolons and trailing punctuation
    text = re.sub(r';+', ';', text)
    text = re.sub(r';\s*$', '', text)

    # Remove empty definitions so we don't leave orphan semicolons like "; ;"
    parts = [p.strip() for p in text.split(';') if p.strip()]
    text = '; '.join(parts)

    # Normalize whitespace
    text = _WHITESPACE_RE.sub(" ", text).strip()

    # If no ASCII letters remain, treat as empty
    if not text or not re.search(r"[A-Za-z]", text):
        return None

    return text


def translate_with_google(text: str, api_key: Optional[str] = None, timeout: int = 6) -> Optional[str]:
    """Translate given text to English using Google Translate v2 REST API.

    Args:
        text: Source text (likely Chinese)
        api_key: Optional API key; if None, read from GOOGLE_TRANSLATE_API_KEY
        timeout: Request timeout in seconds

    Returns:
        Cleaned English translation or None on any error
    """
    if not text or not text.strip():
        return None

    api_key = api_key or os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        return None

    try:
        url = f"https://translation.googleapis.com/language/translate/v2?key={api_key}"
        payload = {
            "q": text,
            "target": "en",
            # Let Google auto-detect source; specifying zh may hurt if input isn't zh
            "format": "text",
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        parsed = json.loads(raw.decode("utf-8"))
        translations = parsed.get("data", {}).get("translations", [])
        if not translations:
            return None
        translated = translations[0].get("translatedText")
        return clean_english_text(translated)
    except (HTTPError, URLError, json.JSONDecodeError, KeyError):
        return None
    except Exception:
        # Be conservative: never let translation errors bubble up into the app
        return None


def _are_different_translations(t1: Optional[str], t2: Optional[str]) -> bool:
    """Check if two translations are meaningfully different."""
    if not t1 or not t2:
        return False
    # Normalize for comparison
    norm1 = t1.lower().strip()
    norm2 = t2.lower().strip()
    # Same text
    if norm1 == norm2:
        return False
    # One contains the other (avoid subset duplicates)
    if norm1 in norm2 or norm2 in norm1:
        return False
    return True


def combine_translations_smart(*translations: Optional[str]) -> Optional[str]:
    """
    Intelligently combine multiple translations, removing duplicates and checking for meaningful differences.

    Args:
        *translations: Variable number of translation strings from different sources

    Returns:
        Combined translation string with unique definitions separated by ' | '
    """
    # Filter out None and empty translations
    valid_translations = [t for t in translations if t and t.strip()]

    if not valid_translations:
        return None

    if len(valid_translations) == 1:
        return valid_translations[0]

    # Split and normalize definitions from all sources
    def normalize_defs(text):
        return [d.strip() for d in text.split(';') if d.strip()]

    # Track seen definitions (case-insensitive) and their sources
    seen_lower = set()
    result_groups = []

    for translation in valid_translations:
        defs = normalize_defs(translation)
        unique_defs = []

        for d in defs:
            d_lower = d.lower()
            # Skip if exact match or containment relationship with any seen definition
            is_duplicate = False
            for existing in seen_lower:
                if d_lower == existing or d_lower in existing or existing in d_lower:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_defs.append(d)
                seen_lower.add(d_lower)

        # Only add this group if it has unique definitions
        if unique_defs:
            result_groups.append('; '.join(unique_defs))

    # Combine all unique groups
    if len(result_groups) > 1:
        return ' | '.join(result_groups)
    elif result_groups:
        return result_groups[0]
    else:
        return None


# Backward compatibility function for two-argument calls
def combine_two_translations(t1: Optional[str], t2: Optional[str]) -> Optional[str]:
    """Backward compatibility wrapper for two-translation combining."""
    return combine_translations_smart(t1, t2)


def translate_with_strategy(text: str, dictionary=None, strategy: str = 'local_first') -> Optional[str]:
    """Translate text using the specified strategy.

    Args:
        text: Text to translate
        dictionary: Local dictionary object with lookup_translation method
        strategy: Translation strategy - 'local_first', 'google_first', 'local_only', 'google_only', 'mixed', 'dict_mixed'

    Returns:
        Translated text or None
    """
    def try_local() -> Optional[str]:
        if dictionary is None:
            return None
        try:
            t = dictionary.lookup_translation(text)
            return clean_english_text(t) if t else None
        except Exception:
            return None

    def try_local_mixed() -> Optional[str]:
        if dictionary is None:
            return None
        try:
            # Use mixed dictionary strategy if available
            if hasattr(dictionary, 'lookup_translation_mixed'):
                t = dictionary.lookup_translation_mixed(text)
            else:
                t = dictionary.lookup_translation(text)
            return clean_english_text(t) if t else None
        except Exception:
            return None

    def try_google() -> Optional[str]:
        return translate_with_google(text)

    if strategy == 'google_first':
        return try_google() or try_local()
    elif strategy == 'local_only':
        return try_local()
    elif strategy == 'google_only':
        return try_google()
    elif strategy == 'dict_mixed':
        # Use mixed dictionary strategy (Mini + CEDICT)
        return try_local_mixed()
    elif strategy == 'mixed':
        local_trans = try_local()
        google_trans = try_google()
        return combine_translations_smart(local_trans, google_trans)
    else:  # local_first (default)
        return try_local() or try_google()

