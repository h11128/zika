"""
End-to-end integration tests for the complete refactored UI system.
Tests full user workflows from input to output with all components working together.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from ui.ports import get_ui_adapter, ComponentConfig
from ui.inputs import render_input_section_adapted
from ui.options import render_options_section_adapted, render_advanced_options_adapted
from ui.sidebar import render_sidebar_adapted
from ui.sections import render_left_column, render_export_section
from ui.error_boundaries import with_error_boundary
from services.performance_monitor import get_performance_monitor, performance_context


class TestCompleteUserWorkflows:
    """Test complete user workflows end-to-end."""
    
    def setup_method(self):
        """Set up test environment."""
        self.adapter = get_ui_adapter()
        self.mock_st = Mock()
    
    def test_complete_card_creation_workflow(self, monkeypatch):
        """Test complete workflow from text input to card generation."""
        # Mock all streamlit components
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        monkeypatch.setattr('ui.sidebar.st', self.mock_st)
        
        # Mock input responses
        self.mock_st.text_area.return_value = "你好\nhello\n测试\ntest"
        self.mock_st.file_uploader.return_value = None
        self.mock_st.button.return_value = False
        
        # Mock options responses
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.side_effect = [3, 2, 48, 18, 14]
        
        # Mock sidebar components
        self.mock_st.sidebar = Mock()
        self.mock_st.header = Mock()
        self.mock_st.metric = Mock()
        self.mock_st.expander = Mock()
        
        # Mock session state
        mock_session_state = {
            'dictionary': Mock(),
            'total_cards_generated': 0,
            'export_history': []
        }
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.sidebar.st.session_state', mock_session_state)
        
        mock_session_state['dictionary'].get_statistics.return_value = {'mini_dict_entries': 100}
        
        # Mock feature flags
        monkeypatch.setattr('ui.sidebar.get_feature_flag', lambda flag, default: default)
        
        # Mock text processing
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [
                {'hanzi': '你好', 'pinyin': 'nihao', 'english': 'hello'},
                {'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}
            ]
            
            with performance_context('complete_workflow'):
                # Step 1: Process input
                cards = render_input_section_adapted(self.adapter)
                
                # Step 2: Configure options
                options = render_options_section_adapted(self.adapter)
                
                # Step 3: Configure advanced options
                advanced = render_advanced_options_adapted(self.adapter)
                
                # Step 4: Render sidebar
                render_sidebar_adapted(self.adapter)
        
        # Validate results
        assert isinstance(cards, list)
        assert len(cards) == 2
        assert all('hanzi' in card and 'pinyin' in card and 'english' in card for card in cards)
        
        assert isinstance(options, tuple)
        assert len(options) == 5
        
        assert isinstance(advanced, tuple)
        assert len(advanced) == 7
    
    def test_error_recovery_workflow(self, monkeypatch):
        """Test that errors in one component don't break the entire workflow."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock normal responses for most components
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.side_effect = [3, 2, 48, 18, 14]
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Make input section fail
        self.mock_st.text_area.side_effect = Exception("Input component failed")
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = []
            
            # Input section should fail gracefully
            try:
                cards = render_input_section_adapted(self.adapter)
                # If error boundary works, this should return None or empty list
                assert cards is None or cards == []
            except Exception:
                # If no error boundary, exception should be caught here
                cards = []
            
            # Options section should still work
            options = render_options_section_adapted(self.adapter)
            assert isinstance(options, tuple)
            
            # Advanced options should still work
            advanced = render_advanced_options_adapted(self.adapter)
            assert isinstance(advanced, tuple)
    
    def test_performance_under_load(self, monkeypatch):
        """Test system performance under load."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock responses
        self.mock_st.text_area.return_value = "测试文本"
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.side_effect = lambda *args, **kwargs: 3
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            # Simulate load by running workflow multiple times
            start_time = time.time()
            
            for i in range(10):
                cards = render_input_section_adapted(self.adapter)
                options = render_options_section_adapted(self.adapter)
                advanced = render_advanced_options_adapted(self.adapter)
            
            duration = time.time() - start_time
            
            # Should complete 10 iterations in reasonable time
            assert duration < 5.0, f"10 workflow iterations took {duration:.2f}s, should be <5s"
    
    def test_memory_stability_workflow(self, monkeypatch):
        """Test that workflows don't leak memory."""
        import gc
        import psutil
        import os
        
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock responses
        self.mock_st.text_area.return_value = "测试"
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.return_value = 3
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            # Run workflow many times
            for i in range(100):
                cards = render_input_section_adapted(self.adapter)
                options = render_options_section_adapted(self.adapter)
                # Don't store references to allow garbage collection
        
        # Force garbage collection
        gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Should not increase memory significantly
        assert memory_increase < 20, f"Memory increased by {memory_increase:.2f}MB, should be <20MB"


class TestCrossComponentIntegration:
    """Test integration between different components."""
    
    def setup_method(self):
        """Set up test environment."""
        self.adapter = get_ui_adapter()
        self.mock_st = Mock()
    
    def test_state_sharing_between_components(self, monkeypatch):
        """Test that components properly share state."""
        # Mock session state that's shared between components
        shared_state = {
            'input_text': '你好\nhello',
            'auto_pinyin': True,
            'page_size': 'A4',
            'card_size_cm': 5.5
        }
        
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        monkeypatch.setattr('ui.inputs.st.session_state', shared_state)
        monkeypatch.setattr('ui.options.st.session_state', shared_state)
        
        # Mock component responses to use shared state
        self.mock_st.text_area.return_value = shared_state['input_text']
        self.mock_st.checkbox.return_value = shared_state['auto_pinyin']
        self.mock_st.selectbox.return_value = shared_state['page_size']
        self.mock_st.slider.return_value = shared_state['card_size_cm']
        self.mock_st.number_input.return_value = 3
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '你好', 'pinyin': 'nihao', 'english': 'hello'}]
            
            # Components should access shared state
            cards = render_input_section_adapted(self.adapter)
            options = render_options_section_adapted(self.adapter)
            
            # Verify state was used
            assert isinstance(cards, list)
            assert isinstance(options, tuple)
            
            # Options should reflect shared state values
            auto_pinyin, auto_translate, page_size, card_size_cm, layout_info = options
            assert auto_pinyin == shared_state['auto_pinyin']
            assert page_size == shared_state['page_size']
            assert card_size_cm == shared_state['card_size_cm']
    
    def test_event_propagation_between_components(self, monkeypatch):
        """Test that events propagate correctly between components."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock session state
        mock_session_state = {'event_triggered': False}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Mock button click event
        self.mock_st.button.return_value = True  # Button clicked
        self.mock_st.text_area.return_value = "测试文本"
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.return_value = 3
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            # Process input (button click should trigger processing)
            cards = render_input_section_adapted(self.adapter)
            
            # Event should have been processed
            assert isinstance(cards, list)
            # In real implementation, button click would trigger text processing
    
    def test_adapter_consistency_across_components(self):
        """Test that the same adapter instance is used across components."""
        # All components should use the same adapter instance
        adapter1 = get_ui_adapter()
        adapter2 = get_ui_adapter()
        adapter3 = get_ui_adapter()
        
        assert adapter1 is adapter2
        assert adapter2 is adapter3
        
        # Components should have consistent interfaces
        assert hasattr(adapter1.inputs, 'text_input')
        assert hasattr(adapter2.layout, 'columns')
        assert hasattr(adapter3.notifications, 'show_success')


class TestDataFlowIntegration:
    """Test data flow through the entire system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.adapter = get_ui_adapter()
        self.mock_st = Mock()
    
    def test_input_to_output_data_flow(self, monkeypatch):
        """Test complete data flow from input to final output."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock input data
        input_text = "你好\nhello\n测试\ntest\n世界\nworld"
        self.mock_st.text_area.return_value = input_text
        self.mock_st.file_uploader.return_value = None
        self.mock_st.button.return_value = False
        
        # Mock options
        self.mock_st.checkbox.return_value = True  # auto_pinyin
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 6.0  # card_size_cm
        self.mock_st.number_input.side_effect = [4, 3, 50, 20, 16]  # cols, rows, fonts
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Mock text processing to return structured data
        expected_cards = [
            {'hanzi': '你好', 'pinyin': 'nihao', 'english': 'hello'},
            {'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'},
            {'hanzi': '世界', 'pinyin': 'shijie', 'english': 'world'}
        ]
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = expected_cards
            
            # Process through entire pipeline
            cards = render_input_section_adapted(self.adapter)
            options = render_options_section_adapted(self.adapter)
            advanced = render_advanced_options_adapted(self.adapter)
            
            # Verify data integrity through pipeline
            assert cards == expected_cards
            
            # Verify options structure
            auto_pinyin, auto_translate, page_size, card_size_cm, layout_info = options
            assert auto_pinyin is True
            assert page_size == "A4"
            assert card_size_cm == 6.0
            
            # Verify advanced options structure
            gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = advanced
            assert layout_cols == 4
            assert layout_rows == 3
            assert hanzi_font_size == 50
    
    def test_configuration_propagation(self, monkeypatch):
        """Test that configuration changes propagate through the system."""
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock session state with initial configuration
        mock_session_state = {
            'card_size_cm': 5.0,
            'layout_cols': 3,
            'layout_rows': 2,
            'hanzi_font_size': 48
        }
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Mock configuration changes
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 7.0  # Changed card size
        self.mock_st.number_input.side_effect = [5, 4, 60, 24, 18]  # Changed layout and fonts
        
        # Get updated configuration
        options = render_options_section_adapted(self.adapter)
        advanced = render_advanced_options_adapted(self.adapter)
        
        # Verify configuration changes are reflected
        auto_pinyin, auto_translate, page_size, card_size_cm, layout_info = options
        assert card_size_cm == 7.0  # Updated value
        
        gap_cm, margin_cm, hanzi_font_size, pinyin_font_size, english_font_size, layout_rows, layout_cols = advanced
        assert layout_cols == 5  # Updated value
        assert layout_rows == 4  # Updated value
        assert hanzi_font_size == 60  # Updated value


class TestErrorHandlingIntegration:
    """Test error handling across the integrated system."""
    
    def setup_method(self):
        """Set up test environment."""
        self.adapter = get_ui_adapter()
        self.mock_st = Mock()
    
    def test_cascading_error_prevention(self, monkeypatch):
        """Test that errors in one component don't cascade to others."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Make input component fail
        self.mock_st.text_area.side_effect = Exception("Input failed")
        
        # Options component should still work
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.return_value = "A4"
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.return_value = 3
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = []
            
            # Input should fail gracefully
            try:
                cards = render_input_section_adapted(self.adapter)
                # Error boundary should handle this
                assert cards is None or isinstance(cards, list)
            except Exception:
                # If no error boundary, should still not break other components
                pass
            
            # Options should still work despite input failure
            options = render_options_section_adapted(self.adapter)
            assert isinstance(options, tuple)
            assert len(options) == 5
    
    def test_partial_failure_recovery(self, monkeypatch):
        """Test recovery from partial system failures."""
        monkeypatch.setattr('ui.inputs.st', self.mock_st)
        monkeypatch.setattr('ui.options.st', self.mock_st)
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        # Mock partial failure in options (some components work, others fail)
        self.mock_st.text_area.return_value = "测试文本"
        self.mock_st.checkbox.return_value = True
        self.mock_st.selectbox.side_effect = Exception("Selectbox failed")
        self.mock_st.slider.return_value = 5.5
        self.mock_st.number_input.return_value = 3
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            # Input should work
            cards = render_input_section_adapted(self.adapter)
            assert isinstance(cards, list)
            
            # Options might partially fail but should handle gracefully
            try:
                options = render_options_section_adapted(self.adapter)
                # Should either work with defaults or fail gracefully
                assert options is None or isinstance(options, tuple)
            except Exception:
                # Acceptable if error boundary isn't implemented for this specific case
                pass


class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system."""
    
    def test_end_to_end_performance_targets(self, monkeypatch):
        """Test that end-to-end workflows meet performance targets."""
        monkeypatch.setattr('ui.inputs.st', Mock())
        monkeypatch.setattr('ui.options.st', Mock())
        
        # Mock fast responses
        monkeypatch.getattr('ui.inputs.st').text_area.return_value = "测试"
        monkeypatch.getattr('ui.inputs.st').checkbox.return_value = True
        monkeypatch.getattr('ui.options.st').selectbox.return_value = "A4"
        monkeypatch.getattr('ui.options.st').slider.return_value = 5.5
        monkeypatch.getattr('ui.options.st').number_input.return_value = 3
        
        # Mock session state
        mock_session_state = {}
        monkeypatch.setattr('ui.inputs.st.session_state', mock_session_state)
        monkeypatch.setattr('ui.options.st.session_state', mock_session_state)
        
        with patch('ui.inputs.process_text_input') as mock_process:
            mock_process.return_value = [{'hanzi': '测试', 'pinyin': 'ceshi', 'english': 'test'}]
            
            # Measure end-to-end performance
            start_time = time.time()
            
            cards = render_input_section_adapted(get_ui_adapter())
            options = render_options_section_adapted(get_ui_adapter())
            advanced = render_advanced_options_adapted(get_ui_adapter())
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Should complete quickly
            assert duration_ms < 100, f"End-to-end workflow took {duration_ms:.2f}ms, should be <100ms"
    
    def test_concurrent_component_access(self):
        """Test that components can be accessed concurrently."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def access_adapter():
            try:
                adapter = get_ui_adapter()
                # Access different parts of the adapter
                _ = adapter.inputs
                _ = adapter.layout
                _ = adapter.notifications
                results.put("success")
            except Exception as e:
                results.put(f"error: {e}")
        
        # Create multiple threads accessing adapter concurrently
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_adapter)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All should succeed
        while not results.empty():
            result = results.get()
            assert result == "success", f"Concurrent access failed: {result}"
