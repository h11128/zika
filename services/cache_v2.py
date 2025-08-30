"""
Cache V2 service for the UI refactor.
Provides schema-versioned, digest-based caching with proper invalidation.
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Callable, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import streamlit as st

from core.feature_flags import use_cache_v2
from core.version import get_code_version
# Import from the main ui.state module (not the package)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("ui_state_module", os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "state.py"))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)

# Import preview dataclasses for v2 functions
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from services.preview_types import LayoutOptions, Typography, VisualOptions
from services.render_core import render_cards_unified, create_render_options_from_legacy

# Schema versions for cache invalidation
PREVIEW_CACHE_SCHEMA_VERSION = "v1.0.0"
EXPORT_CACHE_SCHEMA_VERSION = "v1.0.0"

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0

    def touch(self) -> None:
        """Update access time and count."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1


@dataclass
class CacheConfig:
    """Configuration for a cache instance."""
    max_entries: int = 50
    max_size_bytes: int = 50 * 1024 * 1024  # 50MB
    ttl_seconds: int = 3600  # 1 hour
    name: str = "cache"


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0


class CacheV2:
    """Schema-versioned cache with TTL, size limits, and observability."""

    def __init__(self, config: CacheConfig):
        self.config = config
        self.entries: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not use_cache_v2():
            return None

        if key not in self.entries:
            self.stats.misses += 1
            return None

        entry = self.entries[key]

        # Check TTL
        if self._is_expired(entry):
            self._remove_entry(key)
            self.stats.misses += 1
            return None

        # Update access info
        entry.touch()
        self.stats.hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        if not use_cache_v2():
            return

        # Estimate size
        size_bytes = self._estimate_size(value)

        # Check if we need to evict
        self._ensure_capacity(size_bytes)

        # Create entry
        entry = CacheEntry(
            value=value,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            size_bytes=size_bytes
        )

        # Remove old entry if exists
        if key in self.entries:
            self._remove_entry(key)

        # Add new entry
        self.entries[key] = entry
        self.stats.total_size_bytes += size_bytes
        self.stats.entry_count += 1

    def invalidate(self, key: str) -> bool:
        """Remove specific key from cache."""
        if key in self.entries:
            self._remove_entry(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self.entries.clear()
        self.stats = CacheStats()

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if entry is expired."""
        age = datetime.utcnow() - entry.created_at
        return age.total_seconds() > self.config.ttl_seconds

    def _remove_entry(self, key: str) -> None:
        """Remove entry and update stats."""
        if key in self.entries:
            entry = self.entries[key]
            self.stats.total_size_bytes -= entry.size_bytes
            self.stats.entry_count -= 1
            del self.entries[key]

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (int, float)):
                return 8
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate

    def _ensure_capacity(self, new_size: int) -> None:
        """Ensure cache has capacity for new entry."""
        # Check size limit
        while (self.stats.total_size_bytes + new_size > self.config.max_size_bytes and
               self.entries):
            self._evict_lru()

        # Check entry count limit
        while len(self.entries) >= self.config.max_entries and self.entries:
            self._evict_lru()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self.entries:
            return

        # Find LRU entry
        lru_key = min(self.entries.keys(),
                     key=lambda k: self.entries[k].last_accessed)

        self._remove_entry(lru_key)
        self.stats.evictions += 1


# Global cache instances
_preview_cache: Optional[CacheV2] = None
_export_cache: Optional[CacheV2] = None


def get_preview_cache() -> CacheV2:
    """Get or create preview cache instance."""
    global _preview_cache
    if _preview_cache is None:
        config = CacheConfig(
            max_entries=20,
            max_size_bytes=50 * 1024 * 1024,  # 50MB
            ttl_seconds=3600,
            name="preview"
        )
        _preview_cache = CacheV2(config)
    return _preview_cache


def get_export_cache() -> CacheV2:
    """Get or create export cache instance."""
    global _export_cache
    if _export_cache is None:
        config = CacheConfig(
            max_entries=50,
            max_size_bytes=100 * 1024 * 1024,  # 100MB
            ttl_seconds=7200,  # 2 hours
            name="export"
        )
        _export_cache = CacheV2(config)
    return _export_cache


def compute_cache_key(base_data: Dict[str, Any], schema_version: str) -> str:
    """Compute cache key with schema versioning."""
    cache_data = {
        'data': base_data,
        'schema_version': schema_version,
        'code_version': get_code_version(),
        'session_generation': ui_state_module.get_session_generation(),
    }
    return ui_state_module.stable_digest(cache_data)


def cached_preview_render(render_func: Callable[..., T], *args, **kwargs) -> T:
    """Cache decorator for preview rendering functions."""
    if not use_cache_v2():
        return render_func(*args, **kwargs)

    # Build cache key from arguments, converting dataclasses to dicts
    serializable_args = []
    for arg in args:
        if hasattr(arg, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_args.append(arg.to_dict())
        else:
            serializable_args.append(arg)

    serializable_kwargs = {}
    for key, value in kwargs.items():
        if hasattr(value, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_kwargs[key] = value.to_dict()
        else:
            serializable_kwargs[key] = value

    cache_data = {
        'function': render_func.__name__,
        'args': serializable_args,
        'kwargs': serializable_kwargs,
    }
    cache_key = compute_cache_key(cache_data, PREVIEW_CACHE_SCHEMA_VERSION)

    # Try cache first
    cache = get_preview_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Compute and cache result
    result = render_func(*args, **kwargs)
    cache.set(cache_key, result)
    return result


def cached_export_render(render_func: Callable[..., T], *args, **kwargs) -> T:
    """Cache decorator for export rendering functions."""
    if not use_cache_v2():
        return render_func(*args, **kwargs)

    # Build cache key from arguments, converting dataclasses to dicts
    serializable_args = []
    for arg in args:
        if hasattr(arg, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_args.append(arg.to_dict())
        else:
            serializable_args.append(arg)

    serializable_kwargs = {}
    for key, value in kwargs.items():
        if hasattr(value, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_kwargs[key] = value.to_dict()
        else:
            serializable_kwargs[key] = value

    cache_data = {
        'function': render_func.__name__,
        'args': serializable_args,
        'kwargs': serializable_kwargs,
    }
    cache_key = compute_cache_key(cache_data, EXPORT_CACHE_SCHEMA_VERSION)

    # Try cache first
    cache = get_export_cache()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # Compute and cache result
    result = render_func(*args, **kwargs)
    cache.set(cache_key, result)
    return result


def clear_preview_cache_v2() -> None:
    """Clear preview cache."""
    if use_cache_v2():
        get_preview_cache().clear()


def clear_export_cache_v2() -> None:
    """Clear export cache."""
    if use_cache_v2():
        get_export_cache().clear()


def clear_all_caches_v2() -> None:
    """Clear all v2 caches."""
    clear_preview_cache_v2()
    clear_export_cache_v2()


def get_cache_stats() -> Dict[str, CacheStats]:
    """Get statistics for all caches."""
    if not use_cache_v2():
        return {}

    return {
        'preview': get_preview_cache().get_stats(),
        'export': get_export_cache().get_stats(),
    }


def log_cache_stats() -> None:
    """Log cache statistics for debugging."""
    if not use_cache_v2():
        return

    stats = get_cache_stats()
    for cache_name, cache_stats in stats.items():
        print(f"Cache {cache_name}: "
              f"hit_rate={cache_stats.hit_rate:.1f}%, "
              f"entries={cache_stats.entry_count}, "
              f"size={cache_stats.total_size_bytes // 1024}KB, "
              f"evictions={cache_stats.evictions}")


# Streamlit cache integration
@st.cache_data(show_spinner=False)
def _st_cached_render(cache_key: str, render_func_name: str, *args, **kwargs) -> Any:
    """Streamlit cache integration for v2 cache."""
    # This is a fallback when cache_v2 is disabled
    # Import the function dynamically to avoid circular imports
    if render_func_name == 'create_preview_html':
        # Use shared render core if available
        try:
            result = render_cards_unified(*args, **kwargs)
            if result.success:
                return result.content
            else:
                # Fall back to legacy implementation
                from services.cache import create_preview_html
                return create_preview_html(*args, **kwargs)
        except Exception:
            # Fall back to legacy implementation
            from services.cache import create_preview_html
            return create_preview_html(*args, **kwargs)
    else:
        raise ValueError(f"Unknown render function: {render_func_name}")


# V2 Preview Functions Using Dataclasses
def create_page_preview_html_v2(cards: List[Dict[str, str]], page_num: int,
                                layout: 'LayoutOptions', typography: 'Typography',
                                visual: 'VisualOptions') -> str:
    """
    Create page preview HTML using dataclasses (v2 API).

    Args:
        cards: List of card data
        page_num: Page number to render
        layout: Layout configuration
        typography: Typography configuration
        visual: Visual styling configuration

    Returns:
        HTML string for the page preview
    """
    from services.cache import create_page_preview_html

    # Convert dataclasses to legacy parameters
    return create_page_preview_html(
        cards=cards,
        page_num=page_num,
        card_size=layout.card_size_cm,
        gap=layout.gap_cm,
        margin=layout.margin_cm,
        font_hanzi=typography.font_hanzi_pt,
        font_pinyin=typography.font_pinyin_pt,
        font_english=typography.font_english_pt,
        page_size=layout.page_size,
        hanzi_font=typography.hanzi_font,
        background_color=visual.background_color,
        rows=layout.rows,
        cols=layout.cols,
        auto_fill=layout.auto_fill
    )


def cached_create_page_preview_html_v2(cards: List[Dict[str, str]], page_num: int,
                                       layout: 'LayoutOptions', typography: 'Typography',
                                       visual: 'VisualOptions') -> str:
    """
    Cached version of create_page_preview_html_v2.

    Uses cache_v2 system with dataclass-based cache keys.
    """
    return cached_preview_render(
        create_page_preview_html_v2,
        cards, page_num, layout, typography, visual
    )


def create_simple_grid_html_v2(cards: List[Dict[str, str]],
                              layout: 'LayoutOptions', typography: 'Typography',
                              visual: 'VisualOptions') -> str:
    """
    Create simple grid HTML using dataclasses (v2 API).

    Args:
        cards: List of card data
        layout: Layout configuration
        typography: Typography configuration
        visual: Visual styling configuration

    Returns:
        HTML string for the simple grid
    """
    from services.cache import create_simple_grid_html

    # Convert dataclasses to legacy parameters
    return create_simple_grid_html(
        cards=cards,
        hanzi_font=typography.hanzi_font,
        background_color=visual.background_color,
        rows=layout.rows,
        cols=layout.cols,
        font_hanzi=typography.font_hanzi_pt,
        font_pinyin=typography.font_pinyin_pt,
        font_english=typography.font_english_pt,
        card_size=layout.card_size_cm,
        auto_fill=layout.auto_fill
    )


def cached_create_simple_grid_html_v2(cards: List[Dict[str, str]],
                                     layout: 'LayoutOptions', typography: 'Typography',
                                     visual: 'VisualOptions') -> str:
    """
    Cached version of create_simple_grid_html_v2.

    Uses cache_v2 system with dataclass-based cache keys.
    """
    return cached_preview_render(
        create_simple_grid_html_v2,
        cards, layout, typography, visual
    )