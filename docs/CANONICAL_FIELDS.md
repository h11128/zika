# Canonical Field Names Reference

**Generated**: 2025-08-30 22:25:06

This document defines the canonical field names used throughout the application.

## Typography Fields

- **`hanzi_font_size_pt`**: Font size for Chinese characters in points
- **`pinyin_font_size_pt`**: Font size for pinyin in points
- **`english_font_size_pt`**: Font size for English in points
- **`hanzi_font_family`**: Font family for Chinese characters
- **`pinyin_font_family`**: Font family for pinyin
- **`english_font_family`**: Font family for English
- **`line_height_multiplier`**: Line height multiplier for text

## Layout Fields

- **`layout_rows`**: Number of rows in layout grid
- **`layout_cols`**: Number of columns in layout grid
- **`card_size_cm`**: Card size in centimeters
- **`gap_cm`**: Gap between cards in centimeters
- **`margin_cm`**: Page margin in centimeters
- **`layout_auto_fill`**: Whether to auto-fill empty cards

## Visual Fields

- **`background_color`**: Background color (hex)
- **`border_color`**: Border color (hex)
- **`text_color`**: Text color (hex)
- **`hanzi_color`**: Chinese character color (hex)
- **`pinyin_color`**: Pinyin text color (hex)
- **`english_color`**: English text color (hex)

## Page Fields

- **`page_size`**: Page size (A4, Letter, etc.)
- **`page_width_cm`**: Page width in centimeters
- **`page_height_cm`**: Page height in centimeters
- **`orientation`**: Page orientation (portrait/landscape)

## Field Mapping Rules

The following mappings are applied to resolve field duplications:

- `hanzi_font_size_pt` → `hanzi_font_size_pt`: Standardize hanzi font size field
- `pinyin_font_size_pt` → `pinyin_font_size_pt`: Standardize pinyin font size field
- `english_font_size_pt` → `english_font_size_pt`: Standardize english font size field
- `hanzi_font_family` → `hanzi_font_family`: Standardize hanzi font family field
- `pinyin_font` → `pinyin_font_family`: Standardize pinyin font family field
- `english_font` → `english_font_family`: Standardize english font family field
- `gap` → `gap_cm`: Standardize gap field with unit
- `margin` → `margin_cm`: Standardize margin field with unit
- `card_size` → `card_size_cm`: Standardize card size field with unit
- `rows` → `layout_rows`: Standardize rows field with layout prefix
- `cols` → `layout_cols`: Standardize cols field with layout prefix
- `auto_fill` → `layout_auto_fill`: Standardize auto_fill field with layout prefix
