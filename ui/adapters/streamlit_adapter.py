"""
Streamlit implementation of UI adapter.

This module provides concrete implementations of the UIAdapter interface
for Streamlit components.
"""

import streamlit as st
from typing import Any, List, Dict, Optional, Union, Callable
from dataclasses import dataclass

from ui.ports import (
    UIAdapter, InputsAdapter, PreviewAdapter, LayoutAdapter,
    ComponentConfig, NotificationLevel
)


@dataclass
class StreamlitInputsAdapter(InputsAdapter):
    """Streamlit implementation of inputs adapter."""
    
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
class StreamlitPreviewAdapter(PreviewAdapter):
    """Streamlit implementation of preview adapter."""
    
    def render_html(self, html_content: str, height: int = 600, **kwargs) -> None:
        """Render HTML content using Streamlit."""
        st.components.v1.html(html_content, height=height, **kwargs)
    
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


@dataclass
class StreamlitLayoutAdapter(LayoutAdapter):
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


class StreamlitAdapter(UIAdapter):
    """Streamlit implementation of UI adapter."""
    
    def __init__(self):
        self._inputs = StreamlitInputsAdapter()
        self._preview = StreamlitPreviewAdapter()
        self._layout = StreamlitLayoutAdapter()
    
    @property
    def inputs(self) -> InputsAdapter:
        """Get the inputs adapter."""
        return self._inputs
    
    @property
    def preview(self) -> PreviewAdapter:
        """Get the preview adapter."""
        return self._preview
    
    @property
    def layout(self) -> LayoutAdapter:
        """Get the layout adapter."""
        return self._layout
    
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


def get_streamlit_adapter() -> StreamlitAdapter:
    """Get a Streamlit adapter instance."""
    return StreamlitAdapter()
