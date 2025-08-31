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
        self._write_calls = []

    def markdown(self, html, unsafe_allow_html=False):
        # record calls for assertions
        self._html_calls.append((html, unsafe_allow_html))

    def write(self, content):
        # record write calls for assertions
        self._write_calls.append(content)


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


def test_sticky_preview_context_manager(monkeypatch):
    """Test the sticky_preview context manager."""
    st = setup_dummy_st(monkeypatch)

    # Test normal usage
    with us.sticky_preview():
        st.write("Test content")

    # Should have CSS injection, opening div, content, and closing div
    assert len(st._html_calls) >= 3

    # Check for CSS injection
    css_found = any("preview-sticky" in call[0] for call in st._html_calls)
    assert css_found, "CSS should be injected"

    # Check for opening div
    opening_div_found = any('<div class="preview-sticky">' in call[0] for call in st._html_calls)
    assert opening_div_found, "Opening div should be present"

    # Check for closing div
    closing_div_found = any('</div>' in call[0] for call in st._html_calls)
    assert closing_div_found, "Closing div should be present"


def test_sticky_preview_exception_handling(monkeypatch):
    """Test that sticky_preview properly closes even when exception occurs."""
    st = setup_dummy_st(monkeypatch)

    try:
        with us.sticky_preview():
            raise ValueError("Test exception")
    except ValueError:
        pass  # Expected

    # Should still have opening and closing divs
    opening_div_found = any('<div class="preview-sticky">' in call[0] for call in st._html_calls)
    closing_div_found = any('</div>' in call[0] for call in st._html_calls)

    assert opening_div_found, "Opening div should be present even with exception"
    assert closing_div_found, "Closing div should be present even with exception"


def test_legacy_wrapper_deprecation_warnings(monkeypatch):
    """Test that legacy wrapper functions show deprecation warnings."""
    st = setup_dummy_st(monkeypatch)

    import warnings

    # Test start wrapper deprecation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        us.render_sticky_wrapper_start()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message)
        assert "sticky_preview()" in str(w[0].message)

    # Test end wrapper deprecation
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        us.render_sticky_wrapper_end()

        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "deprecated" in str(w[0].message)
        assert "sticky_preview()" in str(w[0].message)

