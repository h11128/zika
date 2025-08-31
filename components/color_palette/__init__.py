import os
import re
import uuid
from typing import Optional, List
import streamlit as st
import streamlit.components.v1 as components

# Declare the component once (path points to folder containing index.html)
_component_path = os.path.join(os.path.dirname(__file__), "frontend")
_color_palette_component = components.declare_component(
    "color_palette",
    path=_component_path,
)

_HEX_RE = re.compile(r"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})$")

def _norm(c: Optional[str]) -> Optional[str]:
    if not c:
        return None
    c = c.strip()
    if not c.startswith('#'):
        c = '#' + c
    c = c.upper()
    return c if _HEX_RE.match(c) else None


def _fallback_palette(preset: List[str], current: str, key: Optional[str]) -> str:
    """Native Streamlit fallback: render a 10xN button grid with color chips.
    This avoids the custom component handshake entirely and is visually close.
    """
    if not preset:
        preset = ["#FFFFFF", "#000000"]
    # Normalize and de-dup
    values: List[str] = []
    seen = set()
    for c in preset:
        if c and c not in seen:
            values.append(c)
            seen.add(c)

    cols_per_row = 12
    container = st.container()
    chosen = current
    layout_rows = (len(values) + cols_per_row - 1) // cols_per_row
    for r in range(rows):
        layout_cols = container.columns(cols_per_row, gap_cm="small")
        for i in range(cols_per_row):
            idx = r * cols_per_row + i
            if idx >= len(values):
                continue
            c = values[idx]
            border = '#1e90ff' if c == current else '#ddd'
            with cols[i]:
                st.markdown(f"<div style='width_cm:20px;height_cm:20px;border-radius:4px;border:2px solid {border};background:{c};margin_cm:2px auto'></div>", unsafe_allow_html=True)
                if st.button(" ", key=(key or "cp") + f"_fb_{idx}", use_container_width=False):
                    chosen = c
    return chosen


def color_palette(preset_colors, value=None, key=None):
    """Render a color palette component and return selected hex color.

    Falls back to native selectbox if component front-end is not served (404/Not Found).
    """
    preset = [_norm(c) for c in (preset_colors or [])]
    preset = [c for c in preset if c]
    current = _norm(value) or (preset[0] if preset else '#FFFFFF')

    comp_selected = None
    try:
        comp_selected = _color_palette_component(
            preset_colors=preset,
            value=current,
            key=key,
            default=current,
        )
    except Exception:
        comp_selected = None

    # Do NOT always render a native fallback grid here because this function can be
    # called inside nested st.columns. Rendering another set of columns would violate
    # Streamlit's one-level nesting rule and raise an exception.
    # Instead, only return the component value if available; the caller can decide
    # how to fallback (e.g., a selectbox) in a safe context.

    sel_comp = _norm(comp_selected) if isinstance(comp_selected, str) else None

    # Prefer component value if it differs from current
    if sel_comp and sel_comp != current:
        return sel_comp

    # Otherwise keep current value; caller may render a fallback UI if needed.
    return sel_comp or current

