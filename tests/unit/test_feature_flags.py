"""
Unit tests for the feature flag system.
Tests flag evaluation, priority hierarchy, and context managers.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import patch, MagicMock

from core.feature_flags import (
    get_feature_flag, set_test_override, clear_test_override, clear_all_test_overrides,
    FeatureFlagOverride, configure_feature_flags, invalidate_cache,
    is_feature_enabled, use_new_preview_pipeline, use_ui_adapter, use_state_service,
    _parse_env_value, _load_config_file
)


class TestFeatureFlagEvaluation:
    """Test feature flag evaluation and priority."""
    
    def setup_method(self):
        """Setup test environment."""
        clear_all_test_overrides()
        invalidate_cache()
    
    def test_get_feature_flag_default(self):
        """Test getting feature flag with default value."""
        result = get_feature_flag('nonexistent_flag', 'default_value')
        assert result == 'default_value'
    
    def test_get_feature_flag_boolean_default(self):
        """Test getting boolean feature flag with default."""
        result = get_feature_flag('nonexistent_flag', False)
        assert result is False
        
        result = get_feature_flag('nonexistent_flag', True)
        assert result is True
    
    def test_test_override_priority(self):
        """Test that test overrides have highest priority."""
        set_test_override('test_flag', 'override_value')
        
        with patch.dict(os.environ, {'ZIKA_FEATURE_TEST_FLAG': 'env_value'}):
            result = get_feature_flag('test_flag', 'default_value')
            assert result == 'override_value'
    
    def test_environment_variable_priority(self):
        """Test that environment variables have second priority."""
        with patch.dict(os.environ, {'ZIKA_FEATURE_TEST_FLAG': 'env_value'}):
            result = get_feature_flag('test_flag', 'default_value')
            assert result == 'env_value'
    
    def test_clear_test_override(self):
        """Test clearing test overrides."""
        set_test_override('test_flag', 'override_value')
        assert get_feature_flag('test_flag', 'default') == 'override_value'
        
        clear_test_override('test_flag')
        assert get_feature_flag('test_flag', 'default') == 'default'
    
    def test_clear_all_test_overrides(self):
        """Test clearing all test overrides."""
        set_test_override('flag1', 'value1')
        set_test_override('flag2', 'value2')
        
        clear_all_test_overrides()
        
        assert get_feature_flag('flag1', 'default') == 'default'
        assert get_feature_flag('flag2', 'default') == 'default'


class TestFeatureFlagOverrideContext:
    """Test FeatureFlagOverride context manager."""
    
    def setup_method(self):
        """Setup test environment."""
        clear_all_test_overrides()
    
    def test_context_manager_sets_flags(self):
        """Test that context manager sets flags correctly."""
        with FeatureFlagOverride(test_flag='context_value'):
            result = get_feature_flag('test_flag', 'default')
            assert result == 'context_value'
    
    def test_context_manager_restores_flags(self):
        """Test that context manager restores original values."""
        set_test_override('test_flag', 'original_value')
        
        with FeatureFlagOverride(test_flag='context_value'):
            assert get_feature_flag('test_flag', 'default') == 'context_value'
        
        # Should restore original value
        assert get_feature_flag('test_flag', 'default') == 'original_value'
    
    def test_context_manager_multiple_flags(self):
        """Test context manager with multiple flags."""
        with FeatureFlagOverride(flag1='value1', flag2='value2'):
            assert get_feature_flag('flag1', 'default') == 'value1'
            assert get_feature_flag('flag2', 'default') == 'value2'
        
        # Should restore defaults
        assert get_feature_flag('flag1', 'default') == 'default'
        assert get_feature_flag('flag2', 'default') == 'default'
    
    def test_context_manager_nested(self):
        """Test nested context managers."""
        with FeatureFlagOverride(test_flag='outer_value'):
            assert get_feature_flag('test_flag', 'default') == 'outer_value'
            
            with FeatureFlagOverride(test_flag='inner_value'):
                assert get_feature_flag('test_flag', 'default') == 'inner_value'
            
            # Should restore outer value
            assert get_feature_flag('test_flag', 'default') == 'outer_value'
        
        # Should restore default
        assert get_feature_flag('test_flag', 'default') == 'default'


class TestEnvironmentVariableParsing:
    """Test environment variable value parsing."""
    
    def test_parse_boolean_true_values(self):
        """Test parsing boolean true values."""
        true_values = ['true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON']
        
        for value in true_values:
            result = _parse_env_value(value)
            assert result is True, f"Failed for value: {value}"
    
    def test_parse_boolean_false_values(self):
        """Test parsing boolean false values."""
        false_values = ['false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF']
        
        for value in false_values:
            result = _parse_env_value(value)
            assert result is False, f"Failed for value: {value}"
    
    def test_parse_integer_values(self):
        """Test parsing integer values."""
        assert _parse_env_value('42') == 42
        assert _parse_env_value('-10') == -10
        assert _parse_env_value('0') == 0
    
    def test_parse_float_values(self):
        """Test parsing float values."""
        assert _parse_env_value('3.14') == 3.14
        assert _parse_env_value('-2.5') == -2.5
        assert _parse_env_value('0.0') == 0.0
    
    def test_parse_string_values(self):
        """Test parsing string values."""
        assert _parse_env_value('hello') == 'hello'
        assert _parse_env_value('complex_string_123') == 'complex_string_123'
        assert _parse_env_value('') == ''
    
    def test_parse_whitespace_handling(self):
        """Test whitespace handling in parsing."""
        assert _parse_env_value('  true  ') is True
        assert _parse_env_value('  42  ') == 42
        assert _parse_env_value('  hello  ') == 'hello'


class TestConfigFileLoading:
    """Test configuration file loading."""
    
    def test_load_valid_config_file(self):
        """Test loading valid JSON config file."""
        config_data = {
            'feature_flags': {
                'test_flag': True,
                'another_flag': 'value'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            result = _load_config_file(temp_path)
            assert result == config_data['feature_flags']
        finally:
            os.unlink(temp_path)
    
    def test_load_nonexistent_config_file(self):
        """Test loading nonexistent config file."""
        result = _load_config_file('/nonexistent/path.json')
        assert result == {}
    
    def test_load_invalid_json_config_file(self):
        """Test loading invalid JSON config file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('invalid json content')
            temp_path = f.name
        
        try:
            result = _load_config_file(temp_path)
            assert result == {}
        finally:
            os.unlink(temp_path)
    
    def test_load_config_file_no_feature_flags(self):
        """Test loading config file without feature_flags section."""
        config_data = {'other_section': {'key': 'value'}}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            result = _load_config_file(temp_path)
            assert result == {}
        finally:
            os.unlink(temp_path)


class TestConvenienceFunctions:
    """Test convenience functions for specific features."""
    
    def setup_method(self):
        """Setup test environment."""
        clear_all_test_overrides()
    
    def test_is_feature_enabled_true(self):
        """Test is_feature_enabled with true value."""
        set_test_override('test_flag', True)
        assert is_feature_enabled('test_flag') is True
    
    def test_is_feature_enabled_false(self):
        """Test is_feature_enabled with false value."""
        set_test_override('test_flag', False)
        assert is_feature_enabled('test_flag') is False
    
    def test_is_feature_enabled_truthy_string(self):
        """Test is_feature_enabled with truthy string."""
        set_test_override('test_flag', 'enabled')
        assert is_feature_enabled('test_flag') is True
    
    def test_is_feature_enabled_falsy_string(self):
        """Test is_feature_enabled with falsy string."""
        set_test_override('test_flag', '')
        assert is_feature_enabled('test_flag') is False
    
    def test_use_new_preview_pipeline(self):
        """Test use_new_preview_pipeline convenience function."""
        set_test_override('new_preview_pipeline', True)
        assert use_new_preview_pipeline() is True
        
        set_test_override('new_preview_pipeline', False)
        assert use_new_preview_pipeline() is False
    
    def test_use_ui_adapter(self):
        """Test use_ui_adapter convenience function."""
        set_test_override('ui_adapter', True)
        assert use_ui_adapter() is True
        
        set_test_override('ui_adapter', False)
        assert use_ui_adapter() is False
    
    def test_use_state_service(self):
        """Test use_state_service convenience function."""
        set_test_override('state_service', True)
        assert use_state_service() is True
        
        set_test_override('state_service', False)
        assert use_state_service() is False


class TestConfiguration:
    """Test feature flag configuration."""
    
    def test_configure_feature_flags(self):
        """Test configuring feature flags."""
        configure_feature_flags(
            config_file_path='/test/path.json',
            remote_service_url='http://test.com',
            remote_cache_ttl=600,
            env_prefix='TEST_'
        )
        
        # Configuration should affect environment variable parsing
        with patch.dict(os.environ, {'TEST_FLAG': 'true'}):
            result = get_feature_flag('flag', False)
            assert result is True
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # This is mainly to ensure the function doesn't crash
        invalidate_cache()
        
        # Should be able to call multiple times
        invalidate_cache()
        invalidate_cache()
