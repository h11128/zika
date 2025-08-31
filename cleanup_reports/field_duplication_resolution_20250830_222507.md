# Field Duplication Resolution Report

**Date**: 2025-08-30 22:25:07

## Summary

- **Files Modified**: 1
- **Mappings Applied**: 12
- **Conflicts Resolved**: 43
- **Errors**: 0

## Modified Files

- scripts\resolve_field_duplication.py

## Mappings Applied

- **scripts\resolve_field_duplication.py**: `font_hanzi` → `hanzi_font_size_pt`
- **scripts\resolve_field_duplication.py**: `font_pinyin` → `pinyin_font_size_pt`
- **scripts\resolve_field_duplication.py**: `font_english` → `english_font_size_pt`
- **scripts\resolve_field_duplication.py**: `hanzi_font` → `hanzi_font_family`
- **scripts\resolve_field_duplication.py**: `pinyin_font` → `pinyin_font_family`
- **scripts\resolve_field_duplication.py**: `english_font` → `english_font_family`
- **scripts\resolve_field_duplication.py**: `gap` → `gap_cm`
- **scripts\resolve_field_duplication.py**: `margin` → `margin_cm`
- **scripts\resolve_field_duplication.py**: `card_size` → `card_size_cm`
- **scripts\resolve_field_duplication.py**: `rows` → `layout_rows`
- **scripts\resolve_field_duplication.py**: `cols` → `layout_cols`
- **scripts\resolve_field_duplication.py**: `auto_fill` → `layout_auto_fill`

## Conflicts Resolved

- scripts\resolve_field_duplication.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- services\cache_v2.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- services\preview_types.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- services\render_core.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- services\typography.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- src\layout_pdf.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- tests\golden\test_typography_consistency.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- tests\unit\test_cache_v2.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- tests\unit\test_preview_types.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- tests\unit\test_shared_render_core.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- tests\unit\test_typography.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- ui\preview.py: font_hanzi_pt/hanzi_font_size_pt → hanzi_font_size_pt
- scripts\resolve_field_duplication.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- services\cache_v2.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- services\preview_types.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- services\render_core.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- services\typography.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- src\layout_pdf.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- tests\golden\test_typography_consistency.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- tests\unit\test_cache_v2.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- tests\unit\test_preview_types.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- tests\unit\test_shared_render_core.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- tests\unit\test_typography.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- ui\preview.py: font_pinyin_pt/pinyin_font_size_pt → pinyin_font_size_pt
- scripts\resolve_field_duplication.py: font_english_pt/english_font_size_pt → english_font_size_pt
- services\cache_v2.py: font_english_pt/english_font_size_pt → english_font_size_pt
- services\preview_types.py: font_english_pt/english_font_size_pt → english_font_size_pt
- services\render_core.py: font_english_pt/english_font_size_pt → english_font_size_pt
- services\typography.py: font_english_pt/english_font_size_pt → english_font_size_pt
- src\layout_pdf.py: font_english_pt/english_font_size_pt → english_font_size_pt
- tests\golden\test_typography_consistency.py: font_english_pt/english_font_size_pt → english_font_size_pt
- tests\unit\test_cache_v2.py: font_english_pt/english_font_size_pt → english_font_size_pt
- tests\unit\test_preview_types.py: font_english_pt/english_font_size_pt → english_font_size_pt
- tests\unit\test_shared_render_core.py: font_english_pt/english_font_size_pt → english_font_size_pt
- tests\unit\test_typography.py: font_english_pt/english_font_size_pt → english_font_size_pt
- ui\preview.py: font_english_pt/english_font_size_pt → english_font_size_pt
- core\state.py: hanzi_font/hanzi_font_family → hanzi_font_family
- services\preview_types.py: hanzi_font/hanzi_font_family → hanzi_font_family
- services\typography.py: hanzi_font/hanzi_font_family → hanzi_font_family
- src\layout_pptx.py: hanzi_font/hanzi_font_family → hanzi_font_family
- ui\adapter_showcase.py: hanzi_font/hanzi_font_family → hanzi_font_family
- ui\form_components.py: hanzi_font/hanzi_font_family → hanzi_font_family
- ui\options.py: hanzi_font/hanzi_font_family → hanzi_font_family

