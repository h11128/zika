"""
Unified UI functions that automatically choose between adapter and legacy paths.

This module provides a single interface that automatically routes to either
the adapter or legacy Streamlit implementation based on feature flags.
"""

from typing import Any, List, Dict, Optional, Union, Callable, ContextManager
from contextlib import contextmanager
from core.feature_flags import get_feature_flag
from ui.state_bridge import state_get, state_set, state_update, state_delete, state_append, state_increment


class UnifiedUI:
    """Unified UI interface that automatically chooses implementation."""
    
    def __init__(self):
        self._adapter = None
        self._use_adapter = get_feature_flag('ui_adapter', False)

        if self._use_adapter:
            try:
                from ui.ports import get_ui_adapter
                self._adapter = get_ui_adapter()
            except Exception:
                self._use_adapter = False

        # Record adapter usage for observability
        self._record_usage_stats()

    def _record_usage_stats(self) -> None:
        """Record usage statistics for observability."""
        try:
            from services.observability import record_adapter_usage, record_direct_call
            if self._use_adapter and self._adapter:
                record_adapter_usage("unified_ui")
            else:
                record_direct_call("streamlit")
        except ImportError:
            pass

    def header(self, text: str, level: int = 1) -> None:
        """Render a header."""
        if self._use_adapter and self._adapter:
            if level == 1:
                self._adapter.header(text)
            else:
                self._adapter.header(text, level=level)
        else:
            import streamlit as st
            if level == 1:
                st.header(text)
            elif level == 2:
                st.subheader(text)
            else:
                st.write(f"**{text}**")
    
    def button(self, label: str, key: Optional[str] = None, help_text: Optional[str] = None, 
               use_container_width: bool = False) -> bool:
        """Render a button."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.button(config, use_container_width=use_container_width)
        else:
            import streamlit as st
            return st.button(label, key=key, help=help_text, use_container_width=use_container_width)
    
    def radio(self, label: str, options: List[str], index: int = 0, key: Optional[str] = None,
              help_text: Optional[str] = None, horizontal: bool = False) -> str:
        """Render a radio button."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.radio(config, options=options, index=index, horizontal=horizontal)
        else:
            import streamlit as st
            return st.radio(label, options, index=index, key=key, help=help_text, horizontal=horizontal)
    
    def selectbox(self, label: str, options: List[str], index: int = 0, key: Optional[str] = None,
                  help_text: Optional[str] = None) -> str:
        """Render a selectbox."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.selectbox(config, options=options, index=index)
        else:
            import streamlit as st
            return st.selectbox(label, options, index=index, key=key, help=help_text)
    
    def text_input(self, label: str, value: str = "", key: Optional[str] = None,
                   help_text: Optional[str] = None, placeholder: Optional[str] = None) -> str:
        """Render a text input."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.text_input(config, value=value, placeholder=placeholder or "")
        else:
            import streamlit as st
            return st.text_input(label, value=value, key=key, help=help_text, placeholder=placeholder)
    
    def text_area(self, label: str, value: str = "", key: Optional[str] = None,
                  help_text: Optional[str] = None, height_cm: int = 200, placeholder: Optional[str] = None) -> str:
        """Render a text area.
        Note: height_cm is kept for backward compatibility; maps to Streamlit's 'height'.
        """
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.text_area(config, value=value, height=height_cm, placeholder=placeholder or "")
        else:
            import streamlit as st
            return st.text_area(label, value=value, key=key, help=help_text, height=height_cm, placeholder=placeholder)

    def checkbox(self, label: str, value: bool = False, key: Optional[str] = None,
                 help_text: Optional[str] = None) -> bool:
        """Render a checkbox."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.checkbox(config, value=value)
        else:
            import streamlit as st
            return st.checkbox(label, value=value, key=key, help=help_text)
    
    def slider(self, label: str, min_value: float, max_value: float, value: float,
               step: float = 1.0, key: Optional[str] = None, help_text: Optional[str] = None) -> float:
        """Render a slider."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.slider(config, value=value, min_value=min_value, 
                                             max_value=max_value, step=step)
        else:
            import streamlit as st
            return st.slider(label, min_value=min_value, max_value=max_value, value=value,
                           step=step, key=key, help=help_text)
    
    def columns(self, ratios: List[Union[int, float]]) -> List[Any]:
        """Create columns."""
        if self._use_adapter and self._adapter:
            return self._adapter.layout.columns(ratios)
        else:
            import streamlit as st
            return st.columns(ratios)
    
    @contextmanager
    def sidebar(self):
        """Create sidebar context."""
        if self._use_adapter and self._adapter:
            with self._adapter.layout.sidebar():
                yield
        else:
            import streamlit as st
            with st.sidebar:
                yield
    
    @contextmanager
    def expander(self, label: str, expanded: bool = False):
        """Create expander context."""
        if self._use_adapter and self._adapter:
            with self._adapter.layout.expander(label, expanded=expanded):
                yield
        else:
            import streamlit as st
            with st.expander(label, expanded=expanded):
                yield
    
    @contextmanager
    def spinner(self, text: str):
        """Create spinner context."""
        if self._use_adapter and self._adapter:
            with self._adapter.spinner(text):
                yield
        else:
            import streamlit as st
            with st.spinner(text):
                yield
    
    def success(self, message: str) -> None:
        """Show success message."""
        if self._use_adapter and self._adapter:
            from ui.ports import NotificationLevel
            self._adapter.notify(message, NotificationLevel.SUCCESS)
        else:
            import streamlit as st
            st.success(message)
    
    def error(self, message: str) -> None:
        """Show error message."""
        if self._use_adapter and self._adapter:
            from ui.ports import NotificationLevel
            self._adapter.notify(message, NotificationLevel.ERROR)
        else:
            import streamlit as st
            st.error(message)
    
    def warning(self, message: str) -> None:
        """Show warning message."""
        if self._use_adapter and self._adapter:
            from ui.ports import NotificationLevel
            self._adapter.notify(message, NotificationLevel.WARNING)
        else:
            import streamlit as st
            st.warning(message)
    
    def info(self, message: str) -> None:
        """Show info message."""
        if self._use_adapter and self._adapter:
            from ui.ports import NotificationLevel
            self._adapter.notify(message, NotificationLevel.INFO)
        else:
            import streamlit as st
            st.info(message)
    
    def write(self, content: Any) -> None:
        """Write content."""
        if self._use_adapter and self._adapter:
            self._adapter.write(content)
        else:
            import streamlit as st
            st.write(content)
    
    def markdown(self, content: str, unsafe_allow_html: bool = False) -> None:
        """Render markdown."""
        if self._use_adapter and self._adapter:
            self._adapter.markdown(content, unsafe_allow_html=unsafe_allow_html)
        else:
            import streamlit as st
            st.markdown(content, unsafe_allow_html=unsafe_allow_html)
    
    def metric(self, label: str, value: str) -> None:
        """Show metric."""
        if self._use_adapter and self._adapter:
            # Adapter might not have metric, fallback to write
            self._adapter.write(f"**{label}**: {value}")
        else:
            import streamlit as st
            st.metric(label, value)
    
    def download_button(self, label: str, data: bytes, filename: str, mime: str,
                       use_container_width: bool = False) -> bool:
        """Render download button."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=f"download_{filename}", label=label)
            return self._adapter.preview.render_download_button(
                config, data=data, filename=filename, mime=mime, 
                use_container_width=use_container_width
            )
        else:
            import streamlit as st
            return st.download_button(label, data=data, file_name=filename, mime=mime,
                                    use_container_width=use_container_width)
    
    def rerun(self) -> None:
        """Trigger a rerun."""
        if self._use_adapter and self._adapter:
            self._adapter.rerun()
        else:
            import streamlit as st
            st.rerun()

    def tabs(self, tab_names: List[str]) -> List[Any]:
        """Create tabs."""
        if self._use_adapter and self._adapter:
            # Adapter might not have tabs, fallback to containers
            return [self._adapter.layout.container() for _ in tab_names]
        else:
            import streamlit as st
            return st.tabs(tab_names)

    @contextmanager
    def form(self, key: str):
        """Create form context."""
        if self._use_adapter and self._adapter:
            # Adapter might not have form, use regular container
            with self._adapter.layout.container():
                yield
        else:
            import streamlit as st
            with st.form(key):
                yield

    def form_submit_button(self, label: str, key: Optional[str] = None) -> bool:
        """Render form submit button."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label)
            return self._adapter.inputs.button(config)
        else:
            import streamlit as st
            return st.form_submit_button(label)

    def file_uploader(self, label: str, type: Optional[List[str]] = None, key: Optional[str] = None,
                     help_text: Optional[str] = None) -> Any:
        """Render file uploader."""
        if self._use_adapter and self._adapter:
            from ui.ports import ComponentConfig
            config = ComponentConfig(key=key, label=label, help_text=help_text)
            return self._adapter.inputs.file_uploader(config, type=type or [])
        else:
            import streamlit as st
            return st.file_uploader(label, type=type, key=key, help=help_text)

    def dataframe(self, data: Any) -> None:
        """Display dataframe."""
        if self._use_adapter and self._adapter:
            # Adapter might not have dataframe, fallback to write
            self._adapter.write(data)
        else:
            import streamlit as st
            st.dataframe(data)

    def html(self, html_content: str, height_cm: int = 400) -> None:
        """Render HTML content.
        height_cm is in pixels for historical reasons; Streamlit expects 'height'.
        """
        if self._use_adapter and self._adapter:
            # If adapter available, prefer its HTML component if present
            try:
                # Some adapters expose preview.html_component; fall back to markdown if absent
                self._adapter.preview.html_component(html_content, height_cm=height_cm)  # type: ignore[attr-defined]
                return
            except Exception:
                pass
            self._adapter.markdown(f"```html\n{html_content}\n```")
        else:
            import streamlit as st
            st.components.v1.html(html_content, height=height_cm)


# Global unified UI instance
_unified_ui = None


def get_unified_ui() -> UnifiedUI:
    """Get the global unified UI instance."""
    global _unified_ui
    if _unified_ui is None:
        _unified_ui = UnifiedUI()
    return _unified_ui


# Export the main class
__all__ = ['UnifiedUI', 'get_unified_ui']
