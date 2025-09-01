"""
UI Adapter Layer - Ports and Adapters Pattern
Provides framework-agnostic interfaces for UI interactions.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import streamlit as st

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
        return st.text_area(
            config.label, value=value, height_cm=height_cm,
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
        st.components.v1.html(html_content, height_cm=height_cm)
    
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
    
    def header(self, text: str, level: int = 1) -> None:
        if level == 1:
            st.header(text)
        elif level == 2:
            st.subheader(text)
        else:
            st.markdown(f"{'#' * level} {text}")
    
    def subheader(self, text: str) -> None:
        st.subheader(text)
    
    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        st.markdown(text, unsafe_allow_html=unsafe_allow_html)


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
        return self.values.get(config.key, value)

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
        return self.values.get(config.key, options[index] if options else None)

    def checkbox(self, config: ComponentConfig, value: bool = False) -> bool:
        self._record_interaction('checkbox', config, value=value)
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
        self.html_renders.append({'content': html_content, 'height_cm': height_cm})

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
        return [FakeContextManager(f"col_{i}") for i in range(len(ratios))]

    def expander(self, label: str, expanded: bool = False) -> Any:
        self.expanders.append({'label': label, 'expanded': expanded})
        return FakeContextManager(f"expander_{len(self.expanders)}")

    def tabs(self, labels: List[str]) -> List[Any]:
        self.tab_groups.append(labels)
        return [FakeContextManager(f"tab_{i}") for i in range(len(labels))]

    def sidebar(self) -> Any:
        return FakeContextManager("sidebar")


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

    def header(self, text: str, level: int = 1) -> None:
        self.headers.append({'text': text, 'level': level})

    def subheader(self, text: str) -> None:
        self.headers.append({'text': text, 'level': 2})

    def markdown(self, text: str, unsafe_allow_html: bool = False) -> None:
        self.markdown_renders.append({'text': text, 'unsafe_allow_html': unsafe_allow_html})


# Global adapter instance
_ui_adapter: Optional[UIAdapter] = None


def get_ui_adapter() -> UIAdapter:
    """Get the current UI adapter with optimized singleton pattern."""
    global _ui_adapter

    if _ui_adapter is None:
        # Check feature flag for adapter type
        if get_feature_flag('use_fake_adapter', False):
            _ui_adapter = FakeAdapter()
        else:
            # Lazy import to reduce startup time
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
