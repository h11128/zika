"""
Styles for the Chinese Character Learning Cards application.
Centralized CSS and styling utilities.
"""

import streamlit as st


def apply_global_styles() -> None:
    """Apply global CSS styles to the application."""
    st.markdown(
        """
        <style>
        .preview-sticky { 
            position: sticky; 
            top: 0; 
            z-index: 100; 
            background: #ffffff; 
            max-height: 100vh; 
            overflow-y: auto; 
            align-self: start; 
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sticky_wrapper_start() -> None:
    """Render the start of a sticky wrapper div."""
    st.markdown('<div class="preview-sticky">', unsafe_allow_html=True)


def render_sticky_wrapper_end() -> None:
    """Render the end of a sticky wrapper div."""
    st.markdown('</div>', unsafe_allow_html=True)
