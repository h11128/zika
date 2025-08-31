# Preview V2 Migration Guide

## Overview

The preview system has been refactored to use dataclasses for better type safety, maintainability, and consistency. This guide explains how to migrate from legacy preview functions to the new v2 API.

## What Changed

### Legacy Functions (Deprecated)
- `create_page_preview_html()` - 14 individual parameters
- `cached_create_page_preview_html()` - 14 individual parameters  
- `create_simple_grid_html()` - 9 individual parameters
- `cached_create_simple_grid_html()` - 9 individual parameters
- `create_page_preview_html_immediate()` - 14 individual parameters
- `create_simple_grid_html_immediate()` - 9 individual parameters

### New V2 Functions (Recommended)
- `create_page_preview_html_v2()` - 3 dataclass parameters
- `cached_create_page_preview_html_v2()` - 3 dataclass parameters
- `create_simple_grid_html_v2()` - 3 dataclass parameters  
- `cached_create_simple_grid_html_v2()` - 3 dataclass parameters

## Migration Steps

### Step 1: Import New Modules

```python
# Old imports
from services.cache_v2 import create_page_preview_html, cached_create_page_preview_html

# New imports
from services.cache_v2 import create_page_preview_html_v2, cached_create_page_preview_html_v2
from services.preview_types import LayoutOptions, Typography, VisualOptions
```

### Step 2: Convert Parameters to Dataclasses

#### Before (Legacy)
```python
result = create_page_preview_html(
    cards=cards,
    page_num=0,
    card_size=5.5,
    gap=0.5,
    margin=1.0,
    hanzi_font_size_pt=48,
    pinyin_font_size_pt=18,
    english_font_size_pt=14,
    page_size='A4',
    hanzi_font='SimHei',
    background_color='#ffffff',
    rows=3,
    cols=2,
    auto_fill=True
)
```

#### After (V2)
```python
layout = LayoutOptions(
    rows=3,
    cols=2,
    auto_fill=True,
    card_size_cm=5.5,
    gap_cm=0.5,
    margin_cm=1.0,
    page_size='A4'
)

typography = Typography(
    font_hanzi_pt=48,
    font_pinyin_pt=18,
    font_english_pt=14,
    hanzi_font='SimHei'
)

visual = VisualOptions(
    background_color='#ffffff',
    preview_mode='📄 完整页面'
)

result = create_page_preview_html_v2(
    cards=cards,
    page_num=0,
    layout=layout,
    typography=typography,
    visual=visual
)
```

### Step 3: Use Conversion Helpers (Optional)

For gradual migration, you can use conversion helpers:

```python
from services.preview_types import convert_legacy_params_to_preview_params

# Convert legacy parameters to dataclasses
preview_params = convert_legacy_params_to_preview_params(
    card_size=5.5, gap=0.5, margin=1.0, page_size='A4',
    hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14,
    hanzi_font='SimHei', background_color='#ffffff', 
    preview_mode='📄 完整页面',
    rows=3, cols=2, auto_fill=True
)

result = create_page_preview_html_v2(
    cards, 0,
    preview_params.layout,
    preview_params.typography,
    preview_params.visual
)
```

## Benefits of V2 API

### 1. Type Safety
- Frozen dataclasses prevent accidental mutations
- IDE autocomplete and type checking
- Clear parameter grouping by domain

### 2. Maintainability
- Function signatures reduced from 14 parameters to 3
- Changes to parameters only require dataclass updates
- Consistent parameter validation

### 3. Cache Performance
- Deterministic hashing for optimal cache behavior
- JSON serialization for cache keys
- Better cache hit rates

### 4. Consistency
- Same dataclasses used across preview and export
- Unified parameter validation
- Consistent units (cm for sizes, pt for fonts)

## Backward Compatibility

### Automatic Delegation
Legacy functions automatically delegate to v2 implementation when available:

```python
# This still works but shows deprecation warning
result = create_page_preview_html(cards, 0, 5.5, 0.5, 1.0, ...)
# Internally converts to dataclasses and calls v2 function
```

### Feature Flag Control
The delegation is controlled by the `preview_dataclasses_v2` feature flag:

```python
# In core/feature_flags.py or environment
FEATURE_PREVIEW_DATACLASSES_V2 = True  # Enable v2 delegation
```

### Deprecation Warnings
Legacy functions show deprecation warnings:

```
DeprecationWarning: create_page_preview_html() is deprecated. 
Use create_page_preview_html_v2() with dataclasses instead.
```

## Migration Timeline

### Phase 1: Gradual Migration (Current)
- Legacy functions work with deprecation warnings
- New code should use v2 API
- Existing code can be migrated incrementally

### Phase 2: Full Migration (Future)
- All callers migrated to v2 API
- Legacy functions marked for removal
- Performance optimizations for v2 only

### Phase 3: Cleanup (Future)
- Legacy functions removed
- Simplified codebase
- Full v2 benefits realized

## Common Migration Patterns

### Pattern 1: Direct Replacement
Replace function calls with v2 equivalents using dataclasses.

### Pattern 2: Config-Based Migration
If you have configuration objects, create conversion functions:

```python
def config_to_preview_params(config) -> PreviewParams:
    return PreviewParams(
        layout=LayoutOptions.from_layout_config(config.layout),
        typography=Typography.from_configs(config.layout, config.ui),
        visual=VisualOptions.from_ui_config(config.ui)
    )
```

### Pattern 3: Wrapper Functions
Create wrapper functions for common parameter combinations:

```python
def create_standard_preview(cards, page_num):
    layout = LayoutOptions(rows=3, cols=2, auto_fill=True, ...)
    typography = Typography(font_hanzi_pt=48, ...)
    visual = VisualOptions(background_color='#ffffff', ...)
    
    return create_page_preview_html_v2(cards, page_num, layout, typography, visual)
```

## Testing Migration

### Unit Tests
```python
def test_v2_migration():
    # Test that v2 produces same results as legacy
    legacy_result = create_page_preview_html(cards, 0, 5.5, ...)
    
    preview_params = convert_legacy_params_to_preview_params(5.5, ...)
    v2_result = create_page_preview_html_v2(cards, 0, ...)
    
    assert legacy_result == v2_result
```

### Integration Tests
- Test that UI components work with both APIs
- Verify cache behavior is consistent
- Check performance improvements

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `services.cache_v2` and `services.preview_types` are available
2. **Parameter Validation**: Check dataclass field names and types
3. **Cache Misses**: Verify dataclass equality and hashing
4. **Performance**: Monitor cache hit rates and render times

### Debug Tips

1. Enable debug logging to see delegation behavior
2. Use feature flags to test both implementations
3. Compare cache keys between legacy and v2
4. Validate dataclass serialization

## Support

For questions or issues with migration:
1. Check the deprecation warnings for specific guidance
2. Review the dataclass definitions in `services/preview_types.py`
3. Test with feature flags to isolate issues
4. Use conversion helpers for complex migrations
