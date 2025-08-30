"""
Integration tests for digest debug functionality.
Tests the complete debug workflow including recording and display.
"""

import os
import pytest
from unittest.mock import patch

from core.feature_flags import set_test_override, clear_all_test_overrides
from ui.debug import (
    record_digest_debug, get_digest_debug_entries, clear_digest_debug,
    compute_processing_digest_debug, compute_layout_digest_debug,
    compute_style_digest_debug, compute_preview_params_digest_debug,
    is_digest_debug_enabled
)


class TestDigestDebugIntegration:
    """Integration tests for digest debug functionality."""
    
    def setup_method(self):
        """Set up test environment."""
        clear_all_test_overrides()
        clear_digest_debug()
    
    def teardown_method(self):
        """Clean up test environment."""
        clear_all_test_overrides()
        clear_digest_debug()
    
    def test_digest_debug_disabled_by_default(self):
        """Test that digest debug is disabled by default."""
        assert is_digest_debug_enabled() is False
        
        # Recording should not create entries when disabled
        record_digest_debug("test", {"key": "value"}, "digest123")
        entries = get_digest_debug_entries()
        assert len(entries) == 0
    
    def test_digest_debug_enabled_via_feature_flag(self):
        """Test enabling digest debug via feature flag."""
        # Enable digest debug
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        assert is_digest_debug_enabled() is True
        
        # Recording should create entries when enabled
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session123'):
            with patch('ui.debug.get_code_version', return_value='v1.0.0'):
                record_digest_debug("test", {"key": "value"}, "digest123")
                
                entries = get_digest_debug_entries()
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.domain == "test"
                assert entry.raw_inputs == {"key": "value"}
                assert entry.digest == "digest123"
                assert entry.session_generation == "session123"
                assert entry.code_version == "v1.0.0"
    
    def test_digest_debug_environment_variable(self):
        """Test enabling digest debug via environment variable."""
        with patch.dict(os.environ, {'ZIKA_FEATURE_ENABLE_DIGEST_DEBUG': 'true'}, clear=False):
            # Clear test overrides to use environment variable
            clear_all_test_overrides()
            
            assert is_digest_debug_enabled() is True
            
            # Recording should work
            with patch('ui.debug.ui_state_module.get_session_generation', return_value='session456'):
                with patch('ui.debug.get_code_version', return_value='v1.0.1'):
                    record_digest_debug("env_test", {"env": "variable"}, "env_digest")
                    
                    entries = get_digest_debug_entries()
                    assert len(entries) == 1
                    
                    entry = entries[0]
                    assert entry.domain == "env_test"
                    assert entry.raw_inputs == {"env": "variable"}
                    assert entry.digest == "env_digest"
    
    @patch('ui.debug.st')
    def test_compute_processing_digest_debug_integration(self, mock_st):
        """Test processing digest computation with debug recording."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        # Mock session state
        mock_st.session_state.input_text = "integration test"
        mock_st.session_state.auto_pinyin = True
        mock_st.session_state.auto_translate = False
        mock_st.session_state.translate_order = "pinyin_first"
        
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session789'):
            with patch('ui.debug.get_code_version', return_value='v1.0.2'):
                digest = compute_processing_digest_debug()
                
                # Verify digest was computed
                assert isinstance(digest, str)
                assert len(digest) == 16  # Truncated SHA256
                
                # Verify debug entry was recorded
                entries = get_digest_debug_entries()
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.domain == "processing"
                assert entry.raw_inputs['input_text'] == "integration test"
                assert entry.raw_inputs['auto_pinyin'] is True
                assert entry.raw_inputs['auto_translate'] is False
                assert entry.raw_inputs['translate_order'] == "pinyin_first"
                assert entry.digest == digest
    
    @patch('ui.debug.st')
    def test_compute_layout_digest_debug_integration(self, mock_st):
        """Test layout digest computation with debug recording."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        # Mock session state
        mock_st.session_state.rows = 3
        mock_st.session_state.cols = 3
        mock_st.session_state.gap_cm = 0.8
        mock_st.session_state.margin_cm = 1.2
        mock_st.session_state.page_size = 'A3'
        mock_st.session_state.auto_fill = False
        mock_st.session_state.card_size = 'manual'
        
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session999'):
            with patch('ui.debug.get_code_version', return_value='v1.0.3'):
                digest = compute_layout_digest_debug()
                
                # Verify digest was computed
                assert isinstance(digest, str)
                assert len(digest) == 16
                
                # Verify debug entry was recorded
                entries = get_digest_debug_entries()
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.domain == "layout"
                assert entry.raw_inputs['rows'] == 3
                assert entry.raw_inputs['cols'] == 3
                assert entry.raw_inputs['gap_cm'] == 0.8
                assert entry.raw_inputs['margin_cm'] == 1.2
                assert entry.raw_inputs['page_size'] == 'A3'
                assert entry.raw_inputs['auto_fill'] is False
                assert entry.raw_inputs['card_size'] == 'manual'
                assert entry.digest == digest
    
    @patch('ui.debug.st')
    def test_compute_style_digest_debug_integration(self, mock_st):
        """Test style digest computation with debug recording."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        # Mock session state
        mock_st.session_state.font_hanzi = 36
        mock_st.session_state.font_pinyin = 16
        mock_st.session_state.font_english = 12
        mock_st.session_state.hanzi_font = 'KaiTi'
        mock_st.session_state.background_color = '#f0f0f0'
        
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session111'):
            with patch('ui.debug.get_code_version', return_value='v1.0.4'):
                digest = compute_style_digest_debug()
                
                # Verify digest was computed
                assert isinstance(digest, str)
                assert len(digest) == 16
                
                # Verify debug entry was recorded
                entries = get_digest_debug_entries()
                assert len(entries) == 1
                
                entry = entries[0]
                assert entry.domain == "style"
                assert entry.raw_inputs['font_hanzi'] == 36
                assert entry.raw_inputs['font_pinyin'] == 16
                assert entry.raw_inputs['font_english'] == 12
                assert entry.raw_inputs['hanzi_font'] == 'KaiTi'
                assert entry.raw_inputs['background_color'] == '#f0f0f0'
                assert entry.digest == digest
    
    @patch('ui.debug.st')
    def test_compute_preview_params_digest_debug_integration(self, mock_st):
        """Test preview params digest computation with debug recording."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        # Mock session state
        mock_st.session_state.preview_mode = '📄 单页预览'
        
        # Mock the sub-digest functions
        with patch('ui.debug.compute_layout_digest_debug', return_value='layout_debug_123'):
            with patch('ui.debug.compute_style_digest_debug', return_value='style_debug_456'):
                with patch('ui.debug.ui_state_module.get_session_generation', return_value='session222'):
                    with patch('ui.debug.get_code_version', return_value='v1.0.5'):
                        digest = compute_preview_params_digest_debug(15)
                        
                        # Verify digest was computed
                        assert isinstance(digest, str)
                        assert len(digest) == 16
                        
                        # Verify debug entry was recorded
                        entries = get_digest_debug_entries()
                        # Should have 1 entry: preview_params (sub-digests are mocked)
                        assert len(entries) == 1
                        
                        # Get the preview_params entry
                        preview_entry = entries[0]
                        assert preview_entry.domain == "preview_params"
                        assert preview_entry.raw_inputs['layout_digest'] == 'layout_debug_123'
                        assert preview_entry.raw_inputs['style_digest'] == 'style_debug_456'
                        assert preview_entry.raw_inputs['preview_mode'] == '📄 单页预览'
                        assert preview_entry.raw_inputs['cards_count'] == 15
                        assert preview_entry.raw_inputs['schema_version'] == 'v1.0.0'
                        assert preview_entry.raw_inputs['session_generation'] == 'session222'
                        assert preview_entry.raw_inputs['code_version'] == 'v1.0.5'
                        assert preview_entry.digest == digest
    
    def test_multiple_digest_recordings(self):
        """Test recording multiple digests and entry management."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session_multi'):
            with patch('ui.debug.get_code_version', return_value='v1.0.6'):
                # Record multiple digests
                record_digest_debug("domain1", {"key1": "value1"}, "digest1")
                record_digest_debug("domain2", {"key2": "value2"}, "digest2")
                record_digest_debug("domain3", {"key3": "value3"}, "digest3")
                
                entries = get_digest_debug_entries()
                assert len(entries) == 3
                
                # Verify all entries are recorded
                domains = [entry.domain for entry in entries]
                assert "domain1" in domains
                assert "domain2" in domains
                assert "domain3" in domains
                
                # Clear and verify
                clear_digest_debug()
                entries = get_digest_debug_entries()
                assert len(entries) == 0
    
    def test_digest_debug_with_normalization(self):
        """Test that debug entries show both raw and normalized inputs."""
        set_test_override('ENABLE_DIGEST_DEBUG', True)
        
        with patch('ui.debug.ui_state_module.get_session_generation', return_value='session_norm'):
            with patch('ui.debug.get_code_version', return_value='v1.0.7'):
                # Record digest with data that will be normalized
                raw_inputs = {
                    'float_value': 1.23456789,  # Should be rounded to 4 decimals
                    'dict_value': {'z': 3, 'a': 1, 'b': 2},  # Should be sorted
                    'set_value': {3, 1, 2},  # Should be converted to sorted list
                }
                
                record_digest_debug("normalization_test", raw_inputs, "norm_digest")
                
                entries = get_digest_debug_entries()
                assert len(entries) == 1
                
                entry = entries[0]
                
                # Raw inputs should be unchanged
                assert entry.raw_inputs['float_value'] == 1.23456789
                assert entry.raw_inputs['dict_value'] == {'z': 3, 'a': 1, 'b': 2}
                assert entry.raw_inputs['set_value'] == {3, 1, 2}
                
                # Normalized inputs should be processed
                assert entry.normalized_inputs['float_value'] == 1.2346
                assert list(entry.normalized_inputs['dict_value'].keys()) == ['a', 'b', 'z']
                assert entry.normalized_inputs['set_value'] == [1, 2, 3]
