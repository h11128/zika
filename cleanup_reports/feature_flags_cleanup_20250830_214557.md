# Feature Flags Documentation

**Generated**: 2025-08-30 21:45:57

## Removed Flags

The following flags were removed as they represent completed, stable features:

- `preview_dataclasses_v2` - always enabled
- `ui_adapter` - always enabled
- `adapted_inputs` - always enabled
- `adapted_preview` - always enabled
- `adapted_editor` - always enabled
- `adapted_export` - always enabled
- `adapted_sidebar` - always enabled
- `adapted_options` - always enabled
- `new_preview_pipeline` - always enabled
- `state_service` - always enabled
- `cache_v2` - always enabled
- `shared_render_core` - always enabled
- `unified_sections` - always enabled
- `clean_ui_components` - always disabled

## Remaining Flags

The following flags remain active for operational or development purposes:

- `telemetry_enabled` - Active operational/development flag
- `persistence` - Active operational/development flag
- `storage_debug_panel` - Active operational/development flag
- `telemetry_debug` - Active operational/development flag
- `debug_panel` - Active operational/development flag
- `ENABLE_DIGEST_DEBUG` - Active operational/development flag

## Usage Guidelines

- **Development flags** (`debug_panel`, `storage_debug_panel`) - For debugging and development
- **Operational flags** (`persistence`, `telemetry_enabled`) - For runtime configuration
- **Future flags** - For gradual rollout of new features
