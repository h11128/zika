"""
Comprehensive integration tests for all architectural fixes.

Tests the complete system with all new features enabled.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from core.feature_flags import get_feature_flag, set_test_override


class TestFeatureFlagActivation:
    """Test that all critical feature flags are enabled."""
    
    def test_adapter_flags_enabled(self):
        """Test that all adapter flags are enabled."""
        adapter_flags = [
            'ui_adapter',
            'adapted_inputs',
            'adapted_options', 
            'adapted_preview',
            'adapted_editor',
            'adapted_export',
            'adapted_sidebar'
        ]
        
        for flag in adapter_flags:
            assert get_feature_flag(flag, False), f"Adapter flag {flag} should be enabled"
    
    def test_form_and_debouncing_enabled(self):
        """Test that form semantics and debouncing are enabled."""
        assert get_feature_flag('form_semantics', False), "Form semantics should be enabled"
        assert get_feature_flag('debouncing', False), "Debouncing should be enabled"
    
    def test_shared_render_core_enabled(self):
        """Test that shared render core is enabled."""
        assert get_feature_flag('shared_render_core', False), "Shared render core should be enabled"


class TestUIAdapterIntegration:
    """Test UI adapter integration."""
    
    def test_adapter_import_works(self):
        """Test that adapter can be imported and instantiated."""
        from ui.adapters.streamlit_adapter import StreamlitAdapter
        from ui.ports import get_ui_adapter
        
        # Test direct import
        adapter = StreamlitAdapter()
        assert adapter is not None
        
        # Test factory function
        adapter2 = get_ui_adapter()
        assert adapter2 is not None
        assert isinstance(adapter2, StreamlitAdapter)
    
    def test_adapter_has_all_required_methods(self):
        """Test that adapter implements all required methods."""
        from ui.adapters.streamlit_adapter import StreamlitAdapter
        
        adapter = StreamlitAdapter()
        
        # Test inputs adapter
        assert hasattr(adapter.inputs, 'text_input')
        assert hasattr(adapter.inputs, 'checkbox')
        assert hasattr(adapter.inputs, 'slider')
        assert hasattr(adapter.inputs, 'selectbox')
        assert hasattr(adapter.inputs, 'radio')
        assert hasattr(adapter.inputs, 'button')
        
        # Test layout adapter
        assert hasattr(adapter.layout, 'columns')
        assert hasattr(adapter.layout, 'container')
        assert hasattr(adapter.layout, 'expander')
        
        # Test notification methods
        assert hasattr(adapter, 'notify')
        assert hasattr(adapter, 'header')
        assert hasattr(adapter, 'spinner')


class TestStateServiceModularization:
    """Test state service modularization."""
    
    def test_state_modules_import(self):
        """Test that all state modules can be imported."""
        from ui.state import (
            get_state_store, get_state_service,
            get_state_rules, validate_state_change,
            get_state_digest, compute_state_digest,
            get_invalidation_service, invalidate_preview_cache,
            get_navigation_state
        )
        
        # Test that all functions are callable
        assert callable(get_state_store)
        assert callable(get_state_service)
        assert callable(get_state_rules)
        assert callable(validate_state_change)
        assert callable(get_state_digest)
        assert callable(compute_state_digest)
        assert callable(get_invalidation_service)
        assert callable(invalidate_preview_cache)
        assert callable(get_navigation_state)
    
    def test_state_service_basic_operations(self):
        """Test basic state service operations."""
        from ui.state import get_state_service
        
        service = get_state_service()
        
        # Test set/get
        service.set('test_key', 'test_value')
        assert service.get('test_key') == 'test_value'
        
        # Test update
        service.update({'key1': 'value1', 'key2': 'value2'})
        assert service.get('key1') == 'value1'
        assert service.get('key2') == 'value2'
        
        # Test delete
        service.delete('test_key')
        assert service.get('test_key') is None


class TestFormSemanticsIntegration:
    """Test form semantics integration."""
    
    def test_form_manager_import(self):
        """Test that form manager can be imported."""
        from ui.forms import (
            get_form_manager, form_context,
            add_form_field, submit_current_form,
            validate_current_form
        )
        
        manager = get_form_manager()
        assert manager is not None
        assert callable(form_context)
        assert callable(add_form_field)
        assert callable(submit_current_form)
        assert callable(validate_current_form)
    
    def test_form_context_basic_usage(self):
        """Test basic form context usage."""
        from ui.forms import form_context, add_form_field, get_form_manager
        
        submitted_data = {}
        
        def on_submit(data):
            submitted_data.update(data)
        
        manager = get_form_manager()
        
        with form_context("test_form", on_submit) as context:
            assert context.form_id == "test_form"
            
            # Add fields
            add_form_field("field1", "value1")
            add_form_field("field2", "value2")
            
            # Submit form
            success = manager.submit_form("test_form")
            assert success
            assert submitted_data == {"field1": "value1", "field2": "value2"}


class TestDebouncingIntegration:
    """Test debouncing integration."""
    
    def test_debounce_manager_import(self):
        """Test that debounce manager can be imported."""
        from ui.debounce import (
            get_debounce_manager, debounce_state_update,
            debounce_batch_update, flush_debounced_updates
        )
        
        manager = get_debounce_manager()
        assert manager is not None
        assert callable(debounce_state_update)
        assert callable(debounce_batch_update)
        assert callable(flush_debounced_updates)
    
    def test_debounce_basic_functionality(self):
        """Test basic debouncing functionality."""
        from ui.debounce import get_debounce_manager
        
        manager = get_debounce_manager()
        
        # Test that manager can handle updates
        executed_updates = []
        
        def test_callback(key, value):
            executed_updates.append((key, value))
        
        # Add update
        manager.debounce_update("test_key", "test_value", test_callback)
        
        # Check that update is pending
        assert manager.is_pending("test_key")
        
        # Flush immediately
        manager.flush_key("test_key")
        
        # Check that callback was executed
        assert ("test_key", "test_value") in executed_updates


class TestSharedRenderCoreIntegration:
    """Test shared render core integration."""
    
    def test_render_core_import(self):
        """Test that render core can be imported."""
        from services.render_core import (
            render_cards_unified, RenderOptions,
            create_render_options_from_legacy
        )
        
        assert callable(render_cards_unified)
        assert RenderOptions is not None
        assert callable(create_render_options_from_legacy)
    
    def test_render_options_creation(self):
        """Test render options creation."""
        from services.render_core import RenderOptions, create_render_options_from_legacy
        
        # Test direct creation
        options = RenderOptions()
        assert options.card_size_cm > 0
        assert options.gap_cm >= 0
        assert options.margin_cm >= 0
        
        # Test legacy conversion
        legacy_options = {
            'card_size_cm': 5.5,
            'gap_cm': 0.5,
            'margin_cm': 1.0,
            'hanzi_font_size': 48,
            'pinyin_font_size': 18,
            'english_font_size': 14,
            'page_size': 'A4',
            'hanzi_font_family': 'SimHei',
            'background_color': '#ffffff',
            'layout_rows': 2,
            'layout_cols': 3,
            'layout_auto_fill': True
        }

        converted = create_render_options_from_legacy(**legacy_options)
        assert converted.card_size_cm == 5.5
        assert converted.gap_cm == 0.5
        assert converted.margin_cm == 1.0
        assert converted.hanzi_font_size_pt == 48
        assert converted.pinyin_font_size_pt == 18
        assert converted.english_font_size_pt == 14
        assert converted.page_size == 'A4'
        assert converted.hanzi_font_family == 'SimHei'
        assert converted.background_color == '#ffffff'
        assert converted.layout_rows == 2
        assert converted.layout_cols == 3
        assert converted.layout_auto_fill == True


class TestLayoutLogicExtraction:
    """Test layout logic extraction."""
    
    def test_layout_functions_import(self):
        """Test that layout functions can be imported."""
        from services.layout import (
            get_page_dimensions_cm, compute_auto_card_size_cm,
            compute_pdf_layout, compute_pptx_layout,
            validate_layout_params
        )
        
        assert callable(get_page_dimensions_cm)
        assert callable(compute_auto_card_size_cm)
        assert callable(compute_pdf_layout)
        assert callable(compute_pptx_layout)
        assert callable(validate_layout_params)
    
    def test_page_dimensions(self):
        """Test page dimensions calculation."""
        from services.layout import get_page_dimensions_cm
        
        # Test A4
        width_cm, height_cm = get_page_dimensions_cm('A4')
        assert width_cm == 21.0
        assert height_cm == 29.7

        # Test A3
        width_cm, height_cm = get_page_dimensions_cm('A3')
        assert width_cm == 29.7
        assert height_cm == 42.0
    
    def test_layout_validation(self):
        """Test layout validation."""
        from services.layout import validate_layout_params
        
        # Test valid layout
        result = validate_layout_params(2, 3, 5.0, 0.5, 1.0, 'A4')
        assert result['fits_on_page'] is True
        assert len(result['errors']) == 0
        
        # Test invalid layout (too large)
        result = validate_layout_params(10, 10, 5.0, 0.5, 1.0, 'A4')
        assert result['fits_on_page'] is False
        assert len(result['errors']) > 0


class TestEndToEndIntegration:
    """Test end-to-end integration of all fixes."""
    
    def test_all_systems_work_together(self):
        """Test that all systems can work together without conflicts."""
        # This is a smoke test to ensure no import conflicts
        
        # Import all major components
        from ui.adapters.streamlit_adapter import StreamlitAdapter
        from ui.state import get_state_service
        from ui.forms import get_form_manager
        from ui.debounce import get_debounce_manager
        from services.render_core import RenderOptions
        from services.layout import validate_layout_params
        
        # Test that they can all be instantiated
        adapter = StreamlitAdapter()
        state_service = get_state_service()
        form_manager = get_form_manager()
        debounce_manager = get_debounce_manager()
        render_options = RenderOptions()
        
        # Test basic operations
        state_service.set('test', 'value')
        assert state_service.get('test') == 'value'
        
        # Test layout validation
        result = validate_layout_params(2, 3, 5.0, 0.5, 1.0, 'A4')
        assert 'fits_on_page' in result
        
        # If we get here, all systems are compatible
        assert True
