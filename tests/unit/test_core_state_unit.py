from types import SimpleNamespace
import re
import builtins

import pytest

import core.state as cs


class SS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v


class DummySt:
    def __init__(self):
        self.session_state = SS()

    def error(self, *args, **kwargs):
        # noop for tests
        pass


def setup_dummy_st(monkeypatch):
    dummy = DummySt()
    monkeypatch.setattr(cs, "st", dummy)
    return dummy


def test_initialize_and_getters(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    cs.initialize_session_state()

    # Basic keys exist
    assert isinstance(st.session_state.dictionary, object)
    assert isinstance(st.session_state.export_history, list)
    assert st.session_state.total_cards_generated == 0

    # Getters return expected structure
    assert isinstance(cs.get_processed_cards(), list)
    assert isinstance(cs.get_layout_settings(), dict)
    assert isinstance(cs.get_ui_preferences(), dict)
    assert isinstance(cs.get_export_state(), dict)


def test_setters_and_param_change_flow(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    cs.initialize_session_state()

    # Set processed cards and source
    cards = [{"hanzi": "你", "pinyin": "ni3", "english": "you"}]
    cs.set_processed_cards(cards, source="test")
    assert cs.get_processed_cards() == cards

    # Paging
    cs.set_current_page(5)
    assert cs.get_current_page() == 5

    # Export state
    cs.set_export_ready("pdf", b"%PDF", "file.pdf")
    assert cs.is_export_ready("pdf")
    data = cs.get_export_data("pdf")
    assert data["filename"] == "file.pdf"

    # Param tracking
    params = cs.get_all_ui_params(5.5, 0.5, 1.0, "A4", 48, 18, 14, cards)
    changed = cs.handle_param_changes(params)
    assert changed is True
    # Re-applying same params should return False
    assert cs.handle_param_changes(params) is False


def test_update_layout_and_ui_preferences_and_validation(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    cs.initialize_session_state()

    # Update layout
    cs.update_layout_settings(layout_rows=4, layout_cols=5, layout_auto_fill=False)
    layout = cs.get_layout_settings()
    assert layout["layout_rows"] == 4 and layout["layout_cols"] == 5 and layout["layout_auto_fill"] is False

    # UI preferences
    cs.update_ui_preferences(hanzi_font_family="SimSun", background_color="#123456")
    prefs = cs.get_ui_preferences()
    assert prefs["hanzi_font_family"] == "SimSun"
    assert prefs["background_color"] == "#123456"

    # Invalid color should be reset by validation
    cs.update_ui_preferences(background_color="not-a-color")
    prefs = cs.get_ui_preferences()
    assert re.fullmatch(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})", prefs["background_color"]) is not None


def test_clear_helpers(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    cs.initialize_session_state()
    cs.set_export_ready("pptx", b"", "a.pptx")
    cs.clear_export_data()
    assert cs.get_export_data("pptx") == {}

    cs.set_processed_cards([{"hanzi": "你", "pinyin": "ni3", "english": "you"}], source="x")
    cs.clear_processed_cards()
    assert cs.get_processed_cards() == []

