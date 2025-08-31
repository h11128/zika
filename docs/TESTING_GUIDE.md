# Testing Guide

## Overview

This guide covers the comprehensive testing strategy for the Chinese Character Learning Cards application, including unit tests, integration tests, end-to-end tests, and performance testing.

## Testing Architecture

### Test Categories

1. **Unit Tests**: Test individual functions and classes in isolation
2. **Integration Tests**: Test component interactions and data flow
3. **End-to-End Tests**: Test complete user workflows
4. **Performance Tests**: Test performance characteristics and regressions
5. **Golden Tests**: Test consistency between preview and export

### Test Structure

```text
tests/
├── unit/                     # Unit tests
│   ├── test_cache_v2.py      # Cache system tests
│   ├── test_preview_types.py # Data structure tests
│   ├── test_shared_render_core.py # Rendering tests
│   └── test_state_service.py # State management tests
├── integration/              # Integration tests
│   ├── test_preview_pipeline.py # Preview pipeline tests
│   ├── test_ui_adapters.py   # UI adapter tests
│   └── test_export_workflow.py # Export workflow tests
├── e2e/                      # End-to-end tests
│   ├── test_user_workflows.py # Complete user scenarios
│   └── test_performance.py   # Performance regression tests
└── fixtures/                 # Test data and fixtures
    ├── sample_cards.json     # Sample card data
    └── expected_outputs/     # Golden test outputs
```

## Unit Testing

### Test Framework Setup

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Test configuration
pytest_plugins = ["pytest_cov", "pytest_mock"]

@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory."""
    return Path(__file__).parent / "fixtures"

@pytest.fixture
def temp_dir():
    """Provide temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)
```

### Cache System Testing

```python
class TestCacheV2:
    """Test cache v2 functionality."""
    
    @pytest.fixture
    def cache_config(self):
        """Provide cache configuration for testing."""
        return CacheConfig(
            max_entries=10,
            max_size_bytes=1024,
            ttl_seconds=60
        )
    
    def test_cache_basic_operations(self, cache_config):
        """Test basic cache operations."""
        cache = CacheV2(cache_config)
        
        # Test miss
        assert cache.get("key1") is None
        assert cache.stats.misses == 1
        
        # Test set and hit
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.stats.hits == 1
        assert cache.stats.entry_count == 1
    
    def test_cache_ttl_expiration(self, cache_config):
        """Test TTL expiration."""
        cache_config.ttl_seconds = 0.1
        cache = CacheV2(cache_config)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        import time
        time.sleep(0.2)
        assert cache.get("key1") is None
        assert cache.stats.misses == 1
    
    def test_cache_size_eviction(self, cache_config):
        """Test size-based eviction."""
        cache_config.max_size_bytes = 50
        cache = CacheV2(cache_config)
        
        # Add entries that exceed size limit
        cache.set("key1", "a" * 30)  # 30 bytes
        cache.set("key2", "b" * 30)  # 30 bytes - should evict key1
        
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "b" * 30  # Still there
        assert cache.stats.evictions >= 1
```

### State Service Testing

```python
class TestStateService:
    """Test state service functionality."""
    
    @pytest.fixture
    def state_service(self):
        """Provide state service for testing."""
        return StateService()
    
    def test_rule_engine_unit_conversion(self, state_service):
        """Test rule engine unit conversion."""
        # Test gap conversion
        state_service.set_option('gap', 0.5)
        assert state_service.get_option('gap_cm') == 0.5
        
        # Test margin conversion
        state_service.set_option('margin', 1.0)
        assert state_service.get_option('margin_cm') == 1.0
    
    def test_rule_engine_auto_computation(self, state_service):
        """Test automatic card size computation."""
        state_service.set_options_batch({
            'rows': 4,
            'cols': 3,
            'page_size': 'A4'
        })
        
        card_size = state_service.get_option('card_size')
        assert 3.0 <= card_size <= 12.0
    
    def test_digest_computation(self, state_service):
        """Test digest computation."""
        # Get initial digest
        digest1 = state_service.get_layout_digest()
        
        # Change layout
        state_service.set_option('rows', 5)
        digest2 = state_service.get_layout_digest()
        
        # Digest should change
        assert digest1 != digest2
        
        # Non-layout changes shouldn't affect layout digest
        state_service.set_option('hanzi_font_size_pt', 24)
        digest3 = state_service.get_layout_digest()
        assert digest2 == digest3
```

## Integration Testing

### UI Adapter Testing

```python
class TestUIAdapters:
    """Test UI adapter system."""
    
    @pytest.fixture
    def fake_adapter(self):
        """Provide fake adapter for testing."""
        adapter = FakeAdapter()
        set_ui_adapter(adapter)
        yield adapter
        adapter.clear_state()
    
    def test_input_component_integration(self, fake_adapter):
        """Test input component with adapter."""
        # Set up test inputs
        fake_adapter.set_input_value("rows", 4)
        fake_adapter.set_input_value("cols", 3)
        
        # Run component
        from ui.inputs import render_layout_inputs
        render_layout_inputs()
        
        # Verify adapter interactions
        content = fake_adapter.get_displayed_content()
        assert any("rows" in item.lower() for item in content)
        assert any("cols" in item.lower() for item in content)
    
    def test_preview_component_integration(self, fake_adapter):
        """Test preview component with adapter."""
        # Set up test data
        cards = [
            {"hanzi": "你好", "pinyin": "nǐ hǎo", "english": "hello"},
            {"hanzi": "世界", "pinyin": "shì jiè", "english": "world"}
        ]
        
        # Run preview component
        from ui.preview import render_preview_section
        render_preview_section(cards)
        
        # Verify preview was displayed
        content = fake_adapter.get_displayed_content()
        assert any("preview" in item.lower() for item in content)
```

### Preview Pipeline Testing

```python
class TestPreviewPipeline:
    """Test preview pipeline integration."""
    
    def test_complete_preview_pipeline(self):
        """Test complete preview generation pipeline."""
        # Set up test data
        cards = generate_test_cards(count=12)
        params = create_test_preview_params()
        
        # Run pipeline
        from ui.preview_controller import create_page_preview_html_unified
        html = create_page_preview_html_unified(cards, page_num=0, params=params)
        
        # Verify output
        assert html is not None
        assert len(html) > 0
        assert "你好" in html  # Should contain Chinese characters
        assert "nǐ hǎo" in html  # Should contain pinyin
        assert "hello" in html  # Should contain English
    
    def test_preview_caching_integration(self):
        """Test preview caching integration."""
        cards = generate_test_cards(count=6)
        params = create_test_preview_params()
        
        # First call should generate content
        html1 = create_page_preview_html_unified(cards, 0, params)
        
        # Second call with same params should use cache
        html2 = create_page_preview_html_unified(cards, 0, params)
        
        # Content should be identical
        assert html1 == html2
        
        # Verify cache was used
        cache_stats = get_cache_stats()
        assert cache_stats['preview'].hits > 0
```

## End-to-End Testing

### Complete User Workflows

```python
class TestUserWorkflows:
    """Test complete user workflows."""
    
    @pytest.fixture
    def app_session(self):
        """Set up complete application session."""
        # Initialize application state
        from ui.app_controller import initialize_app
        initialize_app()
        
        # Set up fake adapter
        adapter = FakeAdapter()
        set_ui_adapter(adapter)
        
        yield adapter
        
        # Cleanup
        adapter.clear_state()
    
    def test_text_input_to_preview_workflow(self, app_session):
        """Test complete text input to preview workflow."""
        # Step 1: User enters text
        app_session.set_input_value("input_text", "你好 世界 中国")
        app_session.set_input_value("generate_button", True)
        
        # Step 2: Process input
        from ui.app_controller import handle_text_input
        handle_text_input()
        
        # Step 3: Verify cards were generated
        from ui.state import get_state_service
        state = get_state_service()
        cards = state.get_option('cards', [])
        assert len(cards) == 3
        assert cards[0]['hanzi'] == '你好'
        
        # Step 4: Generate preview
        from ui.app_controller import render_preview
        render_preview()
        
        # Step 5: Verify preview was displayed
        content = app_session.get_displayed_content()
        assert any("preview" in item.lower() for item in content)
        assert any("你好" in item for item in content)
    
    def test_csv_upload_to_export_workflow(self, app_session, temp_dir):
        """Test CSV upload to export workflow."""
        # Step 1: Create test CSV
        csv_file = temp_dir / "test_cards.csv"
        csv_content = "hanzi,pinyin,english\n你好,nǐ hǎo,hello\n世界,shì jiè,world"
        csv_file.write_text(csv_content, encoding='utf-8')
        
        # Step 2: Upload CSV
        app_session.set_input_value("csv_upload", csv_file)
        
        # Step 3: Process upload
        from ui.app_controller import handle_csv_upload
        handle_csv_upload()
        
        # Step 4: Configure export
        app_session.set_input_value("export_format", "PDF")
        app_session.set_input_value("export_button", True)
        
        # Step 5: Generate export
        from ui.app_controller import handle_export
        result = handle_export()
        
        # Step 6: Verify export
        assert result.success
        assert result.file_path.exists()
        assert result.file_path.suffix == '.pdf'
```

## Performance Testing

### Performance Benchmarks

```python
class TestPerformance:
    """Test performance characteristics."""
    
    def test_preview_generation_performance(self):
        """Test preview generation performance."""
        cards = generate_test_cards(count=100)
        params = create_test_preview_params()
        
        import time
        start_time = time.time()
        
        # Generate preview
        html = create_page_preview_html_unified(cards, 0, params)
        
        duration = time.time() - start_time
        
        # Should complete within 500ms
        assert duration < 0.5
        assert len(html) > 0
    
    def test_cache_performance(self):
        """Test cache performance."""
        cache = get_preview_cache()
        
        # Test cache hit performance
        cache.set("test_key", "test_value")
        
        import time
        start_time = time.time()
        
        # Perform 1000 cache hits
        for _ in range(1000):
            value = cache.get("test_key")
            assert value == "test_value"
        
        duration = time.time() - start_time
        
        # Should complete within 100ms
        assert duration < 0.1
    
    def test_memory_usage(self):
        """Test memory usage characteristics."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Generate large dataset
        cards = generate_test_cards(count=1000)
        
        # Generate multiple previews
        for page in range(10):
            html = create_page_preview_html_unified(cards, page, create_test_preview_params())
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50 * 1024 * 1024
```

## Golden Testing

### Preview-Export Consistency

```python
class TestGoldenConsistency:
    """Test consistency between preview and export."""
    
    def test_preview_export_consistency(self, test_data_dir):
        """Test that preview and export generate consistent output."""
        # Load test cards
        cards = load_test_cards(test_data_dir / "sample_cards.json")
        params = create_test_preview_params()
        
        # Generate preview HTML
        preview_html = create_page_preview_html_unified(cards, 0, params)
        
        # Generate export PDF (extract text content)
        from services.export import export_cards_to_pdf
        pdf_result = export_cards_to_pdf(cards, params)
        pdf_text = extract_text_from_pdf(pdf_result.file_path)
        
        # Verify consistency
        assert_content_consistency(preview_html, pdf_text)
    
    def test_typography_consistency(self):
        """Test typography consistency across formats."""
        cards = generate_test_cards(count=4)
        params = create_test_preview_params()
        
        # Generate in different formats
        html = create_page_preview_html_unified(cards, 0, params)
        pdf_result = export_cards_to_pdf(cards, params)
        pptx_result = export_cards_to_pptx(cards, params)
        
        # Extract typography information
        html_fonts = extract_font_info_from_html(html)
        pdf_fonts = extract_font_info_from_pdf(pdf_result.file_path)
        pptx_fonts = extract_font_info_from_pptx(pptx_result.file_path)
        
        # Verify consistency
        assert html_fonts['hanzi_font'] == pdf_fonts['hanzi_font']
        assert html_fonts['hanzi_font'] == pptx_fonts['hanzi_font']
```

## Test Utilities

### Test Data Generation

```python
def generate_test_cards(count: int = 10) -> List[Dict[str, str]]:
    """Generate test card data."""
    cards = []
    test_data = [
        ("你好", "nǐ hǎo", "hello"),
        ("世界", "shì jiè", "world"),
        ("中国", "zhōng guó", "China"),
        ("学习", "xué xí", "study"),
        ("朋友", "péng yǒu", "friend"),
    ]
    
    for i in range(count):
        hanzi, pinyin, english = test_data[i % len(test_data)]
        cards.append({
            "hanzi": f"{hanzi}{i}" if i >= len(test_data) else hanzi,
            "pinyin": pinyin,
            "english": english
        })
    
    return cards

def create_test_preview_params() -> PreviewParams:
    """Create test preview parameters."""
    return PreviewParams(
        layout=LayoutParams(rows=3, cols=3, card_size=5.5, gap_cm=0.5, margin_cm=1.0),
        typography=TypographyParams(hanzi_font_size_pt=48, pinyin_font_size_pt=18, english_font_size_pt=14),
        visual=VisualParams(hanzi_font="SimHei", background_color="#FFFFFF")
    )
```

### Test Assertions

```python
def assert_content_consistency(html: str, pdf_text: str):
    """Assert content consistency between HTML and PDF."""
    # Extract text content from HTML
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    html_text = soup.get_text()
    
    # Normalize whitespace
    html_words = set(html_text.split())
    pdf_words = set(pdf_text.split())
    
    # Check that key content is present in both
    common_words = html_words.intersection(pdf_words)
    assert len(common_words) > 0
    
    # Check for Chinese characters
    chinese_chars_html = [char for char in html_text if '\u4e00' <= char <= '\u9fff']
    chinese_chars_pdf = [char for char in pdf_text if '\u4e00' <= char <= '\u9fff']
    
    assert len(chinese_chars_html) > 0
    assert len(chinese_chars_pdf) > 0
    assert set(chinese_chars_html) == set(chinese_chars_pdf)
```

## Running Tests

### Test Execution

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run performance tests
pytest tests/e2e/test_performance.py -v

# Run with specific markers
pytest -m "not slow"
pytest -m "integration"
```

### Continuous Integration

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

---

**Document Version**: 1.0  
**Last Updated**: August 2024  
**Next Review**: November 2024
