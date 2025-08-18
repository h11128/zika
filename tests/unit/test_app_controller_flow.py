import types
import ui.app_controller as ac


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
        self.session_state.cards_source = None
        self.session_state.export_ready = {}
        self.session_state.export_data = {}
        self.session_state.export_history = []
        self.session_state.total_cards_generated = 0

    def title(self, *a, **k):
        pass

    def markdown(self, *a, **k):
        pass

    class _ColCtx:
        def __init__(self, parent):
            self._parent = parent
        def __enter__(self):
            return self._parent
        def __exit__(self, exc_type, exc, tb):
            return False

    def columns(self, spec):
        # Return as many context-managing columns as requested
        n = spec if isinstance(spec, int) else (len(spec) if hasattr(spec, '__len__') else 3)
        return tuple(DummySt._ColCtx(self) for _ in range(n))

    def error(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    # Needed by render_card_editor
    class _Ctx:
        def __enter__(self):
            return DummySt()
        def __exit__(self, exc_type, exc, tb):
            return False

    def expander(self, *a, **k):
        return DummySt._Ctx()

    class _TabCtx:
        def __enter__(self):
            return DummySt()
        def __exit__(self, exc_type, exc, tb):
            return False

    def tabs(self, labels):
        # Return context managers for each tab
        return [DummySt._TabCtx() for _ in labels]

    def text_input(self, *a, **k):
        # return provided default value when present
        return k.get("value", "")

    def write(self, *a, **k):
        pass


def setup_dummy_st(monkeypatch):
    dummy = DummySt()
    monkeypatch.setattr(ac, "st", dummy)
    return dummy


def test_process_cards_if_needed_reprocess_and_error(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    ctrl = ac.AppController()

    # Patch dependencies used in controller
    monkeypatch.setattr(ac, "apply_global_styles", lambda: None)
    monkeypatch.setattr(ac, "initialize_session_state", lambda: None)
    monkeypatch.setattr(ac, "get_processed_cards", lambda: [])
    monkeypatch.setattr(ac, "clear_export_data", lambda: None)
    monkeypatch.setattr(ac, "set_processed_cards", lambda *a, **k: None)
    monkeypatch.setattr(ac, "get_dictionary", lambda: types.SimpleNamespace(lookup_translation=lambda x: "t"))

    # generate_missing_data returns processed data
    monkeypatch.setattr(ac, "generate_missing_data", lambda cards, ap, at, d: [{"hanzi": c['hanzi'], "pinyin": "p", "english": "e"} for c in cards])

    cards = [{"hanzi": "你", "pinyin": "", "english": ""}]
    result = ctrl.process_cards_if_needed(cards, True, True)
    assert result and result[0]["pinyin"] == "p"

    # Make generate_missing_data raise -> fallback to basic_cards
    monkeypatch.setattr(ac, "generate_missing_data", lambda *a, **k: (_ for _ in ()).throw(Exception("boom")))
    result = ctrl.process_cards_if_needed(cards, True, True)
    assert result and result[0]["hanzi"] == "你" and result[0]["pinyin"] == "" and result[0]["english"] == ""


def test_calculate_pagination_resets_when_out_of_range(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    ctrl = ac.AppController()
    monkeypatch.setattr(ac, "get_current_page", lambda: 5)
    called = {"reset": False}
    monkeypatch.setattr(ac, "set_current_page", lambda p: called.__setitem__("reset", True))

    cards_per_page, total_pages = ctrl.calculate_pagination([{}]*3, {"rows": 1, "cols": 2})
    assert cards_per_page == 2 and total_pages == 2
    assert called["reset"] is True


def test_render_right_column_content_paths(monkeypatch):
    st = setup_dummy_st(monkeypatch)
    ctrl = ac.AppController()

    # Patch left params and dependencies
    left_params = {
        'cards': [{"hanzi": "你", "pinyin": "", "english": ""}],
        'auto_pinyin': True,
        'auto_translate': True,
        'page_size': 'A4',
        'card_size': 5.5,
        'gap': 0.5,
        'margin': 1.0,
        'font_hanzi': 48,
        'font_pinyin': 18,
        'font_english': 14,
    }

    monkeypatch.setattr(ac, "render_preview_column_header", lambda: {"hanzi_font": "SimHei", "background_color": "#fff", "preview_mode": "📄 完整页面"})
    monkeypatch.setattr(ac, "get_all_ui_params", lambda *a, **k: {"rows": 2, "cols": 3, "auto_fill": True, "background_color": "#fff", "hanzi_font": "SimHei", "total_cards": 1, "card_size": 5.5, "gap": 0.5, "margin": 1.0, "page_size": 'A4', "font_hanzi": 48, "font_pinyin": 18, "font_english": 14})
    monkeypatch.setattr(ac, "handle_param_changes", lambda p: None)
    monkeypatch.setattr(ac, "render_preview_content_legacy", lambda *a, **k: (6, 1))
    monkeypatch.setattr(ac, "render_sticky_wrapper_end", lambda: None)

    # Process cards path
    monkeypatch.setattr(ac, "get_processed_cards", lambda: [])
    monkeypatch.setattr(ac, "set_processed_cards", lambda *a, **k: None)
    monkeypatch.setattr(ac, "clear_export_data", lambda: None)
    monkeypatch.setattr(ac, "generate_missing_data", lambda *a, **k: [{"hanzi": "你", "pinyin": "p", "english": "e"}])
    ctrl.render_right_column_content(left_params)

    # Empty path
    monkeypatch.setattr(ac, "get_processed_cards", lambda: [])
    monkeypatch.setattr(ac, "generate_missing_data", lambda *a, **k: [])
    ctrl.render_right_column_content(left_params)

