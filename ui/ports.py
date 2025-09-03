"""
UI Adapter Layer - Ports and Adapters Pattern
Provides framework-agnostic interfaces for UI interactions.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import os
import sys


# Simple shim to provide attribute-style access to session_state in tests/bare mode
class _SessionStateShim(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
        raise AttributeError(k)
    def __setattr__(self, k, v):
        self[k] = v

class _StProxy:
    """Proxy for the Streamlit module to allow late binding and testing.
    - In tests, modules may monkeypatch ui.<module>.st directly and never touch this proxy.
    - In production, we bind the real streamlit module at adapter creation time.

    Special-case session_state to allow tests to set/get it even when unbound.
    """
    def __init__(self):
        object.__setattr__(self, "_target", None)
        object.__setattr__(self, "_session_state", _SessionStateShim())
    def bind(self, target):
        object.__setattr__(self, "_target", target)
        # If target has session_state, mirror it
        try:
            ss = getattr(target, "session_state", None)
            if ss is not None:
                # Wrap dict-like in shim to support attribute access in tests
                if isinstance(ss, dict) and not isinstance(ss, _SessionStateShim):
                    ss = _SessionStateShim(ss)
                object.__setattr__(self, "_session_state", ss)
        except Exception:
            pass
    def __getattr__(self, name):
        if name == "session_state":
            return object.__getattribute__(self, "_session_state")
        target = object.__getattribute__(self, "_target")
        if target is None:
            raise RuntimeError("Streamlit module not bound in ui.ports.st; call get_ui_adapter() in app context or bind explicitly.")
        return getattr(target, name)
    def __setattr__(self, name, value):
        if name == "session_state":
            object.__setattr__(self, "_session_state", value)
            return
        target = object.__getattribute__(self, "_target")
        if target is None:
            raise RuntimeError("Streamlit module not bound in ui.ports.st; call get_ui_adapter() in app context or bind explicitly.")
        setattr(target, name, value)

st = _StProxy()

from core.feature_flags import get_feature_flag


class NotificationLevel(Enum):
    """Notification severity levels."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class UIEvent:
    """Represents a UI event."""
    event_type: str
    component_id: str
    value: Any
    metadata: Dict[str, Any] = None


@dataclass
class ComponentConfig:
    """Configuration for UI components."""
    key: str
    label: str
    help_text: Optional[str] = None
    disabled: bool = False
    visible: bool = True


@lru_cache(maxsize=256)
def create_component_config(key: str, label: str, help_text: Optional[str] = None,
                          disabled: bool = False, visible: bool = True) -> ComponentConfig:
    """Create a cached ComponentConfig instance to reduce object creation overhead."""
    return ComponentConfig(
        key=key,
        label=label,
        help_text=help_text,
        disabled=disabled,
        visible=visible
    )


class UIInputsPort(ABC):
    """Port for input components."""

    @abstractmethod
    def text_input(self, config: ComponentConfig, value: str = "",
                   placeholder: str = "") -> str:
        """Render text input component."""
        pass

    @abstractmethod
    def text_area(self, config: ComponentConfig, value: str = "",
                  height_cm: int = 200) -> str:
        """Render text area component."""
        pass

    @abstractmethod
    def number_input(self, config: ComponentConfig, value: float = 0.0,
                     min_value: float = None, max_value: float = None,
                     step: float = None) -> float:
        """Render number input component."""
        pass

    @abstractmethod
    def slider(self, config: ComponentConfig, value: float,
               min_value: float, max_value: float, step: float = None) -> float:
        """Render slider component."""
        pass

    @abstractmethod
    def selectbox(self, config: ComponentConfig, options: List[Any],
                  index: int = 0) -> Any:
        """Render selectbox component."""
        pass

    @abstractmethod
    def checkbox(self, config: ComponentConfig, value: bool = False) -> bool:
        """Render checkbox component."""
        pass

    @abstractmethod
    def radio(self, config: ComponentConfig, options: List[str],
              index: int = 0, horizontal: bool = False) -> str:
        """Render radio button component."""
        pass

    @abstractmethod
    def button(self, config: ComponentConfig) -> bool:
        """Render button component."""
        pass

    @abstractmethod
    def file_uploader(self, config: ComponentConfig,
                      accepted_types: List[str] = None) -> Any:
        """Render file uploader component."""
        pass


class UIPreviewPort(ABC):
    """Port for preview components."""

    @abstractmethod
    def html_component(self, html_content: str, height_cm: int = 600) -> None:
        """Render HTML component."""
        pass

    @abstractmethod
    def empty_placeholder(self) -> Any:
        """Create empty placeholder for dynamic content."""
        pass

    @abstractmethod
    def container(self) -> Any:
        """Create container for grouping components."""
        pass


class UINotificationPort(ABC):
    """Port for notification components."""

    @abstractmethod
    def show_message(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> None:
        """Show notification message."""
        pass

    @abstractmethod
    def show_progress(self, progress: float, text: str = "") -> None:
        """Show progress indicator."""
        pass

    @abstractmethod
    def show_spinner(self, text: str = "Loading...") -> Any:
        """Show spinner context manager."""
        pass

    # Convenience methods expected by tests and UI code
    @abstractmethod
    def show_success(self, message: str) -> None:
        pass

    @abstractmethod
    def show_info(self, message: str) -> None:
        pass

    @abstractmethod
    def show_warning(self, message: str) -> None:
        pass

    @abstractmethod
    def show_error(self, message: str) -> None:
        pass


class UILayoutPort(ABC):
    """Port for layout components."""

    @abstractmethod
    def columns(self, ratios: List[Union[int, float]]) -> List[Any]:
        """Create column layout."""
        pass

    @abstractmethod
    def expander(self, label: str, expanded: bool = False) -> Any:
        """Create expandable section."""
        pass

    @abstractmethod
    def tabs(self, labels: List[str]) -> List[Any]:
        """Create tabbed interface."""
        pass

    @abstractmethod
    def sidebar(self) -> Any:
        """Access sidebar container."""
        pass

    @abstractmethod
    def container(self) -> Any:
        """Create container for grouping components."""
        pass


class UIRefreshScheduler(ABC):
    """Port for refresh scheduling."""

    @abstractmethod
    def schedule_rerun(self, delay_ms: int = 0) -> None:
        """Schedule UI rerun."""
        pass

    @abstractmethod
    def invalidate_cache(self, cache_key: str = None) -> None:
        """Invalidate specific cache or all caches."""
        pass


class UIAdapter(ABC):
    """Main UI adapter interface."""

    @property
    @abstractmethod
    def inputs(self) -> UIInputsPort:
        """Get inputs port."""
        pass

    @property
    @abstractmethod
    def preview(self) -> UIPreviewPort:
        """Get preview port."""
        pass

    @property
    @abstractmethod
    def notifications(self) -> UINotificationPort:
        """Get notifications port."""
        pass

    @property
    @abstractmethod
    def layout(self) -> UILayoutPort:
        """Get layout port."""
        pass

    @property
    @abstractmethod
    def refresh(self) -> UIRefreshScheduler:
        """Get refresh scheduler."""
        pass

    @abstractmethod
    def rerun(self) -> None:
        """Trigger a rerun of the UI/app."""
        pass

    @abstractmethod
    def header(self, text: str, level: int = 1) -> None:
        """Render header."""
        pass

    @abstractmethod
    def subheader(self, text: str) -> None:
        """Render subheader."""
        pass

    @abstractmethod
    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        """Render markdown."""
        pass

    @abstractmethod
    def text(self, text: str) -> None:
        """Render plain text."""
        pass

    @abstractmethod
    def write(self, obj: Any) -> None:
        """Generic write passthrough."""
        pass

    @abstractmethod
    def caption(self, text: str) -> None:
        """Render caption text."""
        pass

    @abstractmethod
    def metric(self, label: str, value: str, delta: Optional[str] = None) -> None:
        """Render a metric widget."""
        pass

    @abstractmethod
    def text(self, text: str) -> None:
        """Render plain text."""
        pass


class StreamlitInputsAdapter(UIInputsPort):
    """Streamlit implementation of inputs port."""

    def text_input(self, config: ComponentConfig, value: str = "",
                   placeholder: str = "") -> str:
        return st.text_input(
            config.label, value=value, placeholder=placeholder,
            key=config.key, help=config.help_text, disabled=config.disabled
        )

    def text_area(self, config: ComponentConfig, value: str = "",
                  height_cm: int = 200) -> str:
        # Streamlit expects 'height' in pixels; our API uses height_cm for tests.
        height_px = height_cm
        return st.text_area(
            config.label, value=value, height=height_px,
            key=config.key, help=config.help_text, disabled=config.disabled
        )

    def number_input(self, config: ComponentConfig, value: float = 0.0,
                     min_value: float = None, max_value: float = None,
                     step: float = None) -> float:
        return st.number_input(
            config.label, value=value, min_value=min_value,
            max_value=max_value, step=step, key=config.key,
            help=config.help_text, disabled=config.disabled
        )

    def slider(self, config: ComponentConfig, value: float,
               min_value: float, max_value: float, step: float = None) -> float:
        return st.slider(
            config.label, min_value=min_value, max_value=max_value,
            value=value, step=step, key=config.key,
            help=config.help_text, disabled=config.disabled
        )

    def selectbox(self, config: ComponentConfig, options: List[Any],
                  index: int = 0) -> Any:
        return st.selectbox(
            config.label, options=options, index=index,
            key=config.key, help=config.help_text, disabled=config.disabled
        )

    def checkbox(self, config: ComponentConfig, value: bool = False) -> bool:
        return st.checkbox(
            config.label, value=value, key=config.key,
            help=config.help_text, disabled=config.disabled
        )

    def radio(self, config: ComponentConfig, options: List[str],
              index: int = 0, horizontal: bool = False) -> str:
        return st.radio(
            config.label, options=options, index=index,
            horizontal=horizontal, key=config.key,
            help=config.help_text, disabled=config.disabled
        )

    def button(self, config: ComponentConfig) -> bool:
        return st.button(
            config.label, key=config.key,
            help=config.help_text, disabled=config.disabled
        )

    def file_uploader(self, config: ComponentConfig,
                      accepted_types: List[str] = None) -> Any:
        return st.file_uploader(
            config.label, type=accepted_types, key=config.key,
            help=config.help_text, disabled=config.disabled
        )


class StreamlitPreviewAdapter(UIPreviewPort):
    """Streamlit implementation of preview port."""

    def html_component(self, html_content: str, height_cm: int = 600) -> None:
        # Streamlit components.html expects 'height' (pixels). Keep our arg name for BC.
        st.components.v1.html(html_content, height=height_cm)

    def empty_placeholder(self) -> Any:
        return st.empty()

    def container(self) -> Any:
        return st.container()


class StreamlitNotificationAdapter(UINotificationPort):
    """Streamlit implementation of notifications port."""

    def show_message(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> None:
        if level == NotificationLevel.INFO:
            st.info(message)
        elif level == NotificationLevel.SUCCESS:
            st.success(message)
        elif level == NotificationLevel.WARNING:
            st.warning(message)
        elif level == NotificationLevel.ERROR:
            st.error(message)

    def show_progress(self, progress: float, text: str = "") -> None:
        st.progress(progress, text=text)

    def show_spinner(self, text: str = "Loading...") -> Any:
        return st.spinner(text)

    # Convenience methods
    def show_success(self, message: str) -> None:
        st.success(message)

    def show_info(self, message: str) -> None:
        st.info(message)

    def show_warning(self, message: str) -> None:
        st.warning(message)

    def show_error(self, message: str) -> None:
        st.error(message)


class StreamlitLayoutAdapter(UILayoutPort):
    """Streamlit implementation of layout port."""

    def columns(self, ratios: List[Union[int, float]]) -> List[Any]:
        return st.columns(ratios)

    def expander(self, label: str, expanded: bool = False) -> Any:
        return st.expander(label, expanded=expanded)

    def tabs(self, labels: List[str]) -> List[Any]:
        return st.tabs(labels)

    def sidebar(self) -> Any:
        return st.sidebar

    def container(self) -> Any:
        return st.container()


class StreamlitRefreshAdapter(UIRefreshScheduler):
    """Streamlit implementation of refresh scheduler."""

    def schedule_rerun(self, delay_ms: int = 0) -> None:
        if delay_ms > 0:
            # Note: Streamlit doesn't support delayed rerun natively
            # This would need to be implemented with threading/async
            import time
            time.sleep(delay_ms / 1000.0)
        st.rerun()

    def invalidate_cache(self, cache_key: str = None) -> None:
        # Use state service for cache invalidation
        try:
            from ui.state import invalidate_preview_cache
            invalidate_preview_cache("adapter invalidation")
        except ImportError:
            # Fallback to legacy cache clearing
            try:
                from services.cache_v2 import clear_preview_cache
                clear_preview_cache()
            except ImportError:
                pass


class StreamlitAdapter(UIAdapter):
    """Streamlit implementation of UI adapter."""

    def __init__(self):
        self._inputs = StreamlitInputsAdapter()
        self._preview = StreamlitPreviewAdapter()
        self._notifications = StreamlitNotificationAdapter()
        self._layout = StreamlitLayoutAdapter()
        self._refresh = StreamlitRefreshAdapter()

    @property
    def inputs(self) -> UIInputsPort:
        return self._inputs

    @property
    def preview(self) -> UIPreviewPort:
        return self._preview

    @property
    def notifications(self) -> UINotificationPort:
        return self._notifications

    @property
    def layout(self) -> UILayoutPort:
        return self._layout

    @property
    def refresh(self) -> UIRefreshScheduler:
        return self._refresh

    def rerun(self) -> None:
        st.rerun()

    def header(self, text: str, level: int = 1) -> None:
        if level == 1:
            st.title(text)
        elif level == 2:
            st.subheader(text)
        else:
            st.markdown(f"{'#' * level} {text}")

    def subheader(self, text: str) -> None:
        st.subheader(text)

    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        st.markdown(text, unsafe_allow_html=unsafe_allow_html)

    def text(self, text: str) -> None:
        st.text(text)

    def write(self, obj: Any) -> None:
        st.write(obj)

    def caption(self, text: str) -> None:
        st.caption(text)

    def title(self, text: str) -> None:
        st.title(text)

    def metric(self, label: str, value: str, delta: Optional[str] = None) -> None:
        st.metric(label, value, delta)

class FakeInputsAdapter(UIInputsPort):
    """Fake implementation for testing."""

    def __init__(self):
        self.interactions: List[Dict[str, Any]] = []
        self.values: Dict[str, Any] = {}
        # Specific tracking for test assertions
        self.radio_calls: List[Dict[str, Any]] = []
        self.button_calls: List[Dict[str, Any]] = []
        self.selectbox_calls: List[Dict[str, Any]] = []
        self.checkbox_calls: List[Dict[str, Any]] = []
        self.text_area_calls: List[Dict[str, Any]] = []
        self.text_input_calls: List[Dict[str, Any]] = []
        self.number_input_calls: List[Dict[str, Any]] = []
        self.slider_calls: List[Dict[str, Any]] = []
        self.file_uploader_calls: List[Dict[str, Any]] = []
        self.download_button_calls: List[Dict[str, Any]] = []

    def _record_interaction(self, component_type: str, config: ComponentConfig, **kwargs):
        self.interactions.append({
            'type': component_type,
            'key': config.key,
            'label': config.label,
            **kwargs
        })

    def text_input(self, config: ComponentConfig, value: str = "",
                   placeholder: str = "") -> str:
        self._record_interaction('text_input', config, value=value, placeholder=placeholder)
        try:
            from ui.ports import st as _st, _StProxy as _Proxy
            return _st.text_input(config.label, value=value, key=config.key, help=config.help_text, placeholder=placeholder, disabled=config.disabled)
        except Exception as e:
            # If st is our unbound proxy, fall back to fake value; otherwise propagate
            try:
                from ui.ports import st as _st, _StProxy as _Proxy
                if isinstance(_st, _Proxy) and getattr(_st, "_target", None) is None:
                    return self.values.get(config.key, value)
            except Exception:
                pass
            raise

    def text_area(self, config: ComponentConfig, value: str = "",
                  height_cm: int = 200) -> str:
        self._record_interaction('text_area', config, value=value, height_cm=height_cm)
        return self.values.get(config.key, value)

    def number_input(self, config: ComponentConfig, value: float = 0.0,
                     min_value: float = None, max_value: float = None,
                     step: float = None) -> float:
        self._record_interaction('number_input', config, value=value,
                               min_value=min_value, max_value=max_value, step=step)
        return self.values.get(config.key, value)

    def slider(self, config: ComponentConfig, value: float,
               min_value: float, max_value: float, step: float = None) -> float:
        self._record_interaction('slider', config, value=value,
                               min_value=min_value, max_value=max_value, step=step)
        return self.values.get(config.key, value)

    def selectbox(self, config: ComponentConfig, options: List[Any],
                  index: int = 0) -> Any:
        self._record_interaction('selectbox', config, options=options, index=index)
        try:
            from ui.ports import st as _st
            return _st.selectbox(config.label, options=options, index=index, key=config.key, help=config.help_text, disabled=config.disabled)
        except Exception:
            return self.values.get(config.key, options[index] if options else None)

    def checkbox(self, config: ComponentConfig, value: bool = False) -> bool:
        self._record_interaction('checkbox', config, value=value)
        try:
            from ui.ports import st as _st
            return _st.checkbox(config.label, value=value, key=config.key, help=config.help_text, disabled=config.disabled)
        except Exception:
            return self.values.get(config.key, value)

    def radio(self, config: ComponentConfig, options: List[str],
              index: int = 0, horizontal: bool = False) -> str:
        self._record_interaction('radio', config, options=options,
                               index=index, horizontal=horizontal)
        self.radio_calls.append({
            'config': config, 'options': options, 'index': index, 'horizontal': horizontal
        })
        return self.values.get(config.key, options[index] if options else "")

    def button(self, config: ComponentConfig) -> bool:
        self._record_interaction('button', config)
        try:
            from ui.ports import st as _st
            return _st.button(config.label, key=config.key, help=config.help_text, disabled=config.disabled)
        except Exception:
            return self.values.get(config.key, False)

    def file_uploader(self, config: ComponentConfig,
                      accepted_types: List[str] = None) -> Any:
        self._record_interaction('file_uploader', config, accepted_types=accepted_types)
        return self.values.get(config.key, None)

    def set_value(self, key: str, value: Any) -> None:
        """Set value for testing."""
        self.values[key] = value


class FakePreviewAdapter(UIPreviewPort):
    """Fake implementation for testing."""

    def __init__(self):
        self.html_renders: List[Dict[str, Any]] = []
        self.placeholders: List[str] = []
        self.containers: List[str] = []

    def html_component(self, html_content: str, height_cm: int = 600) -> None:
        # Record normalized field name 'height' for consistency in tests
        self.html_renders.append({'content': html_content, 'height': height_cm})

    def empty_placeholder(self) -> Any:
        placeholder_id = f"placeholder_{len(self.placeholders)}"
        self.placeholders.append(placeholder_id)
        return placeholder_id

    def container(self) -> Any:
        container_id = f"container_{len(self.containers)}"
        self.containers.append(container_id)
        return container_id


class FakeNotificationAdapter(UINotificationPort):
    """Fake implementation for testing."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.progress_updates: List[Dict[str, Any]] = []
        self.spinners: List[str] = []

    def show_message(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> None:
        self.messages.append({'message': message, 'level': level})

    def show_progress(self, progress: float, text: str = "") -> None:
        self.progress_updates.append({'progress': progress, 'text': text})

    def show_spinner(self, text: str = "Loading...") -> Any:
        self.spinners.append(text)
        return FakeContextManager(f"spinner_{len(self.spinners)}")

    # Convenience methods forward to st for regression tests and record
    def show_success(self, message: str) -> None:
        self.show_message(message, NotificationLevel.SUCCESS)
        try:
            from ui.ports import st as _st
            _st.success(message)
        except Exception:
            pass

    def show_info(self, message: str) -> None:
        self.show_message(message, NotificationLevel.INFO)
        try:
            from ui.ports import st as _st
            _st.info(message)
        except Exception:
            pass

    def show_warning(self, message: str) -> None:
        self.show_message(message, NotificationLevel.WARNING)
        try:
            from ui.ports import st as _st
            _st.warning(message)
        except Exception:
            pass

    def show_error(self, message: str) -> None:
        self.show_message(message, NotificationLevel.ERROR)
        try:
            from ui.ports import st as _st
            _st.error(message)
        except Exception:
            pass


class FakeContextManager:
    """Simple context manager for testing."""
    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakeLayoutAdapter(UILayoutPort):
    """Fake implementation for testing."""

    def __init__(self):
        self.column_layouts: List[List[Union[int, float]]] = []
        self.expanders: List[Dict[str, Any]] = []
        self.tab_groups: List[List[str]] = []

    def columns(self, ratios: List[Union[int, float]]) -> List[Any]:
        self.column_layouts.append(ratios)
        try:
            from ui.ports import st as _st
            return _st.columns(ratios)
        except Exception:
            return [FakeContextManager(f"col_{i}") for i in range(len(ratios))]

    def expander(self, label: str, expanded: bool = False) -> Any:
        self.expanders.append({'label': label, 'expanded': expanded})
        try:
            from ui.ports import st as _st
            return _st.expander(label, expanded=expanded)
        except Exception:
            return FakeContextManager(f"expander_{len(self.expanders)}")

    def tabs(self, labels: List[str]) -> List[Any]:
        self.tab_groups.append(labels)
        try:
            from ui.ports import st as _st
            return _st.tabs(labels)
        except Exception:
            return [FakeContextManager(f"tab_{i}") for i in range(len(labels))]

    def sidebar(self) -> Any:
        try:
            from ui.ports import st as _st
            return _st.sidebar
        except Exception:
            return FakeContextManager("sidebar")

    def container(self) -> Any:
        try:
            from ui.ports import st as _st
            return _st.container()
        except Exception:
            return FakeContextManager("container")


class FakeRefreshAdapter(UIRefreshScheduler):
    """Fake implementation for testing."""

    def __init__(self):
        self.rerun_calls: List[int] = []
        self.cache_invalidations: List[str] = []

    def schedule_rerun(self, delay_ms: int = 0) -> None:
        self.rerun_calls.append(delay_ms)

    def invalidate_cache(self, cache_key: str = None) -> None:
        self.cache_invalidations.append(cache_key or "all")


class FakeAdapter(UIAdapter):
    """Fake implementation for testing."""

    def __init__(self):
        self._inputs = FakeInputsAdapter()
        self._preview = FakePreviewAdapter()
        self._notifications = FakeNotificationAdapter()
        self._layout = FakeLayoutAdapter()
        self._refresh = FakeRefreshAdapter()
        self.headers: List[Dict[str, Any]] = []
        self.markdown_renders: List[Dict[str, Any]] = []

    @property
    def inputs(self) -> UIInputsPort:
        return self._inputs

    @property
    def preview(self) -> UIPreviewPort:
        return self._preview

    @property
    def notifications(self) -> UINotificationPort:
        return self._notifications

    @property
    def layout(self) -> UILayoutPort:
        return self._layout

    @property
    def refresh(self) -> UIRefreshScheduler:
        return self._refresh

    def rerun(self) -> None:
        try:
            from ui.ports import st as _st
            _st.rerun()
        except Exception:
            # Record a rerun intent; tests primarily check existence
            self.headers.append({'action': 'rerun'})

    def header(self, text: str, level: int = 1) -> None:
        self.headers.append({'text': text, 'level': level})
        # Forward to st for tests that expect real Streamlit calls
        try:
            from ui.ports import st as _st
            if level == 1:
                _st.title(text)
            elif level == 2:
                _st.subheader(text)
            else:
                _st.markdown(f"{'#' * level} {text}")
        except Exception:
            pass

    def subheader(self, text: str) -> None:
        self.headers.append({'text': text, 'level': 2})
        # Forward to st for tests that expect st.subheader to be called
        try:
            from ui.ports import st as _st
            _st.subheader(text)
        except Exception:
            pass

    def title(self, text: str) -> None:
        self.headers.append({'text': text, 'level': 0})
        try:
            from ui.ports import st as _st
            _st.title(text)
        except Exception:
            pass

    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        self.markdown_renders.append({'text': text, 'unsafe_allow_html': unsafe_allow_html})
        # Forward to st.markdown to satisfy regression tests
        try:
            from ui.ports import st as _st
            # Keep signature minimal for tests expecting simple call
            if unsafe_allow_html:
                _st.markdown(text, unsafe_allow_html=unsafe_allow_html)
            else:
                _st.markdown(text)
        except Exception:
            pass

    def text(self, text: str) -> None:
        # Record and forward to st for tests that expect st.text to be called
        self.markdown_renders.append({'text': text, 'as': 'text'})
        try:
            from ui.ports import st as _st
            _st.text(text)
        except Exception:
            pass

    def write(self, obj: Any) -> None:
        # Forward to st.write for compatibility
        try:
            from ui.ports import st as _st
            _st.write(obj)
        except Exception:
            # Record for test visibility
            self.markdown_renders.append({'write': obj})

    def caption(self, text: str) -> None:
        try:
            from ui.ports import st as _st
            _st.caption(text)
        except Exception:
            self.markdown_renders.append({'caption': text})

    def metric(self, label: str, value: str, delta: Optional[str] = None) -> None:
        try:
            from ui.ports import st as _st
            _st.metric(label, value, delta)
        except Exception:
            # Record fallback
            self.markdown_renders.append({'metric': {'label': label, 'value': value, 'delta': delta}})


# Global adapter instance
_ui_adapter: Optional[UIAdapter] = None


def get_ui_adapter() -> UIAdapter:
    """Get the current UI adapter with optimized singleton pattern."""
    global _ui_adapter

    if _ui_adapter is None:
        # Use fake adapter only when explicitly enabled via feature flag
        if get_feature_flag('use_fake_adapter', False):
            _ui_adapter = FakeAdapter()
        else:
            # Create real adapter without importing Streamlit yet; it will bind lazily on first use
            from ui.adapters.streamlit_adapter import StreamlitAdapter
            _ui_adapter = StreamlitAdapter()

    return _ui_adapter


def set_ui_adapter(adapter: UIAdapter) -> None:
    """Set the UI adapter (for testing)."""
    global _ui_adapter
    _ui_adapter = adapter


def reset_ui_adapter() -> None:
    """Reset the UI adapter to default."""
    global _ui_adapter
    _ui_adapter = None
