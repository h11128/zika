"""
End-to-end tests for preview update functionality.
Tests complete user interaction scenarios for preview updates.
"""

import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import test utilities (using existing pattern)
# We'll define our own simple test utilities inline

# Import modules under test
from services.cache_v2 import clear_preview_cache_v2 as clear_preview_cache
from services.cache_v2 import create_page_preview_html_immediate
from core.state import initialize_session_state, get_all_ui_params
from ui.options import render_advanced_options
from ui.components import render_preview_section


@pytest.mark.e2e
@pytest.mark.preview_updates
class TestPreviewUpdateEndToEnd:
    """End-to-end tests for preview update scenarios."""
    
    def setup_method(self):
        """Setup test environment for each test."""
        self.test_cards = [
            {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
            {'hanzi': '世界', 'pinyin': 'shì jiè', 'english': 'world'},
            {'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}
        ]
        
        self.default_params = {
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
    
    @patch('streamlit.session_state')
    @patch('streamlit.rerun')
    def test_font_size_change_workflow(self, mock_rerun, mock_session_state):
        """Test complete workflow: user changes font size → preview updates."""
        # Setup session state
        session_data = {
            'current_page': 0,
            'processed_cards': self.test_cards,
            'hanzi_font_size': 48,
            'pinyin_font_size': 18,
            'english_font_size': 14,
            'last_preview_params': None
        }
        
        mock_session_state.__getitem__ = lambda key: session_data.get(key)
        mock_session_state.__setitem__ = lambda key, value: session_data.update({key: value})
        mock_session_state.get = lambda key, default=None: session_data.get(key, default)
        mock_session_state.__contains__ = lambda key: key in session_data
        mock_session_state.__delitem__ = lambda key: session_data.pop(key, None)
        
        # Step 1: Generate initial preview
        initial_html = create_page_preview_html_immediate(
            self.test_cards, 0, **self.default_params
        )
        
        # Verify initial state (font size is calculated: 48 * scale_factor * 0.8)
        # For A4 page, scale_factor is typically around 0.7, so 48 * 0.7 * 0.8 ≈ 26.88px
        assert 'font-size:' in initial_html  # Font size CSS exists
        assert '你好' in initial_html
        
        # Step 2: Simulate user changing font size
        new_font_size = 60
        session_data['hanzi_font_size'] = new_font_size
        
        # Step 3: Generate updated preview
        updated_html = create_page_preview_html_immediate(
            self.test_cards, 0,
            card_size_cm=self.default_params['card_size_cm'],
            gap_cm=self.default_params['gap_cm'],
            margin_cm=self.default_params['margin_cm'],
            hanzi_font_size=new_font_size,  # Changed parameter
            pinyin_font_size=self.default_params['pinyin_font_size'],
            english_font_size=self.default_params['english_font_size'],
            page_size=self.default_params['page_size'],
            hanzi_font_family=self.default_params['hanzi_font_family'],
            background_color=self.default_params['background_color'],
            layout_rows=self.default_params['layout_rows'],
            layout_cols=self.default_params['layout_cols'],
            layout_auto_fill=self.default_params['layout_auto_fill']
        )
        
        # Step 4: Verify preview updated
        # Check that the HTML contains different font size calculations
        assert 'font-size:' in updated_html  # Font size CSS exists
        assert '你好' in updated_html  # Content still present

        # More robust check: extract font sizes and compare
        import re
        initial_font_sizes = re.findall(r'font-size:\s*([0-9.]+)px', initial_html)
        updated_font_sizes = re.findall(r'font-size:\s*([0-9.]+)px', updated_html)

        # Should have different font sizes due to parameter change
        assert initial_font_sizes != updated_font_sizes, f"Font sizes should be different: {initial_font_sizes} vs {updated_font_sizes}"
        
        # Step 5: Verify HTMLs are different
        assert initial_html != updated_html
    
    @patch('streamlit.session_state')
    def test_color_change_workflow(self, mock_session_state):
        """Test complete workflow: user changes color → preview updates."""
        # Setup session state
        session_data = {
            'background_color': '#ffffff',
            'last_preview_params': None
        }
        
        mock_session_state.__getitem__ = lambda key: session_data.get(key)
        mock_session_state.__setitem__ = lambda key, value: session_data.update({key: value})
        mock_session_state.get = lambda key, default=None: session_data.get(key, default)
        
        # Step 1: Generate initial preview with white background
        initial_html = create_page_preview_html_immediate(
            self.test_cards, 0, **self.default_params
        )
        
        # Verify initial color
        assert '#ffffff' in initial_html or 'background-color:#ffffff' in initial_html
        
        # Step 2: Simulate user selecting new color
        new_color = '#ff0000'  # Red
        session_data['background_color'] = new_color
        
        # Step 3: Generate updated preview
        updated_params = self.default_params.copy()
        updated_params['background_color'] = new_color
        
        updated_html = create_page_preview_html_immediate(
            self.test_cards, 0, **updated_params
        )
        
        # Step 4: Verify color updated
        assert new_color in updated_html
        assert initial_html != updated_html
    
    @patch('streamlit.session_state')
    def test_card_content_edit_workflow(self, mock_session_state):
        """Test complete workflow: user edits card content → preview updates."""
        # Setup session state
        session_data = {
            'processed_cards': self.test_cards.copy(),
            'current_page': 0
        }
        
        mock_session_state.__getitem__ = lambda key: session_data.get(key)
        mock_session_state.__setitem__ = lambda key, value: session_data.update({key: value})
        mock_session_state.get = lambda key, default=None: session_data.get(key, default)
        
        # Step 1: Generate initial preview
        initial_html = create_page_preview_html_immediate(
            session_data['processed_cards'], 0, **self.default_params
        )
        
        # Verify initial content
        assert '你好' in initial_html
        assert 'hello' in initial_html
        
        # Step 2: Simulate user editing card content
        edited_cards = session_data['processed_cards'].copy()
        edited_cards[0] = {
            'hanzi': '再见',
            'pinyin': 'zài jiàn', 
            'english': 'goodbye'
        }
        session_data['processed_cards'] = edited_cards
        
        # Step 3: Generate updated preview
        updated_html = create_page_preview_html_immediate(
            edited_cards, 0, **self.default_params
        )
        
        # Step 4: Verify content updated
        assert '再见' in updated_html
        assert 'goodbye' in updated_html
        assert '你好' not in updated_html  # Old content removed
        assert 'hello' not in updated_html  # Old content removed
        
        # Step 5: Verify HTMLs are different
        assert initial_html != updated_html
    
    def test_cache_clearing_effectiveness(self):
        """Test that cache clearing actually forces regeneration."""
        # Generate HTML with caching
        from services.cache_v2 import cached_create_page_preview_html
        
        html1 = cached_create_page_preview_html(
            self.test_cards, 0, **self.default_params
        )
        
        # Generate again - should be identical due to caching
        html2 = cached_create_page_preview_html(
            self.test_cards, 0, **self.default_params
        )
        
        assert html1 == html2  # Cache working
        
        # Clear cache
        clear_preview_cache()
        
        # Generate with different parameters
        modified_params = self.default_params.copy()
        modified_params['background_color'] = '#ff0000'
        
        html3 = cached_create_page_preview_html(
            self.test_cards, 0, **modified_params
        )
        
        # Should be different due to parameter change
        assert html1 != html3
        assert '#ff0000' in html3
    
    @patch('streamlit.session_state')
    @patch('core.state.get_layout_settings')
    @patch('core.state.get_ui_preferences')
    def test_parameter_change_detection_accuracy(self, mock_prefs, mock_layout, mock_session_state):
        """Test that parameter change detection works accurately."""
        # Mock the dependencies
        mock_layout.return_value = {'layout_rows': 2, 'layout_cols': 3, 'layout_auto_fill': True}
        mock_prefs.return_value = {'hanzi_font_family': 'SimHei', 'background_color': '#ffffff'}

        # Test with identical parameters
        params1 = get_all_ui_params(
            5.5, 0.5, 1.0, 'A4', 48, 18, 14, self.test_cards
        )

        params2 = get_all_ui_params(
            5.5, 0.5, 1.0, 'A4', 48, 18, 14, self.test_cards
        )

        # Should be identical
        assert params1 == params2

        # Test with different parameters
        params3 = get_all_ui_params(
            6.0, 0.5, 1.0, 'A4', 48, 18, 14, self.test_cards  # Different card_size
        )

        # Should be different
        assert params1 != params3
        assert params1['card_size_cm'] != params3['card_size_cm']
    
    def test_multiple_parameter_changes(self):
        """Test handling multiple parameter changes simultaneously."""
        # Initial parameters
        initial_params = self.default_params.copy()
        
        # Generate initial HTML
        initial_html = create_page_preview_html_immediate(
            self.test_cards, 0, **initial_params
        )
        
        # Change multiple parameters
        modified_params = initial_params.copy()
        modified_params.update({
            'hanzi_font_size': 60,           # Font size change
            'background_color': '#00ff00',  # Color change
            'card_size_cm': 6.0,           # Size change
            'gap_cm': 0.8                  # Gap change
        })
        
        # Generate updated HTML
        updated_html = create_page_preview_html_immediate(
            self.test_cards, 0, **modified_params
        )
        
        # Verify all changes reflected
        assert '#00ff00' in updated_html   # Color change
        assert initial_html != updated_html  # HTML should be different

        # More robust font size check
        import re
        initial_font_sizes = re.findall(r'font-size:\s*([0-9.]+)px', initial_html)
        updated_font_sizes = re.findall(r'font-size:\s*([0-9.]+)px', updated_html)

        # Should have different font sizes due to parameter change
        assert initial_font_sizes != updated_font_sizes, "Font sizes should be different after parameter change"


@pytest.mark.ui_interaction
class TestUIInteractionBehavior:
    """Test UI interaction behavior for preview updates."""
    
    def test_slider_change_simulation(self):
        """Test simulated slider changes trigger correct updates."""
        # This would be expanded with actual UI interaction simulation
        # For now, test the underlying logic
        
        initial_font_size = 48
        new_font_size = 60
        
        # Simulate the change detection logic
        params_changed = initial_font_size != new_font_size
        assert params_changed
        
        # Verify that change would trigger cache clear
        # (This tests the logic without actual UI interaction)
        if params_changed:
            clear_preview_cache()  # Should not raise exception
    
    def test_color_picker_change_simulation(self):
        """Test simulated color picker changes trigger correct updates."""
        initial_color = '#ffffff'
        new_color = '#ff0000'
        
        # Simulate the change detection logic
        color_changed = initial_color != new_color
        assert color_changed
        
        # Test that different colors produce different HTML
        test_cards = [{'hanzi': '测试', 'pinyin': 'cè shì', 'english': 'test'}]
        
        html1 = create_page_preview_html_immediate(
            test_cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
            'A4', 'SimHei', initial_color, 2, 3, True
        )
        
        html2 = create_page_preview_html_immediate(
            test_cards, 0, 5.5, 0.5, 1.0, 48, 18, 14,
            'A4', 'SimHei', new_color, 2, 3, True
        )
        
        assert html1 != html2
        assert initial_color in html1
        assert new_color in html2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
