#!/usr/bin/env python3
"""
Demo of the new sticky_preview() context manager.
Shows how to use the context manager for proper sticky preview behavior.
"""

import streamlit as st
from ui.styles import sticky_preview, apply_global_styles

def demo_sticky_preview():
    """Demonstrate the sticky preview context manager."""
    st.title("Sticky Preview Context Manager Demo")
    
    st.markdown("""
    This demo shows the new `sticky_preview()` context manager that ensures
    proper matching of open/close sticky wrapper elements.
    """)
    
    # Example 1: Basic usage
    st.header("Example 1: Basic Usage")
    
    with sticky_preview():
        st.subheader("📄 Preview Content")
        st.write("This content is wrapped in a sticky container.")
        st.write("The container will stick to the top when scrolling.")
        
        # Simulate some preview content
        for i in range(5):
            st.write(f"Preview item {i + 1}")
    
    # Example 2: Exception handling
    st.header("Example 2: Exception Handling")
    st.write("Even if an exception occurs, the sticky wrapper is properly closed.")
    
    try:
        with sticky_preview():
            st.subheader("🔲 Grid Preview")
            st.write("This demonstrates exception handling...")
            
            # Simulate some content before potential exception
            st.write("Content before exception")
            
            # This would normally cause an exception, but we'll handle it
            if st.button("Simulate Exception"):
                raise ValueError("Demo exception")
                
            st.write("Content after potential exception")
    except ValueError as e:
        st.error(f"Exception handled: {e}")
    
    # Example 3: Nested usage (not recommended but supported)
    st.header("Example 3: Multiple Sections")
    
    with sticky_preview():
        st.subheader("📊 Analytics Preview")
        st.write("First sticky section")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Cards", "42")
        with col2:
            st.metric("Pages", "7")
    
    st.write("Content between sticky sections...")
    
    with sticky_preview():
        st.subheader("⚙️ Settings Preview")
        st.write("Second sticky section")
        st.slider("Font Size", 12, 72, 48)
    
    # Show the benefits
    st.header("Benefits of Context Manager")
    st.markdown("""
    ### ✅ Advantages:
    - **Automatic cleanup**: Wrapper is always closed, even with exceptions
    - **Cleaner code**: No need to manually track open/close calls
    - **Type safety**: Context manager ensures proper usage
    - **CSS injection**: Automatically applies necessary styles
    - **Error prevention**: Impossible to forget closing wrapper
    
    ### 🚫 Old Way (Deprecated):
    ```python
    # DON'T DO THIS - deprecated
    render_sticky_wrapper_start()
    # ... content ...
    render_sticky_wrapper_end()  # Easy to forget!
    ```
    
    ### ✅ New Way (Recommended):
    ```python
    # DO THIS - context manager
    with sticky_preview():
        # ... content ...
        pass  # Automatically closed
    ```
    """)

if __name__ == "__main__":
    demo_sticky_preview()
