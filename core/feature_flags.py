"""
Feature flag system for the Chinese Character Learning Cards application.
Supports environment variables, configuration files, remote service, and testing overrides.
"""

import os
import json
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FeatureFlagConfig:
    """Configuration for feature flag evaluation."""
    # Cache TTL for remote service (seconds)
    remote_cache_ttl: int = 300  # 5 minutes
    # Configuration file path
    config_file_path: Optional[str] = None
    # Remote service URL (if any)
    remote_service_url: Optional[str] = None
    # Environment variable prefix
    env_prefix: str = "ZIKA_FEATURE_"


@dataclass
class FeatureFlagState:
    """Internal state for feature flag system."""
    # Cached flags from all sources
    cached_flags: Dict[str, Any] = field(default_factory=dict)
    # Last cache update time
    last_cache_update: float = 0
    # Testing overrides
    test_overrides: Dict[str, Any] = field(default_factory=dict)
    # Configuration
    config: FeatureFlagConfig = field(default_factory=FeatureFlagConfig)


# Global state instance
_flag_state = FeatureFlagState()


def configure_feature_flags(
    config_file_path: Optional[str] = None,
    remote_service_url: Optional[str] = None,
    remote_cache_ttl: int = 300,
    env_prefix: str = "ZIKA_FEATURE_"
) -> None:
    """Configure the feature flag system."""
    global _flag_state
    _flag_state.config = FeatureFlagConfig(
        config_file_path=config_file_path,
        remote_service_url=remote_service_url,
        remote_cache_ttl=remote_cache_ttl,
        env_prefix=env_prefix
    )
    # Force cache refresh on next evaluation
    _flag_state.last_cache_update = 0


def get_feature_flag(flag_name: str, default: Any = False) -> Any:
    """
    Get feature flag value with priority: test overrides > env > config file > remote > default.
    
    Args:
        flag_name: Name of the feature flag
        default: Default value if flag not found
        
    Returns:
        Feature flag value
    """
    # Ensure cache is fresh
    _refresh_cache_if_needed()
    
    # Priority 1: Test overrides
    if flag_name in _flag_state.test_overrides:
        return _flag_state.test_overrides[flag_name]
    
    # Priority 2: Environment variables
    env_key = f"{_flag_state.config.env_prefix}{flag_name.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return _parse_env_value(env_value)
    
    # Priority 3-4: Cached flags (config file + remote)
    if flag_name in _flag_state.cached_flags:
        return _flag_state.cached_flags[flag_name]
    
    # Priority 5: Default
    return default


def set_test_override(flag_name: str, value: Any) -> None:
    """Set a test override for a feature flag."""
    _flag_state.test_overrides[flag_name] = value


def clear_test_override(flag_name: str) -> None:
    """Clear a test override for a feature flag."""
    _flag_state.test_overrides.pop(flag_name, None)


def clear_all_test_overrides() -> None:
    """Clear all test overrides."""
    _flag_state.test_overrides.clear()


class FeatureFlagOverride:
    """Context manager for temporary feature flag overrides in tests."""
    
    def __init__(self, **flags):
        self.flags = flags
        self.original_values = {}
    
    def __enter__(self):
        # Store original values
        for flag_name in self.flags:
            if flag_name in _flag_state.test_overrides:
                self.original_values[flag_name] = _flag_state.test_overrides[flag_name]
            else:
                self.original_values[flag_name] = None
        
        # Set new values
        for flag_name, value in self.flags.items():
            set_test_override(flag_name, value)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original values
        for flag_name, original_value in self.original_values.items():
            if original_value is None:
                clear_test_override(flag_name)
            else:
                set_test_override(flag_name, original_value)


def invalidate_cache() -> None:
    """Force cache invalidation on next flag evaluation."""
    global _flag_state
    _flag_state.last_cache_update = 0
    _flag_state.cached_flags.clear()


def _refresh_cache_if_needed() -> None:
    """Refresh cache if TTL expired."""
    current_time = time.time()
    if (current_time - _flag_state.last_cache_update) > _flag_state.config.remote_cache_ttl:
        _refresh_cache()


def _refresh_cache() -> None:
    """Refresh cache from config file and remote service."""
    new_flags = {}
    
    # Load from config file
    if _flag_state.config.config_file_path:
        config_flags = _load_config_file(_flag_state.config.config_file_path)
        new_flags.update(config_flags)
    
    # Load from remote service (with exponential backoff on failures)
    if _flag_state.config.remote_service_url:
        remote_flags = _load_remote_flags(_flag_state.config.remote_service_url)
        new_flags.update(remote_flags)
    
    # Update cache
    _flag_state.cached_flags = new_flags
    _flag_state.last_cache_update = time.time()


def _load_config_file(file_path: str) -> Dict[str, Any]:
    """Load feature flags from configuration file."""
    try:
        path = Path(file_path)
        if path.exists() and path.suffix.lower() == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data.get('feature_flags', {})
        return {}
    except Exception:
        # Silently fail and return empty dict
        return {}


def _load_remote_flags(service_url: str) -> Dict[str, Any]:
    """Load feature flags from remote service with exponential backoff."""
    try:
        # This is a placeholder - implement actual HTTP client if needed
        # For now, return empty dict to avoid external dependencies
        return {}
    except Exception:
        # Silently fail and return empty dict
        return {}


def _parse_env_value(value: str) -> Union[bool, int, float, str]:
    """Parse environment variable value to appropriate type."""
    value = value.strip()
    
    # Boolean values
    if value.lower() in ('true', '1', 'yes', 'on'):
        return True
    if value.lower() in ('false', '0', 'no', 'off'):
        return False
    
    # Numeric values
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    
    # String value
    return value


# Default feature flags for the UI refactor
DEFAULT_FLAGS = {
    'new_preview_pipeline': False,
    'ui_adapter': False,
    'state_service': False,
    'cache_v2': False,
    'persistence': False,
    'debug_panel': False,
}


def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature is enabled (convenience function for boolean flags)."""
    return bool(get_feature_flag(flag_name, DEFAULT_FLAGS.get(flag_name, False)))


# Convenience functions for specific features
def use_new_preview_pipeline() -> bool:
    """Check if new preview pipeline should be used."""
    return is_feature_enabled('new_preview_pipeline')


def use_ui_adapter() -> bool:
    """Check if UI adapter should be used."""
    return is_feature_enabled('ui_adapter')


def use_state_service() -> bool:
    """Check if state service should be used."""
    return is_feature_enabled('state_service')


def use_cache_v2() -> bool:
    """Check if cache v2 should be used."""
    return is_feature_enabled('cache_v2')


def use_persistence() -> bool:
    """Check if persistence should be used."""
    return is_feature_enabled('persistence')


def show_debug_panel() -> bool:
    """Check if debug panel should be shown."""
    return is_feature_enabled('debug_panel')
