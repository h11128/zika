import builtins
import importlib
import types

import pytest


def test_html_component_converts_cm_to_px_in_production(monkeypatch):
    # Create a fake streamlit module with real-like html function (not a MagicMock)
    class FakeV1:
        def __init__(self):
            self.last_args = None
            self.last_kwargs = None
        def html(self, *args, **kwargs):
            self.last_args = args
            self.last_kwargs = kwargs
            return "OK"
    class FakeComponents:
        def __init__(self):
            self.v1 = FakeV1()
    class FakeSt:
        def __init__(self):
            self.components = FakeComponents()
    fake_st = FakeSt()

    # Inject fake streamlit into sys.modules using monkeypatch to auto-restore
    import sys, importlib
    monkeypatch.setitem(sys.modules, 'streamlit', fake_st)

    # Reload adapter to pick up fake streamlit
    import ui.adapters.streamlit_adapter as sa
    importlib.reload(sa)
    adapter = sa.StreamlitPreviewAdapter()

    # Call html_component in production mode (non-MagicMock)
    adapter.html_component("<html></html>", height_cm=10.0, width_cm=21.0, scrolling=True)

    # Verify cm->px conversion (96 DPI)
    h_expected = int(round(10.0 * 96.0 / 2.54))
    w_expected = int(round(21.0 * 96.0 / 2.54))
    assert fake_st.components.v1.last_kwargs.get("height") == h_expected
    assert fake_st.components.v1.last_kwargs.get("width") == w_expected
    assert fake_st.components.v1.last_kwargs.get("scrolling") is True


def test_render_html_converts_cm_to_px_in_production(monkeypatch):
    # Use a fresh fake streamlit each time
    class FakeV1:
        def __init__(self):
            self.last_args = None
            self.last_kwargs = None
        def html(self, *args, **kwargs):
            self.last_args = args
            self.last_kwargs = kwargs
            return "OK"
    class FakeComponents:
        def __init__(self):
            self.v1 = FakeV1()
    class FakeSt:
        def __init__(self):
            self.components = FakeComponents()
    fake_st = FakeSt()

    import sys, importlib
    monkeypatch.setitem(sys.modules, 'streamlit', fake_st)

    import ui.adapters.streamlit_adapter as sa
    importlib.reload(sa)
    adapter = sa.StreamlitPreviewAdapter()

    adapter.render_html("<html></html>", height_cm=29.7)  # A4 height in cm

    h_expected = int(round(29.7 * 96.0 / 2.54))
    assert fake_st.components.v1.last_kwargs.get("height") == h_expected

