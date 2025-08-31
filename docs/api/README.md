# API Documentation

This directory contains comprehensive API documentation for the Chinese Flashcard Application.

## Overview

The Chinese Flashcard Application provides a clean, modular API for creating, managing, and exporting Chinese language flashcards. The API is designed with separation of concerns, using ports and adapters architecture for maximum testability and flexibility.

## Core Components

### Services Layer
- **Layout Service** (`services/layout.py`) - Handles card layout calculations and pagination
- **State Service** (`ui/state.py`) - Manages application state and user preferences
- **Export Service** - Handles PDF and PowerPoint export functionality

### UI Layer
- **Ports** (`ui/ports.py`) - Abstract interfaces for UI components
- **Adapters** - Concrete implementations for different UI frameworks

### Data Models
- **Card Models** - Represent individual flashcards with Chinese characters, pinyin, and English
- **Layout Models** - Define page layouts, typography, and visual options
- **Export Models** - Configure export parameters and formats

## Quick Start

```python
from services.layout import compute_auto_card_size_cm, paginate
from ui.state import get_state_service

# Initialize state service
state = get_state_service()

# Configure layout
state.set_option('layout_rows', 3)
state.set_option('layout_cols', 4)
state.set_option('page_size', 'A4')

# Calculate optimal card size
card_size = compute_auto_card_size_cm(
    page_size='A4',
    margin_cm=1.0,
    gap_cm=0.5,
    layout_rows=3,
    layout_cols=4
)

# Get pagination info
pagination = paginate(
    cards_count=24,
    layout_rows=3,
    layout_cols=4
)
```

## API Reference

### Layout Service API

#### `compute_auto_card_size_cm(page_size, margin_cm, gap_cm, layout_rows, layout_cols)`

Computes optimal card size for given layout parameters.

**Parameters:**
- `page_size` (str): Page size ('A4', 'Letter', etc.)
- `margin_cm` (float): Page margin in centimeters
- `gap_cm` (float): Gap between cards in centimeters
- `layout_rows` (int): Number of rows in layout
- `layout_cols` (int): Number of columns in layout

**Returns:**
- `float`: Optimal card size in centimeters

**Example:**
```python
card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
# Returns: 8.73 (cm)
```

#### `paginate(cards_count, layout_rows, layout_cols)`

Calculates pagination information for given card count and layout.

**Parameters:**
- `cards_count` (int): Total number of cards
- `layout_rows` (int): Number of rows per page
- `layout_cols` (int): Number of columns per page

**Returns:**
- `PaginateInfo`: Object containing pagination details

**Example:**
```python
pagination = paginate(20, 2, 3)
# Returns: PaginateInfo(total_pages=4, cards_per_page=6, last_page_cards=2)
```

### State Service API

#### `get_state_service()`

Returns the singleton state service instance.

**Returns:**
- `StateService`: The application state service

#### `StateService.get_option(key, default=None)`

Gets a configuration option value.

**Parameters:**
- `key` (str): Option key
- `default` (any): Default value if key not found

**Returns:**
- `any`: Option value or default

#### `StateService.set_option(key, value)`

Sets a configuration option value.

**Parameters:**
- `key` (str): Option key
- `value` (any): Option value

**Returns:**
- `bool`: True if value changed, False otherwise

#### `StateService.set_options_batch(options)`

Sets multiple options in a single batch operation.

**Parameters:**
- `options` (dict): Dictionary of key-value pairs

**Returns:**
- `bool`: True if any value changed, False otherwise

### UI Ports API

#### `UIAdapter`

Abstract base class for UI adapters.

**Methods:**
- `inputs`: Property returning `UIInputsPort` instance
- `preview`: Property returning `UIPreviewPort` instance
- `notifications`: Property returning `UINotificationPort` instance
- `refresh_scheduler`: Property returning `UIRefreshScheduler` instance

#### `UIInputsPort`

Abstract interface for user input components.

**Methods:**
- `text_input(key, default="", on_change=None)`: Text input widget
- `number_input(key, default=0, min_value=None, max_value=None, on_change=None)`: Number input widget
- `selectbox(key, options, index=0)`: Selection dropdown widget
- `checkbox(key, default=False)`: Checkbox widget
- `button(label, on_click=None)`: Button widget

#### `UIPreviewPort`

Abstract interface for content preview.

**Methods:**
- `html(content, height=None)`: Display HTML content
- `markdown(content)`: Display Markdown content
- `text(content)`: Display plain text content

#### `UINotificationPort`

Abstract interface for user notifications.

**Methods:**
- `show_success(message)`: Show success notification
- `show_error(message)`: Show error notification
- `show_warning(message)`: Show warning notification
- `show_info(message)`: Show information notification

## Data Models

### Card Model

```python
@dataclass
class Card:
    uuid: str
    hanzi: str
    pinyin: str = ""
    english: str = ""
    version: int = 1
    created_at: float = field(default_factory=time.time)
```

### Layout Options

```python
@dataclass
class LayoutOptions:
    layout_rows: int = 2
    layout_cols: int = 3
    page_size: str = 'A4'
    margin_cm: float = 1.0
    gap_cm: float = 0.5
    card_size_cm: float = 8.0
    layout_auto_fill: bool = True
```

### Typography Options

```python
@dataclass
class Typography:
    hanzi_font_size_pt: int = 48
    pinyin_font_size_pt: int = 18
    english_font_size_pt: int = 14
    hanzi_font_family: str = "SimSun"
    pinyin_font_family: str = "Arial"
    english_font_family: str = "Arial"
```

### Visual Options

```python
@dataclass
class VisualOptions:
    background_color: str = '#FFFFFF'
    text_color: str = '#000000'
    border_color: str = '#CCCCCC'
    border_width_pt: float = 1.0
    corner_radius_pt: float = 4.0
```

## Error Handling

The API uses standard Python exceptions with descriptive messages:

```python
try:
    card_size = compute_auto_card_size_cm('InvalidSize', 1.0, 0.5, 2, 3)
except ValueError as e:
    print(f"Invalid page size: {e}")

try:
    state.set_option('invalid_key', 'value')
except KeyError as e:
    print(f"Unknown option: {e}")
```

## Performance Considerations

### Caching

The application implements intelligent caching:
- Preview cache with content-based keys
- Export cache with version-aware invalidation
- Layout cache for expensive calculations

### Memory Management

- Automatic garbage collection of unused cache entries
- Memory-efficient data structures
- Lazy loading of large datasets

### Batch Operations

Use batch operations for better performance:

```python
# Good: Batch operation
state.set_options_batch({
    'layout_rows': 3,
    'layout_cols': 4,
    'card_size_cm': 7.5
})

# Avoid: Multiple individual operations
state.set_option('layout_rows', 3)
state.set_option('layout_cols', 4)
state.set_option('card_size_cm', 7.5)
```

## Testing

The API is thoroughly tested with:
- Unit tests for individual functions
- Integration tests for component interactions
- End-to-end tests for complete workflows
- Performance tests for scalability
- Security tests for input validation

Run tests with:
```bash
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/performance/
pytest tests/security/
```

## Migration Guide

### From v1 to v2

Key changes in v2:
- Unified state management
- Improved caching system
- Enhanced error handling
- Better type safety

Migration steps:
1. Update import statements
2. Replace direct state access with state service
3. Update cache key generation
4. Handle new exception types

## Contributing

When extending the API:
1. Follow existing patterns and conventions
2. Add comprehensive tests
3. Update documentation
4. Ensure backward compatibility
5. Consider performance implications

## Support

For API questions and issues:
- Check the test files for usage examples
- Review the source code for implementation details
- Create issues for bugs or feature requests
