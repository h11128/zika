"""
Unit tests for framework-agnostic table editor.
Tests apply flow, diff tracking, and UI adapter integration.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from ui.table_editor import (
    TableEditor, TableEditorConfig, EditSession, CardEdit,
    render_table_editor, use_table_editor
)
from services.card_models import Card, CardCollection
from ui.ports import UIAdapter, ComponentConfig, NotificationLevel


class MockUIAdapter:
    """Mock UI adapter for testing."""
    
    def __init__(self):
        self.inputs = MagicMock()
        self.layout = MagicMock()
        self.notifications = MagicMock()
        self.markdown = MagicMock()
        
        # Mock layout.columns to return context managers based on input
        def mock_columns(widths):
            return [MagicMock() for _ in widths]
        self.layout.columns.side_effect = mock_columns

        # Mock button clicks
        self.inputs.button.return_value = False
        self.inputs.text_input.return_value = ""


class TestEditSession:
    """Test edit session functionality."""
    
    def test_edit_session_initialization(self):
        """Test edit session initialization."""
        session = EditSession()
        
        assert session.edits == {}
        assert session.deleted_cards == set()
        assert session.added_cards == []
        assert not session.has_changes()
    
    def test_record_edit(self):
        """Test recording field edits."""
        session = EditSession()
        
        session.record_edit("card1", "hanzi", "老", "新")
        
        assert "card1" in session.edits
        assert "hanzi" in session.edits["card1"]
        
        edit = session.edits["card1"]["hanzi"]
        assert edit.card_id == "card1"
        assert edit.field == "hanzi"
        assert edit.old_value == "老"
        assert edit.new_value == "新"
        assert session.has_changes()
    
    def test_record_multiple_edits_same_card(self):
        """Test recording multiple edits for same card."""
        session = EditSession()
        
        session.record_edit("card1", "hanzi", "老", "新")
        session.record_edit("card1", "pinyin", "lao", "xin")
        
        assert len(session.edits["card1"]) == 2
        assert "hanzi" in session.edits["card1"]
        assert "pinyin" in session.edits["card1"]
    
    def test_record_deletion(self):
        """Test recording card deletions."""
        session = EditSession()
        
        # Add some edits first
        session.record_edit("card1", "hanzi", "老", "新")
        session.record_deletion("card1")
        
        assert "card1" in session.deleted_cards
        assert "card1" not in session.edits  # Edits should be removed
        assert session.has_changes()
    
    def test_record_addition(self):
        """Test recording card additions."""
        session = EditSession()
        
        new_card = Card.create_new("新", "xin", "new")
        session.record_addition(new_card)
        
        assert len(session.added_cards) == 1
        assert session.added_cards[0] == new_card
        assert session.has_changes()
    
    def test_get_change_summary(self):
        """Test change summary generation."""
        session = EditSession()
        
        # No changes
        assert session.get_change_summary() == "无更改"
        
        # Add various changes
        session.record_edit("card1", "hanzi", "老", "新")
        session.record_edit("card1", "pinyin", "lao", "xin")
        session.record_edit("card2", "english", "old", "new")
        session.record_deletion("card3")
        session.record_addition(Card.create_new("添", "tian", "add"))
        
        summary = session.get_change_summary()
        assert "3 个字段编辑" in summary
        assert "1 个卡片删除" in summary
        assert "1 个卡片添加" in summary
    
    def test_clear_session(self):
        """Test clearing edit session."""
        session = EditSession()
        
        # Add changes
        session.record_edit("card1", "hanzi", "老", "新")
        session.record_deletion("card2")
        session.record_addition(Card.create_new("添", "tian", "add"))
        
        assert session.has_changes()
        
        session.clear()
        
        assert not session.has_changes()
        assert session.edits == {}
        assert session.deleted_cards == set()
        assert session.added_cards == []


class TestTableEditorConfig:
    """Test table editor configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = TableEditorConfig()
        
        assert config.page_size == 15
        assert config.show_search is True
        assert config.show_pagination is True
        assert config.show_add_button is True
        assert config.show_delete_button is True
        assert config.editable is True
        assert config.enable_apply_flow is True
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = TableEditorConfig(
            page_size=10,
            show_search=False,
            editable=False,
            enable_apply_flow=False
        )
        
        assert config.page_size == 10
        assert config.show_search is False
        assert config.editable is False
        assert config.enable_apply_flow is False


class TestTableEditor:
    """Test table editor functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
        self.config = TableEditorConfig(page_size=5, enable_apply_flow=True)
        
        # Create test cards
        self.cards = [
            Card.create_new("一", "yi", "one"),
            Card.create_new("二", "er", "two"),
            Card.create_new("三", "san", "three")
        ]
        self.collection = CardCollection(self.cards)
    
    @patch('ui.table_editor.st')
    def test_table_editor_initialization(self, mock_st):
        """Test table editor initialization."""
        mock_st.session_state = MagicMock()
        mock_st.session_state.table_editor_session = EditSession()
        
        editor = TableEditor(self.adapter, self.config)
        
        assert editor.adapter == self.adapter
        assert editor.config == self.config
        assert isinstance(editor.edit_session, EditSession)
    
    @patch('ui.table_editor.st')
    @patch('ui.table_editor.use_stable_card_ids')
    def test_render_with_stable_ids(self, mock_use_stable_ids, mock_st):
        """Test rendering with stable card IDs."""
        mock_use_stable_ids.return_value = True
        mock_st.session_state = MagicMock()
        mock_st.session_state.table_editor_session = EditSession()
        
        editor = TableEditor(self.adapter, self.config)
        
        # Mock no pending changes
        editor.edit_session.has_changes = MagicMock(return_value=False)
        
        result_cards, needs_refresh = editor.render(self.collection)
        
        assert isinstance(result_cards, CardCollection)
        assert needs_refresh is False
    
    @patch('ui.table_editor.st')
    def test_record_edit_functionality(self, mock_st):
        """Test edit recording functionality."""
        mock_st.session_state = MagicMock()
        mock_st.session_state.table_editor_session = EditSession()
        
        editor = TableEditor(self.adapter, self.config)
        
        # Record an edit
        editor._record_edit("card1", "hanzi", "老", "新")
        
        assert editor.edit_session.has_changes()
        assert "card1" in editor.edit_session.edits
        assert editor.edit_session.edits["card1"]["hanzi"].new_value == "新"
    
    @patch('ui.table_editor.st')
    def test_apply_all_changes(self, mock_st):
        """Test applying all pending changes."""
        mock_st.session_state = MagicMock()
        mock_st.session_state.table_editor_session = EditSession()
        
        editor = TableEditor(self.adapter, self.config)
        
        # Add some changes
        card_id = self.cards[0].id
        editor.edit_session.record_edit(card_id, "hanzi", "一", "壹")
        editor.edit_session.record_edit(card_id, "english", "one", "ONE")
        editor.edit_session.record_deletion(self.cards[1].id)
        editor.edit_session.record_addition(Card.create_new("四", "si", "four"))
        
        # Mock CardCollection methods
        with patch.object(CardCollection, 'get_card') as mock_get_card, \
             patch.object(CardCollection, 'update_card') as mock_update, \
             patch.object(CardCollection, 'remove_card') as mock_remove, \
             patch.object(CardCollection, 'add_card') as mock_add:

            mock_get_card.return_value = self.cards[0]

            updated_cards = editor._apply_all_changes(self.collection)

            # Verify methods were called
            mock_get_card.assert_called()
            mock_update.assert_called()
            mock_remove.assert_called()
            mock_add.assert_called()


class TestTableEditorIntegration:
    """Test table editor integration functions."""
    
    @patch('ui.table_editor.get_feature_flag')
    def test_use_table_editor_flag(self, mock_get_flag):
        """Test table editor feature flag."""
        mock_get_flag.return_value = True
        assert use_table_editor() is True
        
        mock_get_flag.return_value = False
        assert use_table_editor() is False
        
        mock_get_flag.assert_called_with('table_editor', False)
    
    @patch('ui.table_editor.get_ui_adapter')
    def test_render_table_editor_function(self, mock_get_adapter):
        """Test render_table_editor convenience function."""
        mock_adapter = MockUIAdapter()
        mock_get_adapter.return_value = mock_adapter
        
        cards = CardCollection([Card.create_new("测", "ce", "test")])
        config = TableEditorConfig(page_size=10)
        
        with patch.object(TableEditor, 'render') as mock_render:
            mock_render.return_value = (cards, False)
            
            result_cards, needs_refresh = render_table_editor(cards, config)
            
            assert result_cards == cards
            assert needs_refresh is False
            mock_render.assert_called_once_with(cards)


class TestTableEditorApplyFlow:
    """Test table editor apply flow functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = MockUIAdapter()
        self.config = TableEditorConfig(enable_apply_flow=True)
        self.cards = [Card.create_new("测", "ce", "test")]
        self.collection = CardCollection(self.cards)
    
    @patch('ui.table_editor.st')
    def test_apply_flow_with_changes(self, mock_st):
        """Test apply flow when there are pending changes."""
        mock_st.session_state = MagicMock()
        session = EditSession()
        session.record_edit("card1", "hanzi", "老", "新")
        mock_st.session_state.table_editor_session = session
        
        editor = TableEditor(self.adapter, self.config)
        
        # Mock apply button click
        self.adapter.inputs.button.return_value = True
        
        with patch.object(editor, '_apply_all_changes') as mock_apply:
            mock_apply.return_value = self.collection
            
            needs_refresh = editor._render_apply_controls(self.collection)
            
            assert needs_refresh is True
            mock_apply.assert_called_once()
    
    @patch('ui.table_editor.st')
    def test_apply_flow_no_changes(self, mock_st):
        """Test apply flow when there are no pending changes."""
        mock_st.session_state = MagicMock()
        mock_st.session_state.table_editor_session = EditSession()
        
        editor = TableEditor(self.adapter, self.config)
        
        needs_refresh = editor._render_apply_controls(self.collection)
        
        assert needs_refresh is False


if __name__ == "__main__":
    pytest.main([__file__])
