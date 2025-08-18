import core.state as cs
import ui.styles as us


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
        self._html_calls = []

    def markdown(self, html, unsafe_allow_html=False):
        # record calls for assertions
        self._html_calls.append((html, unsafe_allow_html))


def setup_dummy_st(monkeypatch):
    dummy = DummySt()
    monkeypatch.setattr(us, "st", dummy)
    return dummy


def test_apply_global_styles_and_wrappers(monkeypatch):
    st = setup_dummy_st(monkeypatch)

    us.apply_global_styles()
    assert st._html_calls and "preview-sticky" in st._html_calls[-1][0]

    us.render_sticky_wrapper_start()
    us.render_sticky_wrapper_end()
    assert len(st._html_calls) >= 3

