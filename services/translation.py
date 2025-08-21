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

