import types
import ui.sections as us


class SS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)
    def __setattr__(self, k, v):
        self[k] = v


class Ctx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False

class SidebarCtx:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False


class DummySt:
    def __init__(self):
        self.session_state = SS()
        self.session_state.dictionary = types.SimpleNamespace(get_statistics=lambda: {"mini_dict_entries": 123})
        self.session_state.total_cards_generated = 10
        self.session_state.export_history = [
            {"time": "2025-01-01 00:00:00", "format": "pptx", "cards": 5},
            {"time": "2025-01-02 00:00:00", "format": "pdf", "cards": 8},
        ]

    # Provide an object supporting context manager for `with st.sidebar:`
    sidebar = SidebarCtx()
    def header(self, *a, **k):
        pass
    def subheader(self, *a, **k):
        pass
    def metric(self, *a, **k):
        pass
    def expander(self, *a, **k):
        return Ctx()
    def write(self, *a, **k):
        pass
    def markdown(self, *a, **k):
        pass


def test_render_sidebar(monkeypatch):
    st = DummySt()
    monkeypatch.setattr(us, "st", st)
    us.render_sidebar()

