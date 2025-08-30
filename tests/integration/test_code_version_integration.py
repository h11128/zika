"""
Integration tests for code version management in cache keys.
Tests that code version changes properly invalidate caches.
"""

import os
import pytest
from unittest.mock import patch

from core.version import get_code_version, clear_version_cache
from services.cache_v2 import compute_cache_key
# Import from the main ui.state module (not the package)
import importlib.util
import os
spec = importlib.util.spec_from_file_location("ui_state_module", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui", "state.py"))
ui_state_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ui_state_module)


class TestCodeVersionIntegration:
    """Test code version integration with caching systems."""
    
    def setup_method(self):
        """Clear version cache before each test."""
        clear_version_cache()
    
    def test_cache_key_includes_code_version(self):
        """Test that cache keys include code version."""
        test_data = {'param1': 'value1', 'param2': 42}
        schema_version = 'v1.0.0'
        
        # Get cache key
        cache_key = compute_cache_key(test_data, schema_version)
        
        # Verify it's a valid cache key
        assert isinstance(cache_key, str)
        assert len(cache_key) == 16  # Truncated SHA256
        
        # The cache key should be deterministic for same inputs
        cache_key2 = compute_cache_key(test_data, schema_version)
        assert cache_key == cache_key2
    
    def test_different_code_versions_produce_different_cache_keys(self):
        """Test that different code versions produce different cache keys."""
        test_data = {'param1': 'value1', 'param2': 42}
        schema_version = 'v1.0.0'
        
        # Get cache key with first version
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.0'}, clear=True):
            clear_version_cache()
            cache_key1 = compute_cache_key(test_data, schema_version)
        
        # Get cache key with different version
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.1'}, clear=True):
            clear_version_cache()
            cache_key2 = compute_cache_key(test_data, schema_version)
        
        # Keys should be different
        assert cache_key1 != cache_key2
    
    def test_export_key_includes_code_version(self):
        """Test that export keys include code version."""
        export_params = {'format': 'pdf', 'quality': 'high'}
        cards_count = 10
        
        # Get export key
        export_key = ui_state_module.compute_export_key(export_params, cards_count)

        # Verify it's a valid export key
        assert isinstance(export_key, str)
        assert len(export_key) == 16  # Truncated SHA256
        
        # The export key should be deterministic for same inputs
        export_key2 = ui_state_module.compute_export_key(export_params, cards_count)
        assert export_key == export_key2
    
    def test_different_code_versions_produce_different_export_keys(self):
        """Test that different code versions produce different export keys."""
        export_params = {'format': 'pdf', 'quality': 'high'}
        cards_count = 10
        
        # Get export key with first version
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.0'}, clear=True):
            clear_version_cache()
            export_key1 = ui_state_module.compute_export_key(export_params, cards_count)

        # Get export key with different version
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.1'}, clear=True):
            clear_version_cache()
            export_key2 = ui_state_module.compute_export_key(export_params, cards_count)
        
        # Keys should be different
        assert export_key1 != export_key2
    
    def test_code_version_format_in_different_environments(self):
        """Test code version format in different environments."""
        # Test development environment
        with patch.dict(os.environ, {}, clear=True):
            clear_version_cache()
            dev_version = get_code_version()
            assert dev_version.startswith('dev-')
            assert 'nogit' in dev_version or len(dev_version.split('-')) >= 3
        
        # Test CI environment
        with patch.dict(os.environ, {'CI': 'true', 'BUILD_NUMBER': '123'}, clear=True):
            with patch('core.version._get_git_sha', return_value='abc1234'):
                clear_version_cache()
                ci_version = get_code_version()
                assert ci_version == 'ci-123-abc1234'
        
        # Test production environment
        with patch.dict(os.environ, {'ENVIRONMENT': 'production', 'VERSION': '2.1.0'}, clear=True):
            clear_version_cache()
            prod_version = get_code_version()
            assert prod_version == 'v2.1.0'
    
    def test_cache_invalidation_on_code_version_change(self):
        """Test that cache is effectively invalidated when code version changes."""
        test_data = {'param1': 'value1'}
        schema_version = 'v1.0.0'
        
        # Simulate cache with version 1.0.0
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.0'}, clear=True):
            clear_version_cache()
            old_cache_key = compute_cache_key(test_data, schema_version)
        
        # Simulate code update to version 1.0.1
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.0.1'}, clear=True):
            clear_version_cache()
            new_cache_key = compute_cache_key(test_data, schema_version)
        
        # Cache keys should be different, effectively invalidating old cache
        assert old_cache_key != new_cache_key
        
        # This simulates what would happen in practice:
        # 1. Old cache entries would have old_cache_key
        # 2. New requests would generate new_cache_key
        # 3. Cache miss would occur, forcing regeneration
    
    def test_version_determinism_across_calls(self):
        """Test that version is deterministic across multiple calls."""
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'test-version'}, clear=True):
            clear_version_cache()
            
            # Multiple calls should return same version
            version1 = get_code_version()
            version2 = get_code_version()
            version3 = get_code_version()
            
            assert version1 == version2 == version3 == 'test-version'
    
    def test_cache_key_reproducibility(self):
        """Test that cache keys are reproducible with same inputs and version."""
        test_data = {'param1': 'value1', 'nested': {'key': 'value'}}
        schema_version = 'v1.0.0'
        
        with patch.dict(os.environ, {'ZIKA_CODE_VERSION': 'v1.2.3'}, clear=True):
            clear_version_cache()
            
            # Generate multiple cache keys with same inputs
            keys = [compute_cache_key(test_data, schema_version) for _ in range(5)]
            
            # All keys should be identical
            assert all(key == keys[0] for key in keys)
            assert len(set(keys)) == 1  # Only one unique key
