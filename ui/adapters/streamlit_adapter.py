"""
Streamlit implementation of UI adapter.

This module provides concrete implementations of the UIAdapter interface
for Streamlit components.
"""

import streamlit as st
import time
from typing import Any, List, Dict, Optional, Union, Callable
from dataclasses import dataclass

from ui.ports import (
    UIAdapter, UIInputsPort, UIPreviewPort, UILayoutPort, UINotificationPort, UIRefreshScheduler,
    ComponentConfig, NotificationLevel
)
from core.feature_flags import get_feature_flag


def _lazy_load_heavy_components():
    """Lazy load heavy components only when needed."""
    # This could be used for expensive imports or initializations
    pass


def _measure_adapter_performance(method_name: str):
    """Decorator to measure adapter method performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if get_feature_flag('performance_monitoring', True):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000

                    # Record performance measurement
                    try:
                        from services.performance_monitor import measure_performance
                        measure_performance(f"adapter_{method_name}", duration_ms, {
                            'method': method_name,
                            'args_count': len(args),
                            'kwargs_count': len(kwargs)
                        })
                    except ImportError:
                        # Performance monitoring not available
                        pass

                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    try:
                        from services.performance_monitor import measure_performance
                        measure_performance(f"adapter_{method_name}_error", duration_ms, {
                            'method': method_name,
                            'error': str(e)
                        })
                    except ImportError:
                        pass
                    raise
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator


@dataclass
class StreamlitInputsAdapter(UIInputsPort):
    """Streamlit implementation of inputs adapter."""
    
    @_measure_adapter_performance("text_input")
    def text_input(self, config: ComponentConfig, value: str = "", **kwargs) -> str:
        """Render a text input using Streamlit."""
        return st.text_input(
            label=config.label,
            value=value,
            key=config.key,
            help=config.help_text,
            placeholder=getattr(config, 'placeholder', None),
            **kwargs
        )
    
    def text_area(self, config: ComponentConfig, value: str = "", **kwargs) -> str:
        """Render a text area using Streamlit."""
        return st.text_area(
            label=config.label,
            value=value,
            key=config.key,
            help=config.help_text,
            placeholder=getattr(config, 'placeholder', None),
            **kwargs
        )
    
    def number_input(self, config: ComponentConfig, value: Union[int, float] = 0, **kwargs) -> Union[int, float]:
        """Render a number input using Streamlit."""
        return st.number_input(
            label=config.label,
            value=value,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def slider(self, config: ComponentConfig, value: Union[int, float] = 0, **kwargs) -> Union[int, float]:
        """Render a slider using Streamlit."""
        return st.slider(
            label=config.label,
            value=value,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def selectbox(self, config: ComponentConfig, options: List[Any], index: int = 0, **kwargs) -> Any:
        """Render a selectbox using Streamlit."""
        return st.selectbox(
            label=config.label,
            options=options,
            index=index,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def radio(self, config: ComponentConfig, options: List[Any], index: int = 0, **kwargs) -> Any:
        """Render radio buttons using Streamlit."""
        return st.radio(
            label=config.label,
            options=options,
            index=index,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def checkbox(self, config: ComponentConfig, value: bool = False, **kwargs) -> bool:
        """Render a checkbox using Streamlit."""
        return st.checkbox(
            label=config.label,
            value=value,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def button(self, config: ComponentConfig, **kwargs) -> bool:
        """Render a button using Streamlit."""
        return st.button(
            label=config.label,
            key=config.key,
            help=config.help_text,
            **kwargs
        )
    
    def file_uploader(self, config: ComponentConfig, **kwargs) -> Optional[Any]:
        """Render a file uploader using Streamlit."""
        return st.file_uploader(
            label=config.label,
            key=config.key,
            help=config.help_text,
            **kwargs
        )


@dataclass
class StreamlitPreviewAdapter(UIPreviewPort):
    """Streamlit implementation of preview adapter."""
    
    def render_html(self, html_content: str, height_cm: int = 600, **kwargs) -> None:
        """Render HTML content using Streamlit."""
        st.components.v1.html(html_content, height_cm=height, **kwargs)
    
    def render_image(self, image_data: Any, caption: str = "", **kwargs) -> None:
        """Render an image using Streamlit."""
        st.image(image_data, caption=caption, **kwargs)
    
    def render_download_button(self, config: ComponentConfig, data: bytes, 
                             filename: str, mime: str, **kwargs) -> bool:
        """Render a download button using Streamlit."""
        return st.download_button(
            label=config.label,
            data=data,
            file_name=filename,
            mime=mime,
            key=config.key,
            help=config.help_text,
            **kwargs
        )

    def container(self):
        """Create a container using Streamlit."""
        return st.container()

    def empty_placeholder(self):
        """Create an empty placeholder using Streamlit."""
        return st.empty()

    def html_component(self, html: str, height_cm: int = None, width_cm: int = None, scrolling: bool = False):
        """Render HTML component using Streamlit."""
        return st.components.v1.html(html, height_cm=height, width_cm=width, scrolling=scrolling)


@dataclass
class StreamlitLayoutAdapter(UILayoutPort):
    """Streamlit implementation of layout adapter."""
    
    def columns(self, ratios: List[Union[int, float]]) -> List[Any]:
        """Create columns using Streamlit."""
        return st.columns(ratios)
    
    def container(self) -> Any:
        """Create a container using Streamlit."""
        return st.container()
    
    def expander(self, label: str, expanded: bool = False) -> Any:
        """Create an expander using Streamlit."""
        return st.expander(label, expanded=expanded)
    
    def tabs(self, labels: List[str]) -> List[Any]:
        """Create tabs using Streamlit."""
        return st.tabs(labels)
    
    def sidebar(self) -> Any:
        """Access the sidebar using Streamlit."""
        return st.sidebar


@dataclass
class StreamlitNotificationAdapter(UINotificationPort):
    """Streamlit implementation of notification adapter."""

    def show_message(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> None:
        """Show a message using Streamlit."""
        if level == NotificationLevel.SUCCESS:
            st.success(message)
        elif level == NotificationLevel.WARNING:
            st.warning(message)
        elif level == NotificationLevel.ERROR:
            st.error(message)
        else:
            st.info(message)

    def show_success(self, message: str) -> None:
        """Show success message."""
        st.success(message)

    def show_warning(self, message: str) -> None:
        """Show warning message."""
        st.warning(message)

    def show_error(self, message: str) -> None:
        """Show error message."""
        st.error(message)

    def show_progress(self, progress: float, text: str = "") -> None:
        """Show progress bar."""
        st.progress(progress, text=text)

    def show_spinner(self, text: str = "Loading..."):
        """Show spinner context manager."""
        return st.spinner(text)


@dataclass
class StreamlitRefreshAdapter(UIRefreshScheduler):
    """Streamlit implementation of refresh scheduler."""

    def schedule_refresh(self, debounce_ms: int = 0) -> None:
        """Schedule a refresh using Streamlit."""
        # For now, immediate rerun - could add debouncing later
        st.rerun()

    def invalidate_cache(self) -> None:
        """Invalidate cache using Streamlit."""
        # Clear all cached functions
        st.cache_data.clear()
        st.cache_resource.clear()

    def schedule_rerun(self) -> None:
        """Schedule a rerun using Streamlit."""
        st.rerun()


class StreamlitAdapter(UIAdapter):
    """Streamlit implementation of UI adapter."""

    def __init__(self):
        # Lazy initialization to improve startup performance
        self._inputs = None
        self._preview = None
        self._layout = None
        self._notifications = None
        self._refresh = None
        self._initialized = False

    def _ensure_initialized(self):
        """Ensure all adapters are initialized (lazy loading)."""
        if not self._initialized:
            self._inputs = StreamlitInputsAdapter()
            self._preview = StreamlitPreviewAdapter()
            self._layout = StreamlitLayoutAdapter()
            self._notifications = StreamlitNotificationAdapter()
            self._refresh = StreamlitRefreshAdapter()
            self._initialized = True

    @property
    def inputs(self) -> UIInputsPort:
        """Get the inputs adapter."""
        self._ensure_initialized()
        return self._inputs

    @property
    def preview(self) -> UIPreviewPort:
        """Get the preview adapter."""
        self._ensure_initialized()
        return self._preview

    @property
    def layout(self) -> UILayoutPort:
        """Get the layout adapter."""
        self._ensure_initialized()
        return self._layout

    @property
    def notifications(self) -> UINotificationPort:
        """Get the notifications adapter."""
        self._ensure_initialized()
        return self._notifications

    @property
    def refresh(self) -> UIRefreshScheduler:
        """Get the refresh scheduler."""
        self._ensure_initialized()
        return self._refresh

    def subheader(self, text: str) -> None:
        """Render a subheader using Streamlit."""
        st.subheader(text)

    def notify(self, message: str, level: NotificationLevel = NotificationLevel.INFO) -> None:
        """Show a notification using Streamlit."""
        if level == NotificationLevel.SUCCESS:
            st.success(message)
        elif level == NotificationLevel.WARNING:
            st.warning(message)
        elif level == NotificationLevel.ERROR:
            st.error(message)
        else:
            st.info(message)
    
    def write(self, content: str) -> None:
        """Write content using Streamlit."""
        st.write(content)
    
    def markdown(self, content: str, unsafe_allow_html: bool = False) -> None:
        """Render markdown using Streamlit."""
        st.markdown(content, unsafe_allow_html=unsafe_allow_html)
    
    def header(self, text: str, level: int = 1) -> None:
        """Render a header using Streamlit."""
        if level == 1:
            st.header(text)
        elif level == 2:
            st.subheader(text)
        else:
            st.write(f"{'#' * level} {text}")
    
    def metric(self, label: str, value: str, delta: Optional[str] = None) -> None:
        """Render a metric using Streamlit."""
        st.metric(label, value, delta)
    
    def progress(self, value: float, text: str = "") -> None:
        """Show progress using Streamlit."""
        st.progress(value, text=text)
    
    def spinner(self, text: str = "Loading...") -> Any:
        """Show a spinner using Streamlit."""
        return st.spinner(text)
    
    def empty(self) -> Any:
        """Create an empty placeholder using Streamlit."""
        return st.empty()
    
    def rerun(self) -> None:
        """Trigger a rerun using Streamlit."""
        st.rerun()

    def cleanup(self) -> None:
        """Clean up resources and reset adapter state."""
        if get_feature_flag('performance_monitoring', True):
            try:
                from services.performance_monitor import measure_performance
                measure_performance("adapter_cleanup", 0.0, {'action': 'cleanup'})
            except ImportError:
                pass

        # Reset lazy initialization
        self._inputs = None
        self._preview = None
        self._layout = None
        self._notifications = None
        self._refresh = None
        self._initialized = False


def get_streamlit_adapter() -> StreamlitAdapter:
    """Get a Streamlit adapter instance."""
    return StreamlitAdapter()
