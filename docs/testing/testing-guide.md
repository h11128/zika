# Testing Guide

This guide covers the comprehensive testing strategy for the Chinese Flashcard Application, including unit tests, integration tests, end-to-end tests, performance tests, and security tests.

## Table of Contents

1. [Testing Overview](#testing-overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Unit Testing](#unit-testing)
5. [Integration Testing](#integration-testing)
6. [End-to-End Testing](#end-to-end-testing)
7. [Performance Testing](#performance-testing)
8. [Security Testing](#security-testing)
9. [Test Coverage](#test-coverage)
10. [Continuous Integration](#continuous-integration)
11. [Best Practices](#best-practices)

## Testing Overview

The application uses a multi-layered testing approach to ensure reliability, performance, and security:

- **Unit Tests**: Test individual functions and components in isolation
- **Integration Tests**: Test component interactions and data flow
- **End-to-End Tests**: Test complete user workflows without sleeps
- **Performance Tests**: Validate performance baselines and scalability
- **Security Tests**: Ensure XSS protection, input validation, and accessibility

### Testing Philosophy

- **Event-driven testing**: Use callbacks and events instead of hardcoded timeouts
- **Realistic scenarios**: Test with real user data and edge cases
- **Comprehensive coverage**: Aim for >90% code coverage with meaningful tests
- **Fast feedback**: Tests should run quickly and provide clear failure messages

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_layout.py      # Layout service tests
│   ├── test_state.py       # State management tests
│   └── test_utils.py       # Utility function tests
├── integration/             # Integration tests
│   ├── test_navigation_behavior.py
│   ├── test_cache_invalidation.py
│   ├── test_session_isolation.py
│   ├── test_ui_adapter_integration.py
│   └── test_export_cache_integration.py
├── e2e/                    # End-to-end tests
│   ├── test_hydration_behavior.py
│   ├── test_editor_apply_by_id.py
│   ├── test_csv_segmentation_errors.py
│   ├── test_cache_hit_miss.py
│   └── test_golden_html_normalization.py
├── performance/            # Performance tests
│   ├── test_render_performance.py
│   ├── test_cache_performance.py
│   └── test_memory_performance.py
├── security/               # Security tests
│   ├── test_xss_protection.py
│   ├── test_dependency_security.py
│   └── test_accessibility.py
├── fixtures/               # Test data and fixtures
│   ├── sample_cards.json
│   ├── test_layouts.json
│   └── mock_data.py
└── conftest.py            # Pytest configuration
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-cov pytest-mock pytest-asyncio
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/
pytest tests/performance/
pytest tests/security/

# Run specific test file
pytest tests/unit/test_layout.py

# Run specific test function
pytest tests/unit/test_layout.py::test_compute_auto_card_size_cm

# Run tests with verbose output
pytest -v

# Run tests with coverage
pytest --cov=src --cov-report=html
```

### Test Configuration

Configure pytest in `pytest.ini`:
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --disable-warnings
    --tb=short
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    performance: Performance tests
    security: Security tests
    slow: Slow running tests
```

### Running Tests by Category

```bash
# Run only unit tests
pytest -m unit

# Run only fast tests
pytest -m "not slow"

# Run performance tests with extended timeout
pytest -m performance --timeout=300

# Run security tests
pytest -m security
```

## Unit Testing

Unit tests focus on testing individual functions and components in isolation.

### Layout Service Tests

```python
def test_compute_auto_card_size_cm():
    """Test automatic card size computation."""
    # Test standard A4 layout
    card_size = compute_auto_card_size_cm('A4', 1.0, 0.5, 2, 3)
    assert 8.0 <= card_size <= 9.0
    
    # Test edge cases
    with pytest.raises(ValueError):
        compute_auto_card_size_cm('InvalidSize', 1.0, 0.5, 2, 3)

def test_paginate():
    """Test pagination logic."""
    result = paginate(20, 2, 3)
    assert result.total_pages == 4
    assert result.cards_per_page == 6
    assert result.last_page_cards == 2
```

### State Management Tests

```python
def test_state_service_singleton():
    """Test that state service is a singleton."""
    state1 = get_state_service()
    state2 = get_state_service()
    assert state1 is state2

def test_option_management():
    """Test option get/set operations."""
    state = get_state_service()
    
    # Test setting and getting options
    assert state.set_option('test_key', 'test_value')
    assert state.get_option('test_key') == 'test_value'
    
    # Test default values
    assert state.get_option('nonexistent', 'default') == 'default'
```

### Mocking and Fixtures

```python
@pytest.fixture
def mock_cards():
    """Fixture providing sample cards for testing."""
    return [
        {'uuid': 'card-1', 'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
        {'uuid': 'card-2', 'hanzi': '世界', 'pinyin': 'shì jiè', 'english': 'world'},
    ]

@patch('services.layout.get_page_dimensions')
def test_layout_with_mock(mock_get_dimensions, mock_cards):
    """Test layout computation with mocked dependencies."""
    mock_get_dimensions.return_value = (21.0, 29.7)  # A4 dimensions
    
    result = compute_layout(mock_cards, 'A4', 2, 3)
    assert result is not None
    mock_get_dimensions.assert_called_once_with('A4')
```

## Integration Testing

Integration tests verify that components work correctly together.

### Navigation Behavior Tests

```python
def test_page_navigation_integration():
    """Test page navigation with state management."""
    state = get_state_service()
    navigator = PageNavigator(state)
    
    # Set up test data
    state.set_option('total_pages', 5)
    state.set_option('current_page', 1)
    
    # Test navigation
    navigator.next_page()
    assert state.get_option('current_page') == 2
    
    navigator.previous_page()
    assert state.get_option('current_page') == 1
```

### Cache Invalidation Tests

```python
def test_cache_invalidation_on_state_change():
    """Test that cache is invalidated when state changes."""
    cache = MockCacheManager()
    state = get_state_service()
    
    # Set up cache invalidation listener
    state.add_change_listener(cache.invalidate_on_change)
    
    # Populate cache
    cache.set('preview_key', 'cached_content')
    
    # Change state that should invalidate cache
    state.set_option('layout_rows', 3)
    
    # Verify cache was invalidated
    assert cache.get('preview_key') is None
```

## End-to-End Testing

E2E tests validate complete user workflows using event-driven approaches.

### Hydration Testing

```python
def test_hydration_single_rerun():
    """Test that hydration triggers exactly one rerun."""
    session = MockStreamlitSession()
    storage = MockBrowserStorage()
    
    # Set up hydration data
    hydration_data = {
        'version': 3,
        'session_id': 'test-session',
        'input_text': '你好 世界',
        'cards': [{'uuid': 'card-1', 'hanzi': '你好'}]
    }
    
    # Trigger hydration
    storage.trigger_hydration(hydration_data)
    
    if storage.is_hydration_triggered():
        session.rerun()
    
    # Verify exactly one rerun
    assert session.get_rerun_count() == 1
```

### Editor Apply-by-ID Testing

```python
def test_editor_apply_by_uuid():
    """Test editor apply functionality with stable UUIDs."""
    editor = MockCardEditor()
    
    # Add cards
    card = MockCard("card-1", "你好", "nǐ hǎo", "hello")
    editor.add_card(card)
    
    # Stage changes
    editor.stage_change("card-1", "english", "hi")
    
    # Apply changes
    applied = editor.apply_changes()
    
    # Verify changes applied
    assert len(applied) == 1
    assert applied[0][0] == "card-1"
    assert applied[0][1] == {"english": "hi"}
```

## Performance Testing

Performance tests validate that the application meets performance baselines.

### Render Performance Tests

```python
def test_first_render_baseline():
    """Test first render meets <500ms baseline."""
    render_engine = MockRenderEngine()
    cards_data = generate_test_cards(50)
    
    monitor = PerformanceMonitor()
    monitor.start_monitoring()
    
    result = render_engine.render_preview(cards_data, "test_digest")
    
    monitor.end_monitoring()
    metrics = monitor.get_metrics()
    
    # Verify baseline compliance
    assert metrics['duration_ms'] < 500
```

### Cache Performance Tests

```python
def test_cache_hit_rate_baseline():
    """Test cache hit rate meets >80% baseline."""
    cache = PerformanceCacheManager()
    
    # Simulate realistic access pattern
    for i in range(1000):
        key = f"key_{i % 20}"  # 20 unique keys, repeated access
        cache.get(key) or cache.set(key, f"value_{i}")
    
    stats = cache.get_stats()
    assert stats['hit_rate'] >= 0.8
```

### Memory Performance Tests

```python
def test_memory_baseline():
    """Test memory usage stays within baseline."""
    tracker = MemoryTracker()
    processor = MockDataProcessor()
    
    tracker.take_snapshot("baseline")
    
    # Perform memory-intensive operations
    for i in range(5):
        processor.process_large_dataset(size_mb=1)
        tracker.take_snapshot(f"operation_{i}")
    
    peak_memory = tracker.get_peak_memory()
    assert peak_memory < 150  # MB baseline
```

## Security Testing

Security tests ensure the application is protected against common vulnerabilities.

### XSS Protection Tests

```python
def test_script_tag_removal():
    """Test that script tags are removed."""
    sanitizer = HTMLSanitizer()
    malicious_html = '<div>Hello <script>alert("XSS")</script> World</div>'
    
    sanitized = sanitizer.sanitize_html(malicious_html)
    
    assert '<script>' not in sanitized
    assert 'alert(' not in sanitized
```

### Input Validation Tests

```python
def test_chinese_text_validation():
    """Test validation of Chinese text input."""
    sanitizer = HTMLSanitizer()
    
    valid_inputs = ['你好世界', '学习中文很有趣']
    invalid_inputs = ['<script>alert("XSS")</script>', 'javascript:alert(1)']
    
    for valid_input in valid_inputs:
        escaped = sanitizer.escape_user_input(valid_input)
        assert len(escaped) > 0
    
    for invalid_input in invalid_inputs:
        escaped = sanitizer.escape_user_input(invalid_input)
        assert '<script>' not in escaped
        assert 'javascript:' not in escaped
```

### Accessibility Tests

```python
def test_wcag_aa_contrast_compliance():
    """Test WCAG AA contrast compliance."""
    checker = AccessibilityChecker()
    
    test_cases = [
        ('#000000', '#FFFFFF', True),   # Black on white - should pass
        ('#CCCCCC', '#FFFFFF', False), # Light gray on white - should fail
    ]
    
    for fg, bg, should_pass in test_cases:
        result = checker.check_color_contrast(fg, bg, 12, False)
        assert result['wcag_aa_compliant'] == should_pass
```

## Test Coverage

### Coverage Goals

- **Overall Coverage**: >90%
- **Critical Paths**: 100%
- **New Code**: 100%
- **Security Functions**: 100%

### Generating Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html --cov-report=term

# Generate XML coverage report (for CI)
pytest --cov=src --cov-report=xml

# Coverage with branch analysis
pytest --cov=src --cov-branch --cov-report=html
```

### Coverage Configuration

Configure coverage in `.coveragerc`:
```ini
[run]
source = src
omit = 
    */tests/*
    */venv/*
    */migrations/*
    */settings/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

## Continuous Integration

### GitHub Actions Workflow

Create `.github/workflows/test.yml`:
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10']

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=src
    
    - name: Run integration tests
      run: pytest tests/integration/ -v
    
    - name: Run E2E tests
      run: pytest tests/e2e/ -v
    
    - name: Run performance tests
      run: pytest tests/performance/ -v
    
    - name: Run security tests
      run: pytest tests/security/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

Configure pre-commit hooks in `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-unit
        name: pytest-unit
        entry: pytest tests/unit/
        language: system
        pass_filenames: false
        always_run: true
      
      - id: pytest-security
        name: pytest-security
        entry: pytest tests/security/
        language: system
        pass_filenames: false
        always_run: true
```

## Best Practices

### Test Writing Guidelines

1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: Each test should test one thing
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Independent Tests**: Tests should not depend on each other
5. **Fast Execution**: Keep tests fast and focused

### Mock Usage

```python
# Good: Mock external dependencies
@patch('external_service.api_call')
def test_with_external_dependency(mock_api):
    mock_api.return_value = {'status': 'success'}
    result = my_function()
    assert result is not None

# Avoid: Over-mocking internal logic
# Don't mock the code you're testing
```

### Test Data Management

```python
# Use fixtures for reusable test data
@pytest.fixture
def sample_cards():
    return [
        Card(uuid='1', hanzi='你好', pinyin='nǐ hǎo', english='hello'),
        Card(uuid='2', hanzi='世界', pinyin='shì jiè', english='world'),
    ]

# Use factories for dynamic test data
def create_card(hanzi='测试', **kwargs):
    defaults = {'pinyin': 'cèshì', 'english': 'test'}
    defaults.update(kwargs)
    return Card(hanzi=hanzi, **defaults)
```

### Debugging Failed Tests

```bash
# Run with detailed output
pytest -vvv --tb=long

# Run specific failing test
pytest tests/unit/test_layout.py::test_failing_function -vvv

# Drop into debugger on failure
pytest --pdb

# Run with print statements visible
pytest -s
```

Remember: Good tests are your safety net for refactoring and adding new features. Invest time in writing comprehensive, maintainable tests!
