"""
Comprehensive tests for core state management related to preview functionality.
Tests parameter change detection, state persistence, and preview optimization.
"""

import pytest
from unittest.mock import patch, MagicMock
import streamlit as st


class TestCoreStatePreview:
    """Test core state management for preview functionality."""

    def setup_method(self):
        """Setup test environment."""
        # Clear any existing session state
        if hasattr(st, 'session_state'):
            for key in list(st.session_state.keys()):
                del st.session_state[key]

    def test_check_params_changed_first_time(self):
        """Test parameter change detection on first run."""
        from core.state import check_params_changed

        with patch('core.state.st') as mock_st:
            # Mock session state with no previous params
            mock_st.session_state = MagicMock()
            mock_st.session_state.get.return_value = None  # No last_params set

            # Provide current params
            current = {'card_size_cm': 5.5}
            result = check_params_changed(current)

            # Should return True on first run (no previous params)
            assert result is True

    def test_check_params_changed_params_different(self):
        """Test parameter change detection when params are different."""
        from core.state import check_params_changed

        with patch('core.state.st') as mock_st:
            # Mock session state with different previous params
            mock_st.session_state = MagicMock()
            # Set the last_params attribute (used by _ss_get)
            mock_st.session_state.last_params = {
                'card_size_cm': 5.0,  # Previous
                'background_color': '#ffffff'
            }

            current = {
                'card_size_cm': 5.5,  # Current value
                'background_color': '#ffffff'
            }

            result = check_params_changed(current)

            # Should return True when params are different
            assert result is True

    def test_check_params_changed_params_same(self):
        """Test parameter change detection when params are the same."""
        from core.state import check_params_changed

        with patch('core.state.st') as mock_st:
            # Mock session state with same previous params
            current_params = {
                'card_size_cm': 5.5,
                'background_color': '#ffffff',
                'hanzi_font_size': 48
            }

            mock_st.session_state = MagicMock()
            mock_st.session_state.last_params = current_params.copy()

            result = check_params_changed(current_params)

            # Should return False when params are the same
            assert result is False

    def test_get_all_ui_params_complete(self):
        """Test getting all UI parameters."""
        from core.state import get_all_ui_params

        with patch('core.state.st') as mock_st:
            # Mock session state with all parameters using attributes (used by _ss_get/getattr)
            mock_st.session_state = MagicMock()
            mock_st.session_state.hanzi_font_family = 'SimHei'
            mock_st.session_state.background_color = '#ffffff'
            mock_st.session_state.layout_rows = 2
            mock_st.session_state.layout_cols = 3
            mock_st.session_state.layout_auto_fill = True

            params = get_all_ui_params(
                card_size_cm=5.5,
                gap_cm=0.5,
                margin_cm=1.0,
                page_size='A4',
                hanzi_font_size=48,
                pinyin_font_size=18,
                english_font_size=14,
                processed_cards=[{'hanzi': '你', 'pinyin': 'ni3', 'english': 'you'}],
                preview_mode='📄 完整页面'
            )

            # Should return all expected parameters
            expected_keys = [
                'card_size_cm', 'gap_cm', 'margin_cm', 'hanzi_font_size', 'pinyin_font_size',
                'english_font_size', 'page_size', 'hanzi_font_family', 'background_color',
                'layout_rows', 'layout_cols', 'layout_auto_fill', 'total_cards', 'preview_mode'
            ]

            for key in expected_keys:
                assert key in params

            # Check specific values
            assert params['card_size_cm'] == 5.5
            assert params['hanzi_font_size'] == 48
            assert params['background_color'] == '#ffffff'
            assert params['total_cards'] == 1
            assert params['preview_mode'] == '📄 完整页面'

    def test_get_all_ui_params_with_defaults(self):
        """Test getting UI parameters with default values."""
        from core.state import get_all_ui_params

        with patch('core.state.st') as mock_st:
            # Mock session state with missing parameters (should use defaults)
            mock_st.session_state = MagicMock()

            params = get_all_ui_params(
                card_size_cm=5.5,
                gap_cm=0.5,
                margin_cm=1.0,
                page_size='A4',
                hanzi_font_size=48,
                pinyin_font_size=18,
                english_font_size=14,
                processed_cards=[],
                preview_mode=None
            )

            # Should return parameters dictionary
            assert isinstance(params, dict)
            # Check that totals derived are reasonable
            assert params['total_cards'] == 0
            assert 'layout_rows' in params and 'layout_cols' in params and 'layout_auto_fill' in params

    def test_set_current_page(self):
        """Test setting current page."""
        from core.state import set_current_page

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()

            set_current_page(2)

            # Should call assignment with bounded page >= 0
            assert mock_st.session_state.current_page == 2

    def test_get_current_page_exists(self):
        """Test getting current page when it exists."""
        from core.state import get_current_page

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()
            mock_st.session_state.current_page = 3

            page = get_current_page()

            # Should return the stored page
            assert page == 3

    def test_get_current_page_default(self):
        """Test getting current page with default value."""
        from core.state import get_current_page

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()
            # Simulate default initialized value
            mock_st.session_state.current_page = 0

            page = get_current_page()

            # Should return default value (0)
            assert page == 0

    def test_get_processed_cards_exists(self):
        """Test getting processed cards when they exist."""
        from core.state import get_processed_cards

        with patch('core.state.st') as mock_st:
            test_cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]
            mock_st.session_state = MagicMock()
            mock_st.session_state.processed_cards = test_cards

            cards = get_processed_cards()

            # Should return the stored cards
            assert cards == test_cards

    def test_get_processed_cards_default(self):
        """Test getting processed cards with default value."""
        from core.state import get_processed_cards

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()
            # Mimic default initialized value
            mock_st.session_state.processed_cards = []

            cards = get_processed_cards()

            # Should return empty list by default initialize
            assert cards == []

    def test_set_processed_cards(self):
        """Test setting processed cards."""
        from core.state import set_processed_cards

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()
            test_cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

            set_processed_cards(test_cards)

            # Should set processed_cards in session state
            assert mock_st.session_state.processed_cards == test_cards

    def test_parameter_change_detection_edge_cases(self):
        """Test parameter change detection edge cases."""
        from core.state import check_params_changed

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()

            # Test with None vs empty dict
            mock_st.session_state.get.return_value = None

            result = check_params_changed({})
            assert result is True  # None != {}

            # Test with empty dict vs empty dict
            mock_st.session_state.last_params = {}
            result = check_params_changed({})
            assert result is False  # {} == {}

    def test_state_persistence_across_reruns(self):
        """Test that state persists correctly across reruns."""
        from core.state import set_current_page, get_current_page, set_processed_cards, get_processed_cards

        with patch('core.state.st') as mock_st:
            # Simulate persistent session state
            persistent_state = {}
            mock_st.session_state = MagicMock()

            def mock_get(key, default=None):
                return persistent_state.get(key, default)

            mock_st.session_state.get.side_effect = mock_get

            # Set values
            set_current_page(5)
            persistent_state['current_page'] = 5  # Simulate persistence

            test_cards = [{'hanzi': '测试', 'pinyin': 'ce4shi4', 'english': 'test'}]
            set_processed_cards(test_cards)
            persistent_state['processed_cards'] = test_cards  # Simulate persistence

            # Get values (simulating new run)
            page = get_current_page()
            cards = get_processed_cards()

            # Should retrieve persisted values
            assert page == 5
            assert cards == test_cards

    def test_preview_optimization_flags(self):
        """Test preview optimization flags and caching behavior."""
        from core.state import check_params_changed, update_last_params

        with patch('core.state.st') as mock_st:
            mock_st.session_state = MagicMock()

            # Test that last_params is updated after check
            current_params = {'card_size_cm': 5.5, 'background_color': '#ffffff'}
            mock_st.session_state.get.return_value = None  # First time

            result = check_params_changed(current_params)

            # Should return True
            assert result is True
            # Update last params and verify
            update_last_params(current_params)
            assert mock_st.session_state.last_params == current_params

    def test_font_size_parameter_tracking(self):
        """Test that font size parameters are properly tracked for preview updates."""
        from core.state import check_params_changed

        with patch('core.state.st') as mock_st:
            # Test font size changes trigger preview updates
            mock_st.session_state = MagicMock()

            # Previous params with different font sizes
            mock_st.session_state.get.return_value = {
                'hanzi_font_size': 48,
                'pinyin_font_size': 18,
                'english_font_size': 14
            }

            # Current params with changed font sizes
            current = {
                'hanzi_font_size': 26,  # Changed
                'pinyin_font_size': 12,  # Changed
                'english_font_size': 14  # Same
            }

            result = check_params_changed(current)

            # Should detect font size changes
            assert result is True
