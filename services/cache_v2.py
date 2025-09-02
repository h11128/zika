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

# Cache v2 is now always enabled - no feature flag needed
from core.version import get_code_version
# Import from the main ui.state module (not the package)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("ui_state_module", os.path.join(os.path.dirname(os.path.dirname(__file__)), "ui", "state.py"))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)

# Backward-compatibility feature flag hook expected by tests
# Cache v2 is the only implementation now; keep a toggle for tests to patch
# so they can simulate "disabled" mode behavior.
def use_cache_v2() -> bool:
    return True

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
        # Respect feature flag: disabled => no caching
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
        # Respect feature flag: disabled => no-op
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
        if not use_cache_v2():
            return False
        if key in self.entries:
            self._remove_entry(key)
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        if not use_cache_v2():
            return
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
    # Cache v2 is always enabled
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
        'function_name': render_func.__name__,
        'function_module': getattr(render_func, '__module__', None),
        'function_qualname': getattr(render_func, '__qualname__', render_func.__name__),
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
    """Cache decorator for export rendering functions with content version awareness."""
    # Cache v2 is always enabled
    # Build cache key from arguments, converting dataclasses to dicts
    serializable_args = []
    cards_data = None  # Track cards for content version signal

    for arg in args:
        if hasattr(arg, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_args.append(arg.to_dict())
        else:
            serializable_args.append(arg)
            # Check if this argument looks like cards data
            if isinstance(arg, list) and arg and isinstance(arg[0], dict):
                if any(key in arg[0] for key in ['hanzi', 'pinyin', 'english']):
                    cards_data = arg

    serializable_kwargs = {}
    for key, value in kwargs.items():
        if hasattr(value, 'to_dict'):
            # Convert dataclass to dict for serialization
            serializable_kwargs[key] = value.to_dict()
        else:
            serializable_kwargs[key] = value
            # Check if this kwarg looks like cards data
            if key == 'cards' and isinstance(value, list):
                cards_data = value

    # Use enhanced export key computation with content version signal
    try:
        from ui.state import compute_export_key, get_content_version_signal

        # Extract export parameters from args/kwargs
        export_params = {
            'function_name': render_func.__name__,
            'function_module': getattr(render_func, '__module__', None),
            'function_qualname': getattr(render_func, '__qualname__', render_func.__name__),
            'args': serializable_args,
            'kwargs': serializable_kwargs,
        }

        # Get content version signal if we have cards
        content_version_signal = None
        cards_count = 0
        if cards_data:
            content_version_signal = get_content_version_signal(cards_data)
            cards_count = len(cards_data)

        # Compute enhanced cache key
        cache_key = compute_export_key(
            export_params=export_params,
            cards_count=cards_count,
            content_version_signal=content_version_signal,
            export_schema_version=EXPORT_CACHE_SCHEMA_VERSION
        )

    except ImportError:
        # Fallback to old method if ui.state is not available
        cache_data = {
            'function_name': render_func.__name__,
            'function_module': getattr(render_func, '__module__', None),
            'function_qualname': getattr(render_func, '__qualname__', render_func.__name__),
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
    """Clear preview cache and invalidate any function-level caches (legacy)."""
    # Cache v2 is always enabled
    get_preview_cache().clear()

    # Also attempt to clear function-level caches for backward-compatibility tests
    try:
        # These attributes are sometimes patched in tests to assert .clear() is called
        _self = globals()
        fn = _self.get('cached_create_page_preview_html')
        if fn is not None and hasattr(fn, 'clear'):
            try:
                fn.clear()
            except Exception:
                pass
        fn2 = _self.get('cached_create_simple_grid_html')
        if fn2 is not None and hasattr(fn2, 'clear'):
            try:
                fn2.clear()
            except Exception:
                pass
    except Exception:
        pass


def clear_export_cache_v2() -> None:
    """Clear export cache."""
    # Cache v2 is always enabled
    get_export_cache().clear()


def clear_all_caches_v2() -> None:
    """Clear all v2 caches."""
    clear_preview_cache_v2()
    clear_export_cache_v2()


# Legacy-compatible wrappers (names expected by tests)

def clear_preview_cache() -> None:
    """Legacy alias to clear preview cache (v2)."""
    return clear_preview_cache_v2()


def cached_create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                                    card_size_cm: float, gap_cm: float, margin_cm: float,
                                    hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                                    page_size: str = "A4", hanzi_font_family: str = "SimHei",
                                    background_color: str = "#ffffff",
                                    layout_rows: int = 3, layout_cols: int = 3, layout_auto_fill: bool = True) -> str:
    """Legacy signature: cached version delegating to v2 dataclass API."""
    preview_params = convert_legacy_params_to_preview_params(
        card_size_cm, gap_cm, margin_cm, page_size,
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '📄 完整页面',
        layout_rows, layout_cols, layout_auto_fill
    )
    return cached_create_page_preview_html_v2(cards, page_num, preview_params.layout, preview_params.typography, preview_params.visual)


def cached_create_simple_grid_html(cards: List[Dict[str, str]],
                                   hanzi_font_family: str, background_color: str,
                                   layout_rows: int, layout_cols: int,
                                   hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                                   card_size: float, auto_fill: bool) -> str:
    """Legacy signature: cached simple grid delegating to v2 dataclass API."""
    preview_params = convert_legacy_params_to_preview_params(
        card_size, 0.5, 1.0, 'A4',
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '🔲 简单网格',
        layout_rows, layout_cols, auto_fill
    )
    return cached_create_simple_grid_html_v2(cards, preview_params.layout, preview_params.typography, preview_params.visual)


def get_cache_stats() -> Dict[str, CacheStats]:
    """Get statistics for all caches."""
    # Respect feature flag: disabled => empty stats
    if not use_cache_v2():
        return {}
    return {
        'preview': get_preview_cache().get_stats(),
        'export': get_export_cache().get_stats(),
    }


def log_cache_stats() -> None:
    """Log cache statistics for debugging."""
    # Cache v2 is always enabled
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
                from services.cache_v2 import create_preview_html
                return create_preview_html(*args, **kwargs)
        except Exception:
            # Fall back to legacy implementation
            from services.cache_v2 import create_preview_html
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
    # Direct implementation to avoid recursion with legacy delegation
    from services.cache import (
        _slice_cards_for_page, _compute_page_layout_metrics,
        _compute_page_card_box, _compute_font_px, PageTemplateContext
    )

    # Safety guards
    layout_rows = max(1, int(layout.layout_rows or 3))
    layout_cols = max(1, int(layout.layout_cols or 3))

    # Compute inputs via helpers
    cards_per_page, page_cards = _slice_cards_for_page(cards, page_num, layout_rows, layout_cols)
    if not page_cards and page_num > 0:
        return "<div style='text-align: center; color: #666; padding: 50px;'>页面不存在</div>"

    M = _compute_page_layout_metrics(
        layout.page_size, layout.gap_cm, layout.margin_cm,
        layout_rows, layout_cols, layout.card_size_cm, layout.layout_auto_fill
    )
    card_box = _compute_page_card_box(M)
    font_px = _compute_font_px(
        typography.hanzi_font_size_pt, typography.pinyin_font_size_pt,
        typography.english_font_size_pt, M.scale_factor
    )

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('page_preview.html.j2')

    ctx = PageTemplateContext(
        page_num=page_num, layout_rows=layout_rows, layout_cols=layout_cols,
        hanzi_font_family=typography.hanzi_font_family, background_color=visual.background_color
    )

    page_cards_ctx = [(page_cards[i] if i < len(page_cards) else None) for i in range(cards_per_page)]
    return template.render(M=M, font=font_px, card_box=card_box, ctx=ctx, page_cards=page_cards_ctx)


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
    # Direct implementation to avoid recursion with legacy delegation
    from services.cache import (
        _compute_simple_grid_css, _compute_simple_grid_font_px,
        _compute_simple_card_box, SimpleGridTemplateContext
    )

    layout_rows = max(1, int(layout.layout_rows or 3))
    layout_cols = max(1, int(layout.layout_cols or 3))

    if not cards:
        return "<div style='text-align: center; color: #666; padding: 50px;'>输入汉字以查看预览</div>"

    params = _compute_simple_grid_css(layout_cols, layout.card_size_cm, layout.layout_auto_fill)
    font_px = _compute_simple_grid_font_px(
        typography.hanzi_font_size_pt, typography.pinyin_font_size_pt, typography.english_font_size_pt
    )
    card_box = _compute_simple_card_box(params.card_size_px_calc)

    # Build grid cards with padding for empty slots
    cards_per_page = layout.layout_rows * layout.layout_cols
    grid_cards: List[Dict[str, str]] = []
    for i in range(cards_per_page):
        grid_cards.append(cards[i] if i < len(cards) else None)

    from jinja2 import Environment, FileSystemLoader, select_autoescape
    env = Environment(
        loader=FileSystemLoader('templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('simple_grid.html.j2')

    ctx = SimpleGridTemplateContext(
        layout_rows=layout_rows, layout_cols=layout_cols,
        hanzi_font_family=typography.hanzi_font_family, background_color=visual.background_color
    )

    return template.render(params=params, ctx=ctx, font=font_px, card_box=card_box, grid_cards=grid_cards)


def cached_create_simple_grid_html_v2(cards: List[Dict[str, str]],
                                     layout: 'LayoutOptions', typography: 'Typography', visual: 'VisualOptions') -> str:
    """
    Cached version of create_simple_grid_html_v2.

    Uses cache_v2 system with dataclass-based cache keys.
    """
    return cached_preview_render(
        create_simple_grid_html_v2,
        cards, layout, typography, visual
    )

# Immediate (non-cached) v2 preview API for tests that expect direct rendering
# Provided for compatibility with UI E2E tests

def create_page_preview_html_immediate(cards: List[Dict[str, str]], page_num: int,
                                       card_size_cm: float, gap_cm: float, margin_cm: float,
                                       hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                                       page_size: str = "A4", hanzi_font_family: str = "SimHei",
                                       background_color: str = "#ffffff",
                                       layout_rows: int = 3, layout_cols: int = 3, layout_auto_fill: bool = True) -> str:
    # Call the legacy-named function so tests can patch it
    return create_page_preview_html(
        cards, page_num,
        card_size_cm, gap_cm, margin_cm,
        hanzi_font_size, pinyin_font_size, english_font_size,
        page_size, hanzi_font_family, background_color,
        layout_rows, layout_cols, layout_auto_fill
    )


# Backward-compatibility shim for legacy imports used in tests
# Some integration tests import create_preview_html from cache_v2
# Provide a thin wrapper that maps to the v2 API using dataclasses via preview_types helpers
from services.preview_types import convert_legacy_params_to_preview_params

# Immediate (non-cached) simple grid rendering for tests


# Legacy alias for tests expecting create_simple_grid_html with minimal args
# Delegates to v2 via legacy parameter conversion

def create_simple_grid_html(cards: List[Dict[str, str]],
                            hanzi_font_family: str = "SimHei",
                            background_color: str = "#ffffff",
                            layout_rows: int = 3, layout_cols: int = 3,
                            hanzi_font_size: int = 48, pinyin_font_size: int = 18, english_font_size: int = 14,
                            card_size_cm: float = 5.5, auto_fill: bool = True) -> str:
    preview_params = convert_legacy_params_to_preview_params(
        card_size_cm, 0.5, 1.0, 'A4',
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '🔲 简单网格',
        layout_rows, layout_cols, auto_fill
    )
    return create_simple_grid_html_v2(cards, preview_params.layout, preview_params.typography, preview_params.visual)

def create_simple_grid_html_immediate(cards: List[Dict[str, str]],
                                      hanzi_font_family: str, background_color: str,
                                      layout_rows: int, layout_cols: int,
                                      hanzi_font_size: int = 48, pinyin_font_size: int = 18, english_font_size: int = 14,
                                      card_size: float = 5.5, auto_fill: bool = True) -> str:
    """Immediate simple grid renderer (legacy-friendly).

    Accepts a minimal signature used by tests and fills sensible defaults
    for omitted typography and sizing parameters.
    """
    preview_params = convert_legacy_params_to_preview_params(
        card_size, 0.5, 1.0, 'A4',
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '🔲 简单网格',
        layout_rows, layout_cols, auto_fill
    )
    return create_simple_grid_html_v2(cards, preview_params.layout, preview_params.typography, preview_params.visual)


def create_preview_html(cards: List[Dict[str, str]], page_num: int,
                        page_size: str, gap_cm: float, margin_cm: float,
                        layout_rows: int, layout_cols: int, card_size_cm: float,
                        hanzi_font_size_pt: int, pinyin_font_size_pt: int, english_font_size_pt: int,
                        hanzi_font_family: str, background_color: str,
                        layout_auto_fill: bool = False) -> str:
    """Legacy signature wrapper to maintain compatibility for tests.
    Converts legacy parameters to v2 dataclasses and delegates to v2 renderer.
    """
    preview_params = convert_legacy_params_to_preview_params(
        card_size_cm, gap_cm, margin_cm, page_size,
        hanzi_font_size_pt, pinyin_font_size_pt, english_font_size_pt,
        hanzi_font_family, background_color, '📄 完整页面',
        layout_rows, layout_cols, layout_auto_fill
    )
    return create_page_preview_html_v2(cards, page_num, preview_params.layout, preview_params.typography, preview_params.visual)


# Legacy-named function expected by some tests for patching
# Accepts legacy parameters order grouped by type for convenience

def create_page_preview_html(cards: List[Dict[str, str]], page_num: int,
                             card_size_cm: float, gap_cm: float, margin_cm: float,
                             hanzi_font_size: int, pinyin_font_size: int, english_font_size: int,
                             page_size: str = "A4", hanzi_font_family: str = "SimHei",
                             background_color: str = "#ffffff",
                             layout_rows: int = 3, layout_cols: int = 3, layout_auto_fill: bool = True) -> str:
    preview_params = convert_legacy_params_to_preview_params(
        card_size_cm, gap_cm, margin_cm, page_size,
        hanzi_font_size, pinyin_font_size, english_font_size,
        hanzi_font_family, background_color, '📄 完整页面',
        layout_rows, layout_cols, layout_auto_fill
    )
    return create_page_preview_html_v2(cards, page_num, preview_params.layout, preview_params.typography, preview_params.visual)
