# Feature Flags System Guide

## Overview

The Feature Flags system (`core/feature_flags.py`) provides a flexible, hierarchical configuration system for controlling feature availability, enabling gradual rollouts, A/B testing, and safe deployment practices.

## Architecture

### Core Components

1. **Feature Flag Evaluation**: Hierarchical flag resolution
2. **Configuration Sources**: Environment, config files, remote services
3. **Rollout Management**: Gradual feature deployment
4. **Testing Overrides**: Test-specific configurations
5. **Monitoring Integration**: Flag usage tracking

### Priority Hierarchy

The system evaluates flags in the following priority order:

1. **Test Overrides** (highest priority)
2. **Environment Variables**
3. **Configuration Files**
4. **Remote Services**
5. **Default Values** (lowest priority)

## Configuration Sources

### Environment Variables

```bash
# Enable/disable features via environment
export FEATURE_PERSISTENCE=true
export FEATURE_DEBUG_PANEL=false
export FEATURE_TELEMETRY_ENABLED=true
```

### Configuration Files

```json
{
  "feature_flags": {
    "persistence": true,
    "debug_panel": false,
    "telemetry_enabled": true,
    "storage_debug_panel": false
  }
}
```

### Default Configuration

```python
DEFAULT_FLAGS = {
    # Operational flags
    'persistence': True,
    'telemetry_enabled': True,
    'telemetry_debug': False,
    
    # Development flags
    'debug_panel': False,
    'storage_debug_panel': False,
    'ENABLE_DIGEST_DEBUG': False,
    
    # Future feature flags
    'new_feature_x': False,
    'experimental_ui': False,
}
```

## Usage Examples

### Basic Flag Evaluation

```python
from core.feature_flags import get_feature_flag

# Simple flag check
if get_feature_flag('persistence', True):
    # Feature is enabled
    save_to_storage(data)

# With default value
debug_enabled = get_feature_flag('debug_panel', False)
if debug_enabled:
    show_debug_info()
```

### Conditional Feature Loading

```python
# Conditional imports based on flags
if get_feature_flag('advanced_analytics', False):
    from services.advanced_analytics import AdvancedAnalytics
    analytics = AdvancedAnalytics()
else:
    analytics = None

# Feature-gated functionality
def process_data(data):
    if get_feature_flag('new_processing_algorithm', False):
        return new_algorithm(data)
    else:
        return legacy_algorithm(data)
```

### Testing Overrides

```python
import pytest
from core.feature_flags import override_flag, clear_overrides

def test_with_feature_enabled():
    """Test behavior with feature enabled."""
    with override_flag('new_feature', True):
        result = feature_dependent_function()
        assert result.uses_new_feature is True

def test_with_feature_disabled():
    """Test behavior with feature disabled."""
    with override_flag('new_feature', False):
        result = feature_dependent_function()
        assert result.uses_legacy_behavior is True

@pytest.fixture(autouse=True)
def clear_flag_overrides():
    """Clear flag overrides after each test."""
    yield
    clear_overrides()
```

## Flag Categories

### Operational Flags

These flags control runtime behavior and can be toggled in production:

- **`persistence`**: Enable/disable browser storage
- **`telemetry_enabled`**: Enable/disable telemetry collection
- **`telemetry_debug`**: Enable detailed telemetry logging

### Development Flags

These flags are primarily for development and debugging:

- **`debug_panel`**: Show debug information panel
- **`storage_debug_panel`**: Show storage debugging information
- **`ENABLE_DIGEST_DEBUG`**: Enable digest computation debugging

### Feature Rollout Flags

These flags control gradual rollout of new features:

- **`new_feature_x`**: Enable new experimental feature
- **`experimental_ui`**: Enable experimental UI components
- **`beta_export_formats`**: Enable beta export formats

## Rollout Management

### Gradual Rollout

```python
from services.rollout import create_feature_rollout, RolloutStrategy

# Create gradual rollout
rollout = create_feature_rollout(
    feature_name='new_ui_component',
    strategy=RolloutStrategy.GRADUAL,
    initial_percentage=5.0,
    increment_percentage=10.0,
    target_percentage=100.0
)

# Start rollout
start_feature_rollout('new_ui_component')

# Check if enabled for user
if is_feature_enabled_for_user('new_ui_component', user_id):
    render_new_component()
else:
    render_legacy_component()
```

### A/B Testing

```python
from services.rollout import get_ab_test_manager

# Create A/B test
ab_manager = get_ab_test_manager()
ab_manager.create_ab_test(
    experiment_name='ui_redesign_test',
    feature_name='new_ui_design',
    control_percentage=50.0,
    treatment_percentage=50.0,
    duration_days=14
)

# Use in code
if is_feature_enabled_for_user('new_ui_design', user_id):
    # Treatment group - new UI
    render_new_ui()
else:
    # Control group - current UI
    render_current_ui()
```

### Canary Deployment

```python
# Create canary deployment
rollout = create_feature_rollout(
    feature_name='performance_optimization',
    strategy=RolloutStrategy.CANARY,
    canary_percentage=1.0,
    max_error_rate=2.0,
    max_latency_ms=1000.0
)

# Automatic rollback on issues
# System monitors error rates and performance
# Rolls back automatically if thresholds exceeded
```

## Advanced Features

### Dynamic Flag Updates

```python
from core.feature_flags import update_flag_config

# Update flags at runtime (for remote configuration)
new_config = {
    'new_feature': True,
    'experimental_mode': False
}
update_flag_config(new_config)
```

### Flag Dependencies

```python
def get_dependent_flag(flag_name: str, dependencies: List[str]) -> bool:
    """Get flag value with dependency checking."""
    # Check if all dependencies are enabled
    for dep in dependencies:
        if not get_feature_flag(dep, False):
            return False
    
    return get_feature_flag(flag_name, False)

# Usage
if get_dependent_flag('advanced_feature', ['persistence', 'telemetry_enabled']):
    enable_advanced_feature()
```

### Flag Monitoring

```python
from core.feature_flags import track_flag_usage

def feature_function():
    """Function that uses feature flags."""
    if get_feature_flag('new_algorithm', False):
        track_flag_usage('new_algorithm', True)
        return new_algorithm()
    else:
        track_flag_usage('new_algorithm', False)
        return legacy_algorithm()
```

## Best Practices

### Flag Naming

1. **Use Descriptive Names**: `new_ui_component` not `flag1`
2. **Include Context**: `export_pdf_v2` not `pdf_export`
3. **Use Consistent Prefixes**: `debug_*` for debug flags
4. **Avoid Negatives**: `enable_feature` not `disable_feature`

### Flag Lifecycle

1. **Start with False**: New flags should default to disabled
2. **Gradual Rollout**: Use percentage-based rollouts for risky features
3. **Monitor Closely**: Track performance and error rates
4. **Clean Up**: Remove flags once features are stable

### Testing Strategy

1. **Test Both Paths**: Test with flag enabled and disabled
2. **Use Overrides**: Use test overrides for deterministic testing
3. **Integration Tests**: Test flag interactions
4. **Performance Tests**: Measure flag evaluation overhead

### Security Considerations

1. **Validate Inputs**: Sanitize flag values from external sources
2. **Audit Changes**: Log all flag configuration changes
3. **Access Control**: Restrict who can modify production flags
4. **Rollback Plan**: Have procedures for emergency flag changes

## Monitoring and Observability

### Flag Usage Tracking

```python
# Track which flags are being evaluated
from services.telemetry import record_flag_evaluation

def get_feature_flag_with_tracking(flag_name: str, default: bool) -> bool:
    """Get feature flag with usage tracking."""
    value = get_feature_flag(flag_name, default)
    record_flag_evaluation(flag_name, value, default)
    return value
```

### Performance Monitoring

```python
# Monitor flag evaluation performance
import time
from services.telemetry import record_performance_event

def timed_flag_evaluation(flag_name: str, default: bool) -> bool:
    """Evaluate flag with performance tracking."""
    start_time = time.time()
    value = get_feature_flag(flag_name, default)
    duration = time.time() - start_time
    
    record_performance_event('flag_evaluation', {
        'flag_name': flag_name,
        'duration_ms': duration * 1000,
        'value': value
    })
    
    return value
```

### Error Handling

```python
def safe_get_feature_flag(flag_name: str, default: bool) -> bool:
    """Get feature flag with error handling."""
    try:
        return get_feature_flag(flag_name, default)
    except Exception as e:
        # Log error but don't break functionality
        logging.error(f"Error evaluating flag {flag_name}: {e}")
        return default
```

## Migration and Cleanup

### Flag Removal Process

1. **Deprecation Warning**: Add warnings when flag is always True/False
2. **Code Cleanup**: Remove conditional logic
3. **Configuration Cleanup**: Remove from default configs
4. **Documentation Update**: Update feature documentation

### Automated Cleanup

```python
# Script to identify unused flags
def find_unused_flags():
    """Find flags that are no longer referenced in code."""
    defined_flags = set(DEFAULT_FLAGS.keys())
    used_flags = set()
    
    # Scan codebase for flag usage
    for file_path in scan_python_files():
        used_flags.update(extract_flag_names(file_path))
    
    unused_flags = defined_flags - used_flags
    return unused_flags
```

## Troubleshooting

### Common Issues

1. **Flag Not Taking Effect**: Check priority hierarchy
2. **Inconsistent Behavior**: Verify flag evaluation timing
3. **Performance Issues**: Monitor flag evaluation frequency
4. **Test Failures**: Ensure proper test isolation

### Debugging Tools

```python
# Debug flag resolution
from core.feature_flags import debug_flag_resolution

debug_info = debug_flag_resolution('problematic_flag')
print(f"Flag sources: {debug_info['sources']}")
print(f"Final value: {debug_info['value']}")
print(f"Resolution path: {debug_info['path']}")
```

---

**Document Version**: 1.0  
**Last Updated**: August 2024  
**Next Review**: November 2024
