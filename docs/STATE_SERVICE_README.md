# State Service Documentation

## Overview

The State Service (`ui/state.py`) is the central state management system for the Chinese Character Learning Cards application. It provides a unified, rule-based approach to managing application state with automatic validation, digest computation, and change tracking.

## Architecture

### Core Components

1. **StateService**: Main state management class
2. **Rule Engine**: Automatic field normalization and validation
3. **Digest System**: Deterministic cache invalidation
4. **Change Tracking**: Domain-specific change detection
5. **Session Management**: Session generation and lifecycle

### Key Features

- **Atomic Operations**: Batch updates with rollback capability
- **Rule-Based Validation**: Automatic field normalization
- **Digest-Driven Caching**: Intelligent cache invalidation
- **Session Isolation**: Multi-user session boundaries
- **Change Detection**: Fine-grained change tracking

## Usage Examples

### Basic State Operations

```python
from ui.state import get_state_service

# Get state service instance
state = get_state_service()

# Set single option
changed = state.set_option('rows', 4)
if changed:
    print("Rows changed, preview will refresh")

# Get current value
current_rows = state.get_option('rows', default=3)

# Batch updates
changes = {
    'rows': 4,
    'cols': 3,
    'card_size': 6.0
}
changeset = state.set_options_batch(changes)
print(f"Layout affected: {changeset.affects_layout}")
```

### Rule Engine Integration

```python
# Rules are automatically applied
state.set_option('gap', 0.3)  # Automatically converts to gap_cm
state.set_option('margin', 1.2)  # Automatically converts to margin_cm

# Auto card size computation
state.set_options_batch({
    'rows': 4,
    'cols': 3,
    'page_size': 'A4'
})
# card_size is automatically computed based on layout
```

### Digest Computation

```python
# Get domain-specific digests
processing_digest = state.get_processing_digest()
layout_digest = state.get_layout_digest()
style_digest = state.get_style_digest()

# Get combined preview digest
preview_digest = state.get_preview_params_digest()

# Check if digest changed
if state.digest_changed('layout', previous_digest):
    # Layout changed, need to refresh preview
    pass
```

## Rule Engine

### Automatic Field Normalization

The rule engine automatically normalizes fields to ensure consistency:

```python
# Unit conversion
'gap' -> 'gap_cm'
'margin' -> 'margin_cm'

# Value clamping
rows: 1-10
cols: 1-10
card_size: 3.0-12.0 cm

# Auto computation
card_size = compute_auto_card_size_cm(rows, cols, page_size)
```

### Rule Categories

1. **Unit Rules**: Convert legacy units to standard units
2. **Range Rules**: Clamp values to valid ranges
3. **Dependency Rules**: Update dependent fields automatically
4. **Validation Rules**: Ensure data consistency

### Custom Rules

```python
def custom_rule(key: str, value: Any, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """Custom rule implementation."""
    changes = {}
    
    if key == 'special_field':
        # Apply custom logic
        changes['dependent_field'] = compute_dependent_value(value)
    
    return changes

# Register custom rule
state.add_rule('special_field', custom_rule)
```

## Digest System

### Domain-Specific Digests

The state service computes separate digests for different domains:

- **Processing Digest**: Input text, segmentation settings
- **Layout Digest**: Rows, cols, card size, page settings
- **Style Digest**: Fonts, colors, typography settings
- **Navigation Digest**: Current page, pagination state

### Digest Computation

```python
def get_layout_digest(self) -> str:
    """Compute layout digest for cache invalidation."""
    layout_data = {
        'rows': self.get_option('rows'),
        'cols': self.get_option('cols'),
        'card_size': self.get_option('card_size'),
        'page_size': self.get_option('page_size'),
        'auto_fill': self.get_option('auto_fill')
    }
    return stable_digest(layout_data)
```

### Cache Integration

```python
# Check if cache is valid
cache_key = f"preview_{preview_digest}"
cached_result = cache.get(cache_key)

if cached_result is None:
    # Generate new content
    result = generate_preview(cards, layout_params)
    cache.set(cache_key, result)
else:
    result = cached_result
```

## Change Tracking

### ChangeSet System

The state service tracks which domains are affected by changes:

```python
@dataclass
class ChangeSet:
    affects_processing: bool = False
    affects_layout: bool = False
    affects_style: bool = False
    affects_navigation: bool = False
    
    def any_change(self) -> bool:
        return any([
            self.affects_processing,
            self.affects_layout,
            self.affects_style,
            self.affects_navigation
        ])
```

### Change Detection Logic

```python
def detect_changes(self, changes: Dict[str, Any]) -> ChangeSet:
    """Detect which domains are affected by changes."""
    changeset = ChangeSet()
    
    for key in changes:
        if key in PROCESSING_FIELDS:
            changeset.affects_processing = True
        elif key in LAYOUT_FIELDS:
            changeset.affects_layout = True
        elif key in STYLE_FIELDS:
            changeset.affects_style = True
        elif key in NAVIGATION_FIELDS:
            changeset.affects_navigation = True
    
    return changeset
```

## Session Management

### Session Generation

```python
def get_session_generation(self) -> str:
    """Get current session generation."""
    if 'session_generation' not in st.session_state:
        st.session_state.session_generation = generate_session_id()
    return st.session_state.session_generation

def reset_session(self):
    """Reset session generation (forces cache invalidation)."""
    st.session_state.session_generation = generate_session_id()
```

### Session Isolation

- Each browser tab gets a unique session
- Session state is isolated between users
- Session generation included in cache keys
- Automatic session cleanup on browser close

## Performance Considerations

### Batch Operations

Always use batch operations for multiple changes:

```python
# Good: Single batch operation
state.set_options_batch({
    'rows': 4,
    'cols': 3,
    'card_size': 6.0
})

# Bad: Multiple individual operations
state.set_option('rows', 4)
state.set_option('cols', 3)
state.set_option('card_size', 6.0)
```

### Digest Caching

Digests are cached within a single request:

```python
# First call computes digest
digest1 = state.get_layout_digest()

# Subsequent calls return cached value
digest2 = state.get_layout_digest()  # Same as digest1
```

### Memory Management

- State service uses weak references where possible
- Automatic cleanup of expired cache entries
- Memory usage monitoring and alerts

## Error Handling

### Validation Errors

```python
try:
    state.set_option('rows', 15)  # Invalid: exceeds maximum
except ValueError as e:
    print(f"Validation error: {e}")
```

### Rule Engine Errors

```python
try:
    changeset = state.set_options_batch(invalid_changes)
except RuleEngineError as e:
    print(f"Rule engine error: {e}")
    # Rollback to previous state
    state.rollback()
```

### Graceful Degradation

- Invalid values are clamped to valid ranges
- Missing fields use sensible defaults
- Partial updates succeed even if some fields fail

## Testing

### Unit Tests

```python
def test_rule_engine():
    """Test rule engine functionality."""
    state = StateService()
    
    # Test unit conversion
    state.set_option('gap', 0.5)
    assert state.get_option('gap_cm') == 0.5
    
    # Test auto computation
    state.set_options_batch({'rows': 4, 'cols': 3, 'page_size': 'A4'})
    card_size = state.get_option('card_size')
    assert 3.0 <= card_size <= 12.0
```

### Integration Tests

```python
def test_digest_integration():
    """Test digest computation and caching."""
    state = StateService()
    
    # Get initial digest
    digest1 = state.get_layout_digest()
    
    # Change layout
    state.set_option('rows', 5)
    digest2 = state.get_layout_digest()
    
    # Digest should change
    assert digest1 != digest2
```

## Best Practices

### State Updates

1. **Use Batch Operations**: For multiple related changes
2. **Check Return Values**: Verify if changes actually occurred
3. **Handle Validation**: Wrap updates in try-catch blocks
4. **Use Digests**: For cache invalidation decisions

### Rule Engine

1. **Keep Rules Simple**: Each rule should have a single responsibility
2. **Avoid Side Effects**: Rules should be pure functions
3. **Test Thoroughly**: Rules affect application behavior
4. **Document Dependencies**: Clear documentation of field relationships

### Performance

1. **Minimize State Access**: Cache frequently used values
2. **Use Appropriate Digests**: Only compute digests you need
3. **Batch Related Changes**: Reduce rule engine overhead
4. **Monitor Performance**: Track digest computation time

---

**Document Version**: 1.0  
**Last Updated**: August 2024  
**Next Review**: November 2024
