# Refactoring Plan: Reduce Parameter Bloat in HTML Preview Functions with Dataclasses

## 1) Current State Analysis

The HTML preview code currently exposes several functions with long parameter lists. This increases call-site noise, error risk (argument order mistakes), and makes caching wrappers duplicate many parameters.

Current signatures (as of this plan):

- services/cache.py
  - create_page_preview_html(
    cards: List[Dict[str, str]],
    page_num: int,
    card_size: float,
    gap: float,
    margin: float,
    hanzi_font_size_pt: int,
    pinyin_font_size_pt: int,
    english_font_size_pt: int,
    page_size: str = "A4",
    hanzi_font_family: str = DEFAULT_HANZI_FONT,
    background_color: str = DEFAULT_BACKGROUND_COLOR,
    rows: int = 3,
    cols: int = 3,
    auto_fill: bool = True
  ) -> str  → 14 parameters

  - cached_create_page_preview_html(
    cards, page_num, card_size, gap, margin,
    hanzi_font_size_pt, pinyin_font_size_pt, english_font_size_pt,
    page_size, hanzi_font_family, background_color,
    rows, cols, auto_fill
  ) -> str  → 14 parameters (duplication)

  - create_simple_grid_html(
    cards: List[Dict[str, str]],
    hanzi_font_family: str = DEFAULT_HANZI_FONT,
    background_color: str = DEFAULT_BACKGROUND_COLOR,
    rows: int = 3,
    cols: int = 3,
    hanzi_font_size_pt: int = 48,
    pinyin_font_size_pt: int = 18,
    english_font_size_pt: int = 14,
    card_size: float = 5.5,
    auto_fill: bool = True
  ) -> str  → 10 parameters

  - cached_create_simple_grid_html( ...same as above... ) -> str  → 10 parameters (duplication)

Pain points:
- Readability: Call sites (e.g., ui/sections.py) become hard to read and maintain.
- Safety: Easy to mis-order parameters or pass mismatched defaults.
- Duplication: Cached and immediate wrappers replicate long signatures.
- Extensibility: Adding/removing a parameter forces changes across many call sites.


## 2) Proposed Solution (Option B: three focused dataclasses)

Introduce strongly-typed, focused dataclasses that group related options. These are immutable (frozen=True) for safety and cacheability.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class LayoutOptions:
    rows: int
    cols: int
    auto_fill: bool
    card_size_cm: float
    gap_cm: float
    margin_cm: float
    page_size: str  # e.g., "A4", "Letter"

@dataclass(frozen=True)
class Typography:
    font_hanzi_pt: int
    font_pinyin_pt: int
    font_english_pt: int
    hanzi_font_family: str

@dataclass(frozen=True)
class VisualOptions:
    background_color: str
```

New function shapes:
- create_page_preview_html_v2(cards, page_num, layout: LayoutOptions, type: Typography, visual: VisualOptions) -> str
- cached_create_page_preview_html_v2(cards, page_num, layout, type, visual) -> str
- create_simple_grid_html_v2(cards, layout: LayoutOptions, type: Typography, visual: VisualOptions) -> str
- cached_create_simple_grid_html_v2(cards, layout, type, visual) -> str

Back-compat: existing functions keep their signatures but delegate to the new v2 functions by constructing the dataclasses internally.


## 3) Implementation Plan

### Phase 1: Add dataclasses and v2 functions (backward compatible)
1. Create dataclasses (e.g., in services/types.py or services/cache.py initially). Mark frozen=True.
2. Implement v2 functions:
   - create_page_preview_html_v2(cards, page_num, layout, type, visual)
   - cached_create_page_preview_html_v2(...)
   - create_simple_grid_html_v2(cards, layout, type, visual)
   - cached_create_simple_grid_html_v2(...)
3. Adapt internal helpers to accept/use these dataclasses (we already refactored internals; only call sites need change).
4. Update legacy functions to construct dataclasses from their parameters and call v2 equivalents.
5. Add deprecation notes in docstrings and (optional) runtime warnings.

### Phase 2: Update ui/sections.py
1. Where UI collects inputs, construct dataclasses once:
   - layout = LayoutOptions(rows, cols, auto_fill, card_size, gap, margin, page_size)
   - type = Typography(hanzi_font_size_pt, pinyin_font_size_pt, english_font_size_pt, hanzi_font_family)
   - visual = VisualOptions(background_color)
2. Replace calls to old functions with v2 signatures.
3. Ensure cached versions are used where needed.

### Phase 3 (optional): Future enhancements
- Card dataclass for stronger typing
  ```python
  @dataclass(frozen=True)
  class Card:
      hanzi: str
      pinyin: str
      english: str
  ```
- PageRequest dataclass to wrap page_num + options
  ```python
  @dataclass(frozen=True)
  class PageRequest:
      page_num: int
      layout: LayoutOptions
      type: Typography
      visual: VisualOptions
  ```
- Unified render API:
  - create_page_preview(request: PageRequest, cards: list[Card]) -> str


## 4) Migration Strategy (backward compatibility)

- Keep legacy functions (create_page_preview_html, cached_create_page_preview_html, create_simple_grid_html, cached_create_simple_grid_html, and the *_immediate variants).
- Mark them as deprecated in docstrings and add warnings.warn(..., DeprecationWarning, stacklevel=2) to nudge migration, without breaking callers.
- Each legacy function constructs LayoutOptions, Typography, VisualOptions and delegates to the corresponding v2 function.
- This allows an incremental migration of ui/sections.py and any other callers without breaking runtime behavior.
- After migration is complete and stable for a release cycle, consider removing legacy signatures.


## 5) Caching Considerations (Streamlit @st.cache_data)

- Streamlit hashes input arguments to cache results. Using frozen dataclasses is ideal:
  - They are immutable, hashable, and provide stable equality semantics.
- For cards (currently list[dict]):
  - Continue to pass as-is; this matches current behavior.
  - If we later move to a Card dataclass, mark it frozen=True as well for consistent hashing.
- Avoid passing non-hashable/transient objects (e.g., Jinja2 Environment) directly into cached functions.
- If we ever need to cache on a complex object, add a .cache_key() method that returns a tuple of primitives and use that in the cached wrapper.


## 6) Code Examples (before/after)

### Before (in ui/sections.py)
```python
html = create_page_preview_html(
    cards,
    page_num,
    card_size,
    gap,
    margin,
    hanzi_font_size_pt,
    pinyin_font_size_pt,
    english_font_size_pt,
    page_size,
    hanzi_font_family,
    background_color,
    rows,
    cols,
    auto_fill,
)
```

### After (Option B)
```python
layout = LayoutOptions(
    rows=rows,
    cols=cols,
    auto_fill=auto_fill,
    card_size_cm=card_size,
    gap_cm=gap,
    margin_cm=margin,
    page_size=page_size,
)

typo = Typography(
    font_hanzi_pt=hanzi_font_size_pt,
    font_pinyin_pt=pinyin_font_size_pt,
    font_english_pt=english_font_size_pt,
    hanzi_font_family=hanzi_font_family,
)

visual = VisualOptions(background_color=background_color)

html = create_page_preview_html_v2(cards, page_num, layout, typo, visual)
```

### Cached usage (v2)
```python
html = cached_create_page_preview_html_v2(cards, page_num, layout, typo, visual)
```

### Simple grid (v2)
```python
html = create_simple_grid_html_v2(cards, layout, typo, visual)
# or cached_create_simple_grid_html_v2(...)
```

### Legacy function delegating to v2 (implementation sketch)
```python
def create_page_preview_html(cards, page_num, card_size, gap, margin, hanzi_font_size_pt, pinyin_font_size_pt, english_font_size_pt,
                             page_size="A4", hanzi_font_family=DEFAULT_HANZI_FONT, background_color=DEFAULT_BACKGROUND_COLOR,
                             rows=3, cols=3, auto_fill=True) -> str:
    warnings.warn("create_page_preview_html is deprecated; use create_page_preview_html_v2", DeprecationWarning, stacklevel=2)
    layout = LayoutOptions(rows, cols, auto_fill, card_size, gap, margin, page_size)
    typo = Typography(hanzi_font_size_pt, pinyin_font_size_pt, english_font_size_pt, hanzi_font_family)
    visual = VisualOptions(background_color)
    return create_page_preview_html_v2(cards, page_num, layout, typo, visual)
```


## 7) Testing Strategy

- Unit tests
  - New dataclasses: type/field correctness; equality/hash behavior (frozen)
  - v2 functions: basic rendering works with representative inputs
  - Regression: for a matrix of inputs, assert v1 (legacy) HTML == v2 HTML
  - Layout math: verify helpers compute identical metrics when fed via dataclasses vs. legacy args
- Integration tests
  - ui/sections: event-driven tests that simulate user input changes, building dataclasses and invoking v2 functions; assert updated HTML/snippets
  - Caching behavior: repeated calls with identical dataclasses hit cache; different dataclasses produce cache misses
- Snapshot tests
  - Compare rendered HTML (Jinja output) to checked-in snapshots for representative cases
  - Include edge cases (min/max rows/cols, extreme font sizes, auto_fill on/off)
- Smoke tests
  - Import-time checks pass; templates load; no unreachable code
- Rollback safety
  - Legacy function tests remain green until migration completes


## Rollout Checklist
- [ ] Add dataclasses and v2 functions
- [ ] Add deprecation warnings to legacy functions
- [ ] Update ui/sections.py to use v2
- [ ] Add unit/integration/snapshot tests
- [ ] Monitor for any regressions; remove legacy after deprecation window

