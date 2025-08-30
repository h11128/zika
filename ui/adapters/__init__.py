"""
UI Adapters package.

This package contains concrete implementations of the UIAdapter interface
for different UI frameworks (Streamlit, etc.).
"""

from .streamlit_adapter import StreamlitAdapter

__all__ = ['StreamlitAdapter']
