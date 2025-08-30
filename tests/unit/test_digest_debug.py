"""
Unit tests for digest debug functionality.
Tests debug panel, logging, and digest recording.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from ui.debug import (
    DigestDebugInfo, DigestDebugCollector,
    record_digest_debug, get_digest_debug_entries, clear_digest_debug,
    compute_processing_digest_debug, compute_layout_digest_debug,
    compute_style_digest_debug, compute_preview_params_digest_debug,
    enable_digest_debug, disable_digest_debug, is_digest_debug_enabled
)


class TestDigestDebugInfo:
    """Test DigestDebugInfo dataclass."""
    
    def test_digest_debug_info_creation(self):
        """Test creating DigestDebugInfo."""
        info = DigestDebugInfo(
            domain="test",
            raw_inputs={"key": "value"},
            normalized_inputs={"key": "value"},
            digest="abc123",
            timestamp="2025-08-30T12:00:00",
            session_generation="session123",
            code_version="v1.0.0"
        )
        
        assert info.domain == "test"
        assert info.raw_inputs == {"key": "value"}
        assert info.normalized_inputs == {"key": "value"}
        assert info.digest == "abc123"
        assert info.timestamp == "2025-08-30T12:00:00"
        assert info.session_generation == "session123"
        assert info.code_version == "v1.0.0"


class TestDigestDebugCollector:
    """Test DigestDebugCollector class."""
    
    def setup_method(self):
        """Set up test environment."""
        self.collector = DigestDebugCollector()
    
    def test_record_digest_disabled(self):
        """Test recording digest when debug is disabled."""
        with patch.object(self.collector, '_is_debug_enabled', return_value=False):
            self.collector.record_digest("test", {"key": "value"}, "digest123")
            
            entries = self.collector.get_debug_entries()
            assert len(entries) == 0
    
    def test_record_digest_enabled(self):
        """Test recording digest when debug is enabled."""
        with patch.object(self.collector, '_is_debug_enabled', return_value=True):
            with patch('ui.debug.ui_state_module.get_session_generation', return_value='session123'):
                with patch('ui.debug.get_code_version', return_value='v1.0.0'):
                    self.collector.record_digest("test", {"key": "value"}, "digest123")
                    
                    entries = self.collector.get_debug_entries()
                    assert len(entries) == 1
                    
                    entry = entries[0]
                    assert entry.domain == "test"
                    assert entry.raw_inputs == {"key": "value"}
                    assert entry.digest == "digest123"
                    assert entry.session_generation == "session123"
                    assert entry.code_version == "v1.0.0"
    
    def test_max_entries_limit(self):
        """Test that collector respects max entries limit."""
        with patch.object(self.collector, '_is_debug_enabled', return_value=True):
            with patch('ui.debug.ui_state_module.get_session_generation', return_value='session123'):
                with patch('ui.debug.get_code_version', return_value='v1.0.0'):
                    # Set a small max entries for testing
                    self.collector._max_entries = 3
                    
                    # Record more entries than the limit
                    for i in range(5):
                        self.collector.record_digest(f"test{i}", {"key": f"value{i}"}, f"digest{i}")
                    
                    entries = self.collector.get_debug_entries()
                    assert len(entries) == 3
                    
                    # Should keep the last 3 entries
                    assert entries[0].domain == "test2"
                    assert entries[1].domain == "test3"
                    assert entries[2].domain == "test4"
    
    def test_clear_debug_entries(self):
        """Test clearing debug entries."""
        with patch.object(self.collector, '_is_debug_enabled', return_value=True):
            with patch('ui.debug.ui_state_module.get_session_generation', return_value='session123'):
                with patch('ui.debug.get_code_version', return_value='v1.0.0'):
                    self.collector.record_digest("test", {"key": "value"}, "digest123")
                    assert len(self.collector.get_debug_entries()) == 1
                    
                    self.collector.clear_debug_entries()
                    assert len(self.collector.get_debug_entries()) == 0
    
    def test_is_debug_enabled(self):
        """Test debug enabled check."""
        with patch('ui.debug.get_feature_flag') as mock_flag:
            mock_flag.return_value = True
            assert self.collector._is_debug_enabled() is True
            
            mock_flag.return_value = False
            assert self.collector._is_debug_enabled() is False
            
            mock_flag.assert_called_with('ENABLE_DIGEST_DEBUG', default=False)


class TestGlobalFunctions:
    """Test global debug functions."""
    
    def test_record_digest_debug(self):
        """Test global record_digest_debug function."""
        with patch('ui.debug._debug_collector') as mock_collector:
            record_digest_debug("test", {"key": "value"}, "digest123")
            mock_collector.record_digest.assert_called_once_with("test", {"key": "value"}, "digest123")
    
    def test_get_digest_debug_entries(self):
        """Test global get_digest_debug_entries function."""
        with patch('ui.debug._debug_collector') as mock_collector:
            mock_collector.get_debug_entries.return_value = ["entry1", "entry2"]
            
            entries = get_digest_debug_entries()
            assert entries == ["entry1", "entry2"]
            mock_collector.get_debug_entries.assert_called_once()
    
    def test_clear_digest_debug(self):
        """Test global clear_digest_debug function."""
        with patch('ui.debug._debug_collector') as mock_collector:
            clear_digest_debug()
            mock_collector.clear_debug_entries.assert_called_once()


class TestDebugDigestFunctions:
    """Test debug versions of digest computation functions."""
    
    @patch('ui.debug.st')
    def test_compute_processing_digest_debug(self, mock_st):
        """Test processing digest computation with debug."""
        # Mock session state
        mock_st.session_state.input_text = "test text"
        mock_st.session_state.auto_pinyin = True
        mock_st.session_state.auto_translate = False
        mock_st.session_state.translate_order = "pinyin_first"
        
        with patch('ui.debug.ui_state_module.stable_digest', return_value='digest123') as mock_digest:
            with patch('ui.debug.record_digest_debug') as mock_record:
                result = compute_processing_digest_debug()
                
                assert result == 'digest123'
                
                # Check that digest was computed with correct inputs
                expected_inputs = {
                    'input_text': 'test text',
                    'auto_pinyin': True,
                    'auto_translate': False,
                    'translate_order': 'pinyin_first'
                }
                mock_digest.assert_called_once_with(expected_inputs)
                mock_record.assert_called_once_with('processing', expected_inputs, 'digest123')
    
    @patch('ui.debug.st')
    def test_compute_layout_digest_debug(self, mock_st):
        """Test layout digest computation with debug."""
        # Mock session state
        mock_st.session_state.rows = 4
        mock_st.session_state.cols = 2
        mock_st.session_state.gap_cm = 0.5
        mock_st.session_state.margin_cm = 1.0
        mock_st.session_state.page_size = 'A4'
        mock_st.session_state.auto_fill = True
        mock_st.session_state.card_size = 'auto'
        
        with patch('ui.debug.ui_state_module.stable_digest', return_value='layout123') as mock_digest:
            with patch('ui.debug.record_digest_debug') as mock_record:
                result = compute_layout_digest_debug()
                
                assert result == 'layout123'
                
                # Check that digest was computed with correct inputs
                expected_inputs = {
                    'rows': 4,
                    'cols': 2,
                    'gap_cm': 0.5,
                    'margin_cm': 1.0,
                    'page_size': 'A4',
                    'auto_fill': True,
                    'card_size': 'auto'
                }
                mock_digest.assert_called_once_with(expected_inputs)
                mock_record.assert_called_once_with('layout', expected_inputs, 'layout123')
    
    @patch('ui.debug.st')
    def test_compute_style_digest_debug(self, mock_st):
        """Test style digest computation with debug."""
        # Mock session state
        mock_st.session_state.font_hanzi = 48
        mock_st.session_state.font_pinyin = 18
        mock_st.session_state.font_english = 14
        mock_st.session_state.hanzi_font = 'SimHei'
        mock_st.session_state.background_color = '#ffffff'
        
        with patch('ui.debug.ui_state_module.stable_digest', return_value='style123') as mock_digest:
            with patch('ui.debug.record_digest_debug') as mock_record:
                result = compute_style_digest_debug()
                
                assert result == 'style123'
                
                # Check that digest was computed with correct inputs
                expected_inputs = {
                    'font_hanzi': 48,
                    'font_pinyin': 18,
                    'font_english': 14,
                    'hanzi_font': 'SimHei',
                    'background_color': '#ffffff'
                }
                mock_digest.assert_called_once_with(expected_inputs)
                mock_record.assert_called_once_with('style', expected_inputs, 'style123')
    
    @patch('ui.debug.st')
    def test_compute_preview_params_digest_debug(self, mock_st):
        """Test preview params digest computation with debug."""
        # Mock session state
        mock_st.session_state.preview_mode = '📄 完整页面'
        
        with patch('ui.debug.compute_layout_digest_debug', return_value='layout123'):
            with patch('ui.debug.compute_style_digest_debug', return_value='style123'):
                with patch('ui.debug.ui_state_module.get_session_generation', return_value='session123'):
                    with patch('ui.debug.get_code_version', return_value='v1.0.0'):
                        with patch('ui.debug.ui_state_module.stable_digest', return_value='preview123') as mock_digest:
                            with patch('ui.debug.record_digest_debug') as mock_record:
                                result = compute_preview_params_digest_debug(10)
                                
                                assert result == 'preview123'
                                
                                # Check that digest was computed with correct inputs
                                expected_inputs = {
                                    'layout_digest': 'layout123',
                                    'style_digest': 'style123',
                                    'preview_mode': '📄 完整页面',
                                    'cards_count': 10,
                                    'schema_version': 'v1.0.0',
                                    'session_generation': 'session123',
                                    'code_version': 'v1.0.0'
                                }
                                mock_digest.assert_called_once_with(expected_inputs)
                                mock_record.assert_called_once_with('preview_params', expected_inputs, 'preview123')


class TestDebugControlFunctions:
    """Test debug control functions."""
    
    @patch('ui.debug.st')
    def test_enable_digest_debug(self, mock_st):
        """Test enabling digest debug."""
        enable_digest_debug()
        assert mock_st.session_state.__setitem__.called
        mock_st.session_state.__setitem__.assert_called_with('ENABLE_DIGEST_DEBUG', True)
    
    @patch('ui.debug.st')
    def test_disable_digest_debug(self, mock_st):
        """Test disabling digest debug."""
        disable_digest_debug()
        assert mock_st.session_state.__setitem__.called
        mock_st.session_state.__setitem__.assert_called_with('ENABLE_DIGEST_DEBUG', False)
    
    def test_is_digest_debug_enabled(self):
        """Test checking if digest debug is enabled."""
        with patch('ui.debug.get_feature_flag') as mock_flag:
            mock_flag.return_value = True
            assert is_digest_debug_enabled() is True
            
            mock_flag.return_value = False
            assert is_digest_debug_enabled() is False
            
            mock_flag.assert_called_with('ENABLE_DIGEST_DEBUG', default=False)
