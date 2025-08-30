"""
Integration tests to verify complete Streamlit migration.

Tests that all UI modules can work with adapters enabled.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from core.feature_flags import set_test_override, get_feature_flag, clear_all_test_overrides


class TestStreamlitMigrationComplete:
    """Test complete Streamlit migration."""
    
    def setup_method(self):
        """Setup test environment."""
        # Clear any existing overrides
        clear_all_test_overrides()
        # Enable all adapter flags
        set_test_override('ui_adapter', True)
        set_test_override('adapted_inputs', True)
        set_test_override('adapted_options', True)
        set_test_override('adapted_preview', True)
        set_test_override('adapted_editor', True)
        set_test_override('adapted_export', True)
        set_test_override('adapted_sidebar', True)
    
    def test_all_adapter_flags_enabled(self):
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
            assert get_feature_flag(flag, False), f"Flag {flag} should be enabled"
    
    def test_sections_module_adapter_integration(self):
        """Test that sections module integrates with adapters."""
        from ui.sections import render_sidebar, render_export_section, render_left_column, render_right_column
        
        # Mock session state and dependencies
        with patch('streamlit.session_state') as mock_session:
            mock_session.dictionary.get_statistics.return_value = {'mini_dict_entries': 100}
            mock_session.total_cards_generated = 50
            mock_session.export_history = []
            mock_session.get.return_value = 'A4'
            
            # Mock adapter
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.layout.sidebar.return_value.__enter__ = Mock()
                mock_adapter.layout.sidebar.return_value.__exit__ = Mock()
                mock_adapter.layout.columns.return_value = [Mock(), Mock(), Mock()]
                mock_get_adapter.return_value = mock_adapter
                
                # Test that functions can be called without errors
                try:
                    render_sidebar()
                    # Verify adapter was used
                    mock_get_adapter.assert_called()
                    mock_adapter.header.assert_called()
                except Exception as e:
                    pytest.fail(f"render_sidebar failed with adapter: {e}")
    
    def test_inputs_module_adapter_integration(self):
        """Test that inputs module integrates with adapters."""
        from ui.inputs import render_input_section
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.get.return_value = '手动输入'
            mock_session.input_text = '你好 世界'
            
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.inputs.radio.return_value = '手动输入'
                mock_adapter.inputs.selectbox.return_value = '颜色'
                mock_adapter.inputs.text_area.return_value = '你好 世界'
                mock_adapter.inputs.checkbox.return_value = False
                mock_adapter.inputs.button.return_value = False
                mock_adapter.layout.columns.return_value = [Mock(), Mock()]
                mock_get_adapter.return_value = mock_adapter
                
                # Mock processing functions
                with patch('services.processing.parse_input_text') as mock_parse:
                    mock_parse.return_value = [{'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'}]
                    
                    try:
                        result = render_input_section()
                        assert isinstance(result, list)
                        # Verify adapter was used
                        mock_get_adapter.assert_called()
                        mock_adapter.header.assert_called()
                    except Exception as e:
                        pytest.fail(f"render_input_section failed with adapter: {e}")
    
    def test_options_module_adapter_integration(self):
        """Test that options module integrates with adapters."""
        from ui.options import render_options_section, render_advanced_options
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.get.return_value = True
            
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.inputs.checkbox.return_value = True
                mock_adapter.inputs.selectbox.return_value = 'A4'
                mock_adapter.inputs.slider.return_value = 5.5
                mock_get_adapter.return_value = mock_adapter
                
                try:
                    result = render_options_section()
                    assert isinstance(result, tuple)
                    assert len(result) == 4  # auto_pinyin, auto_translate, page_size, card_size
                    # Verify adapter was used
                    mock_get_adapter.assert_called()
                except Exception as e:
                    pytest.fail(f"render_options_section failed with adapter: {e}")
    
    def test_editor_module_adapter_integration(self):
        """Test that editor module integrates with adapters."""
        from ui.editor import render_improved_card_editor
        
        test_cards = [
            {'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'},
            {'hanzi': '世界', 'pinyin': 'shi jie', 'english': 'world'}
        ]
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.edit_page = 0
            mock_session.processed_cards = test_cards
            
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.inputs.radio.return_value = '分页编辑'
                mock_adapter.layout.columns.return_value = [Mock(), Mock(), Mock()]
                mock_get_adapter.return_value = mock_adapter
                
                try:
                    render_improved_card_editor(test_cards)
                    # Verify adapter was used
                    mock_get_adapter.assert_called()
                except Exception as e:
                    pytest.fail(f"render_improved_card_editor failed with adapter: {e}")
    
    def test_preview_module_adapter_integration(self):
        """Test that preview module integrates with adapters."""
        from ui.preview import render_preview_section_wrapper
        
        test_cards = [
            {'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'}
        ]
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.get.return_value = '📄 完整页面'
            mock_session.preview_mode = '📄 完整页面'
            mock_session.current_page = 0
            mock_session.last_params = {}
            mock_session.export_ready = {}
            mock_session.export_data = {}
            
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.inputs.radio.return_value = '📄 完整页面'
                mock_adapter.layout.expander.return_value.__enter__ = Mock()
                mock_adapter.layout.expander.return_value.__exit__ = Mock()
                mock_get_adapter.return_value = mock_adapter
                
                # Mock preview rendering
                with patch('services.cache.create_preview_html') as mock_create_html:
                    mock_create_html.return_value = '<div>Preview</div>'
                    
                    try:
                        render_preview_section_wrapper(
                            processed_cards=test_cards,
                            card_size=5.5, gap=0.5, margin=1.0, page_size='A4',
                            font_hanzi=48, font_pinyin=18, font_english=14,
                            hanzi_font='SimHei', background_color='#ffffff',
                            rows=2, cols=3, auto_fill=True
                        )
                        # Verify adapter was used
                        mock_get_adapter.assert_called()
                        mock_adapter.header.assert_called()
                    except Exception as e:
                        pytest.fail(f"render_preview_section_wrapper failed with adapter: {e}")
    
    def test_export_section_adapter_integration(self):
        """Test that export section integrates with adapters."""
        from ui.sections import render_export_section
        
        test_cards = [
            {'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'}
        ]
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.get.return_value = 5.5
            mock_session.hanzi_font = 'SimHei'
            mock_session.background_color = '#ffffff'
            mock_session.rows = 2
            mock_session.cols = 3
            mock_session.auto_fill = True
            mock_session.export_ready = {}
            mock_session.export_data = {}
            mock_session.export_history = []
            mock_session.total_cards_generated = 0
            
            with patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                mock_adapter = Mock()
                mock_adapter.layout.columns.return_value = [Mock(), Mock(), Mock()]
                mock_adapter.inputs.button.return_value = False
                mock_adapter.notify = Mock()
                mock_get_adapter.return_value = mock_adapter
                
                try:
                    render_export_section(test_cards)
                    # Verify adapter was used
                    mock_get_adapter.assert_called()
                    mock_adapter.header.assert_called()
                except Exception as e:
                    pytest.fail(f"render_export_section failed with adapter: {e}")
    
    def test_adapter_fallback_behavior(self):
        """Test that adapter fallback works when adapters fail."""
        # Disable adapter flags
        set_test_override('ui_adapter', False)
        set_test_override('adapted_inputs', False)
        
        from ui.inputs import render_input_section
        
        with patch('streamlit.session_state') as mock_session:
            mock_session.get.return_value = '手动输入'
            mock_session.input_text = '你好'
            
            # Mock Streamlit functions
            with patch('streamlit.header'), \
                 patch('streamlit.radio') as mock_radio, \
                 patch('streamlit.selectbox') as mock_selectbox, \
                 patch('streamlit.text_area') as mock_text_area, \
                 patch('streamlit.checkbox') as mock_checkbox, \
                 patch('streamlit.button') as mock_button, \
                 patch('streamlit.columns') as mock_columns, \
                 patch('streamlit.write'), \
                 patch('streamlit.markdown'):
                
                mock_radio.return_value = '手动输入'
                mock_selectbox.return_value = '颜色'
                mock_text_area.return_value = '你好'
                mock_checkbox.return_value = False
                mock_button.return_value = False
                mock_columns.return_value = [Mock(), Mock()]
                
                with patch('services.processing.parse_input_text') as mock_parse:
                    mock_parse.return_value = [{'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'}]
                    
                    try:
                        result = render_input_section()
                        assert isinstance(result, list)
                        # Verify Streamlit functions were called (fallback)
                        mock_radio.assert_called()
                    except Exception as e:
                        pytest.fail(f"Fallback failed: {e}")


class TestAdapterConsistency:
    """Test that adapter and legacy paths produce consistent results."""
    
    def test_input_section_consistency(self):
        """Test that adapter and legacy input sections are consistent."""
        # This would require more complex mocking to ensure identical behavior
        # For now, we test that both paths can execute without errors
        
        test_cases = [
            {'adapted_inputs': True},
            {'adapted_inputs': False}
        ]
        
        for case in test_cases:
            set_test_override('adapted_inputs', case['adapted_inputs'])
            
            with patch('streamlit.session_state') as mock_session:
                mock_session.get.return_value = '手动输入'
                mock_session.input_text = '你好'
                
                # Mock all necessary functions
                with patch('streamlit.header'), \
                     patch('streamlit.radio', return_value='手动输入'), \
                     patch('streamlit.selectbox', return_value='颜色'), \
                     patch('streamlit.text_area', return_value='你好'), \
                     patch('streamlit.checkbox', return_value=False), \
                     patch('streamlit.button', return_value=False), \
                     patch('streamlit.columns', return_value=[Mock(), Mock()]), \
                     patch('streamlit.write'), \
                     patch('streamlit.markdown'), \
                     patch('ui.ports.get_ui_adapter') as mock_get_adapter:
                    
                    if case['adapted_inputs']:
                        mock_adapter = Mock()
                        mock_adapter.inputs.radio.return_value = '手动输入'
                        mock_adapter.inputs.selectbox.return_value = '颜色'
                        mock_adapter.inputs.text_area.return_value = '你好'
                        mock_adapter.inputs.checkbox.return_value = False
                        mock_adapter.inputs.button.return_value = False
                        mock_adapter.layout.columns.return_value = [Mock(), Mock()]
                        mock_get_adapter.return_value = mock_adapter
                    
                    with patch('services.processing.parse_input_text') as mock_parse:
                        mock_parse.return_value = [{'hanzi': '你好', 'pinyin': 'ni hao', 'english': 'hello'}]
                        
                        from ui.inputs import render_input_section
                        
                        try:
                            result = render_input_section()
                            assert isinstance(result, list)
                            assert len(result) == 1
                            assert result[0]['hanzi'] == '你好'
                        except Exception as e:
                            pytest.fail(f"Input section failed with {case}: {e}")
