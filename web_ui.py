#!/usr/bin/env python3
"""
Chinese Character Learning Cards - Web UI Entry Point
Simple web interface for generating learning cards with real-time preview.
"""

import streamlit as st
import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file from current directory
except ImportError:
    pass  # dotenv not available, skip
# Suppress noisy third-party deprecation warning from jieba using pkg_resources
import warnings as _warnings
_warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module=r"jieba\._compat"
)


# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="中文学习卡片生成器",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import application controller and new components
from ui.app_controller import AppController


def initialize_new_components():
    """Initialize new components and systems."""
    try:
        # Initialize persistence system
        from components.browser_storage import hydrate_once, use_browser_storage
        from core.feature_flags import get_feature_flag

        if use_browser_storage():
            # Attempt to hydrate session state from localStorage
            if hydrate_once():
                st.rerun()  # Rerun if hydration occurred

        # Initialize feature flags configuration
        from core.feature_flags import configure_feature_flags
        configure_feature_flags(config_file_path=".zika_flags.json")

        # Show debug panel if enabled
        if get_feature_flag('storage_debug_panel', False):
            from components.browser_storage import render_storage_debug_panel
            with st.sidebar:
                render_storage_debug_panel()

    except Exception as e:
        # Don't let initialization errors break the app
        st.error(f"组件初始化警告: {str(e)}")


def main():
    """Main application entry point."""
    # Initialize new components first
    initialize_new_components()

    # Run main application
    controller = AppController()
    controller.run_main_flow()

    # Schedule save after main flow
    try:
        from components.browser_storage import flush_if_due, use_browser_storage
        if use_browser_storage():
            flush_if_due()  # Save if needed
    except Exception:
        pass  # Don't break app if save fails


# Run application
if __name__ == "__main__":
    main()