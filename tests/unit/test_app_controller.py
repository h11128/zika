"""
Tests for the application controller in ui/app_controller.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from ui.app_controller import AppController


class TestAppController:
    """Test AppController class."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock streamlit functions to avoid runtime errors."""
        with patch.multiple(
            'streamlit',
            set_page_config=Mock(),
            title=Mock(),
            markdown=Mock(),
            error=Mock(),
            info=Mock(),
            columns=Mock(return_value=[Mock(), Mock()]),
            session_state=Mock()
        ):
            yield
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies."""
        with patch.multiple(
            'ui.app_controller',
            apply_global_styles=Mock(),
            initialize_session_state=Mock(),
            render_sidebar=Mock(),
            render_left_column=Mock(return_value={
                'cards': [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}],
                'auto_pinyin': True,
                'auto_translate': True,
                'page_size': 'A4',
                'card_size_cm': 5.5,
                'gap_cm': 0.5,
                'margin_cm': 1.0,
                'hanzi_font_size': 48,
                'pinyin_font_size': 18,
                'english_font_size': 14
            }),
            render_preview_column_header=Mock(return_value={
                'hanzi_font_family': 'SimHei',
                'background_color': '#ffffff',
                'preview_mode': '📄 完整页面'
            }),
            render_preview_content_legacy=Mock(return_value=(6, 1)),
            render_export_section=Mock(),
            render_sticky_wrapper_end=Mock(),
            get_processed_cards=Mock(return_value=[]),
            get_all_ui_params=Mock(return_value={}),
            handle_param_changes=Mock(return_value=False),
            generate_missing_data=Mock(return_value=[]),
            set_processed_cards=Mock(),
            clear_export_data=Mock(),
            clear_processed_cards=Mock(),
            get_dictionary=Mock(return_value={})
        ):
            yield
    
    def test_controller_initialization(self, mock_streamlit, mock_dependencies):
        """Test AppController initialization."""
        controller = AppController()
        assert controller is not None
    
    def test_setup_app(self, mock_streamlit, mock_dependencies):
        """Test setup_app method."""
        controller = AppController()
        controller.setup_app()
        # Verify that setup functions were called
        # (mocked functions don't need assertion as they're already called in __init__)
    
    def test_render_header(self, mock_streamlit, mock_dependencies):
        """Test render_header method."""
        controller = AppController()
        controller.render_header()
        # Verify streamlit functions were called
        st.title.assert_called()
        st.markdown.assert_called()
    
    def test_should_reprocess_cards_with_valid_session(self, mock_streamlit, mock_dependencies):
        """Test should_reprocess_cards with valid session state."""
        with patch('ui.app_controller.get_processed_cards', return_value=[{'hanzi': '你好'}]):
            with patch('ui.app_controller.st.session_state') as mock_session:
                mock_session.cards_source = 'test_source'
                
                controller = AppController()
                cards = [{'hanzi': '你好'}]
                current_source = 'test_source'
                
                result = controller.should_reprocess_cards(cards, current_source)
                assert result is False  # Should not reprocess if source matches
    
    def test_should_reprocess_cards_with_different_source(self, mock_streamlit, mock_dependencies):
        """Test should_reprocess_cards with different source."""
        with patch('ui.app_controller.get_processed_cards', return_value=[{'hanzi': '你好'}]):
            with patch('ui.app_controller.st.session_state') as mock_session:
                mock_session.cards_source = 'old_source'
                
                controller = AppController()
                cards = [{'hanzi': '你好'}]
                current_source = 'new_source'
                
                result = controller.should_reprocess_cards(cards, current_source)
                assert result is True  # Should reprocess if source differs
    
    def test_should_reprocess_cards_error_handling(self, mock_streamlit, mock_dependencies):
        """Test should_reprocess_cards error handling."""
        with patch('ui.app_controller.get_processed_cards', side_effect=Exception("Test error")):
            controller = AppController()
            cards = [{'hanzi': '你好'}]
            current_source = 'test_source'
            
            result = controller.should_reprocess_cards(cards, current_source)
            assert result is True  # Should force reprocessing on error
            st.error.assert_called()
    
    def test_process_cards_if_needed_empty_cards(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed with empty cards."""
        controller = AppController()
        result = controller.process_cards_if_needed([], True, True)
        assert result == []
    
    def test_process_cards_if_needed_invalid_input(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed with invalid input."""
        controller = AppController()
        result = controller.process_cards_if_needed("not a list", True, True)
        assert result == []
    
    def test_process_cards_if_needed_with_cards(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed with valid cards."""
        test_cards = [{'hanzi': '你好', 'pinyin': '', 'english': ''}]
        processed_cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
        
        with patch.object(AppController, 'should_reprocess_cards', return_value=True):
            with patch('ui.app_controller.generate_missing_data', return_value=processed_cards):
                controller = AppController()
                result = controller.process_cards_if_needed(test_cards, True, True)
                assert len(result) == 1
                assert result[0]['hanzi'] == '你好'
    
    def test_process_cards_error_handling(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed error handling."""
        test_cards = [{'hanzi': '你好'}]
        
        with patch.object(AppController, 'should_reprocess_cards', return_value=True):
            with patch('ui.app_controller.generate_missing_data', side_effect=Exception("Test error")):
                controller = AppController()
                result = controller.process_cards_if_needed(test_cards, True, True)
                # Should return basic cards on error
                assert len(result) == 1
                st.error.assert_called()
    
    def test_calculate_pagination(self, mock_streamlit, mock_dependencies):
        """Test calculate_pagination method."""
        test_cards = [{'hanzi': f'卡片{i}'} for i in range(10)]
        
        with patch('ui.app_controller.get_layout_settings', return_value={'layout_rows': 2, 'layout_cols': 3}):
            with patch('ui.app_controller.get_current_page', return_value=0):
                controller = AppController()
                pagination_info = controller.calculate_pagination(test_cards, {'layout_rows': 2, 'layout_cols': 3})
                cards_per_page, total_pages = pagination_info.cards_per_page, pagination_info.total_pages
                
                assert cards_per_page == 6  # 2 * 3
                assert total_pages == 2     # ceil(10 / 6)
    
    def test_calculate_pagination_page_reset(self, mock_streamlit, mock_dependencies):
        """Test calculate_pagination with page reset."""
        test_cards = [{'hanzi': '卡片1'}]
        
        with patch('ui.app_controller.get_layout_settings', return_value={'layout_rows': 2, 'layout_cols': 3}):
            with patch('ui.app_controller.get_current_page', return_value=5):  # Out of range
                with patch('ui.app_controller.set_current_page') as mock_set_page:
                    controller = AppController()
                    controller.calculate_pagination(test_cards, {'layout_rows': 2, 'layout_cols': 3})
                    
                    mock_set_page.assert_called_with(0)  # Should reset to page 0

    def test_app_controller_setup(self, mock_streamlit, mock_dependencies):
        """Test AppController setup method."""
        controller = AppController()
        # Should initialize without errors
        assert controller is not None

    def test_app_controller_render_header(self, mock_streamlit, mock_dependencies):
        """Test AppController header rendering."""
        controller = AppController()
        controller.render_header()

        # Should call streamlit title and markdown
        st.title.assert_called_with("🀄 Chinese Learning Cards Generator")
        assert st.markdown.call_count >= 2

    def test_app_controller_should_reprocess_cards(self, mock_streamlit, mock_dependencies):
        """Test should_reprocess_cards method."""
        with patch('ui.app_controller.get_processed_cards') as mock_get_cards:
            mock_get_cards.return_value = []

            controller = AppController()
            cards = [{'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'}]
            result = controller.should_reprocess_cards(cards, 'test_source')

            # Should return boolean
            assert isinstance(result, bool)

    def test_app_controller_process_cards_if_needed_with_translation_order(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed with different translation orders."""
        with patch('ui.app_controller.generate_missing_data_ordered') as mock_ordered, \
             patch('ui.app_controller.generate_missing_data') as mock_regular, \
             patch('ui.app_controller.get_dictionary') as mock_dict, \
             patch('ui.app_controller.set_processed_cards') as mock_set:

            mock_ordered.return_value = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]
            mock_regular.return_value = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]
            mock_dict.return_value = {}

            controller = AppController()
            cards = [{'hanzi': '你好', 'pinyin': '', 'english': ''}]

            # Test with API-first translation order
            result = controller.process_cards_if_needed(cards, True, True, 'api_first')

            # Should use ordered generation
            mock_ordered.assert_called_once()
            assert len(result) == 1

    def test_app_controller_process_cards_if_needed_error_handling(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed error handling."""
        with patch('ui.app_controller.generate_missing_data') as mock_generate:
            mock_generate.side_effect = Exception("Processing error")

            controller = AppController()
            cards = [{'hanzi': '你好', 'pinyin': '', 'english': ''}]

            result = controller.process_cards_if_needed(cards, True, True, 'local_first')

            # Should handle error gracefully and return original cards
            assert len(result) == 1
            assert result[0]['hanzi'] == '你好'
            st.error.assert_called()

    def test_app_controller_calculate_pagination(self, mock_streamlit, mock_dependencies):
        """Test pagination calculation."""
        with patch('ui.app_controller.get_current_page') as mock_get_page, \
             patch('ui.app_controller.set_current_page') as mock_set_page:

            mock_get_page.return_value = 5  # Out of range page

            controller = AppController()
            cards = [{'hanzi': f'字{i}', 'pinyin': f'zi{i}', 'english': f'word{i}'} for i in range(10)]
            layout = {'layout_rows': 2, 'layout_cols': 3}  # 6 cards per page

            pagination_info = controller.calculate_pagination(cards, layout)
            cards_per_page, total_pages = pagination_info.cards_per_page, pagination_info.total_pages

            # Should calculate correct pagination
            assert cards_per_page == 6
            assert total_pages == 2  # 10 cards / 6 per page = 2 pages
            # Should reset page to 0 when out of range
            mock_set_page.assert_called_with(0)

    def test_app_controller_render_card_editor_empty(self, mock_streamlit, mock_dependencies):
        """Test card editor with empty cards."""
        controller = AppController()

        # Should handle empty cards gracefully
        controller.render_card_editor([], 6)

        # Should not crash or show editor

    def test_app_controller_render_card_editor_with_cards(self, mock_streamlit, mock_dependencies):
        """Test card editor with actual cards."""
        with patch('ui.app_controller.render_improved_card_editor') as mock_editor:
            controller = AppController()
            cards = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]

            controller.render_card_editor(cards, 6)

            # Should call the improved editor
            mock_editor.assert_called_once_with(cards)

    def test_app_controller_process_cards_if_needed_local_first_fallback(self, mock_streamlit, mock_dependencies):
        """Test process_cards_if_needed with local_first translation order fallback."""
        with patch('ui.app_controller.generate_missing_data') as mock_regular, \
             patch('ui.app_controller.get_dictionary') as mock_dict, \
             patch('ui.app_controller.set_processed_cards') as mock_set:

            mock_regular.return_value = [{'hanzi': '你好', 'pinyin': 'ni3hao3', 'english': 'hello'}]
            mock_dict.return_value = {}

            controller = AppController()
            cards = [{'hanzi': '你好', 'pinyin': '', 'english': ''}]

            # Test with local_first (should use regular generation)
            result = controller.process_cards_if_needed(cards, True, True, 'local_first')

            # Should use regular generation for local_first
            mock_regular.assert_called_once()
            assert len(result) == 1


if __name__ == '__main__':
    pytest.main([__file__])
