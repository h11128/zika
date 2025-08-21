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

# Page configuration - must be first Streamlit command
st.set_page_config(
    page_title="中文学习卡片生成器",
    page_icon="🀄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import application controller
from ui.app_controller import AppController


def main():
    """Main application entry point."""
    controller = AppController()
    controller.run_main_flow()


# Run application
if __name__ == "__main__":
    main()