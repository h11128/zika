import os
import sys
import pathlib
import traceback
import streamlit as st

st.set_page_config(page_title="Color Palette Mini Debug", layout="centered")

# Import both wrapper and underlying component for deep debug
from components.color_palette import color_palette  # wrapper (renders fallback too)
from components.color_palette import _color_palette_component as comp

presets = [
    "#000000", "#333333", "#FF4444", "#FF8800", "#FFDD00",
    "#44FF44", "#00DDDD", "#4488FF", "#8844FF", "#FF44FF",
    "#FFFFFF", "#CCCCCC", "#FF9999", "#FFBB77", "#FFEE77",
    "#99FF99", "#77EEEE", "#99BBFF", "#BB99FF", "#FF99FF",
]

# Session rerun counter
st.session_state.setdefault("_mini_dbg_reruns", 0)
st.session_state["_mini_dbg_reruns"] += 1

st.header("Mini Component Debug")

# Env info
st.subheader("环境信息")
st.write({
    "python": sys.version,
    "executable": sys.executable,
    "cwd": os.getcwd(),
    "streamlit": st.__version__,
})

# Filesystem checks
st.subheader("组件文件检查")
root = pathlib.Path(__file__).parent
frontend_dir = root / "components" / "color_palette" / "frontend"
index_html = frontend_dir / "index.html"
exists = {
    "components_dir": (root / "components").exists(),
    "color_palette_dir": (root / "components" / "color_palette").exists(),
    "frontend_dir": frontend_dir.exists(),
    "index_html": index_html.exists(),
}
st.write(exists)
if index_html.exists():
    try:
        content = index_html.read_text(encoding="utf-8", errors="ignore")
        st.code(content[:500] + ("..." if len(content) > 500 else ""), language="html")
    except Exception as e:
        st.error(f"读取 index.html 失败: {e}")

# Expected iframe route (for reference only)
route = "components.color_palette.color_palette"
st.caption(f"期望的组件路由: /component/{route}/index.html?streamlitUrl=http://localhost:8501/")

# Direct component call (raw)
st.subheader("直接调用 _color_palette_component（原始返回值）")
current = "#FFFFFF"
try:
    raw = comp(preset_colors=presets, value=current, key="mini_raw", default=current)
    st.write({"type": str(type(raw)), "repr": repr(raw)})
except Exception as e:
    st.error("直接调用抛出异常")
    st.code(traceback.format_exc())
    raw = None

# Wrapper call (renders fallback grid as well)
st.subheader("调用封装 color_palette（含备用网格）")
try:
    wrapped = color_palette(preset_colors=presets, value=current, key="mini_wrap")
    st.write({"type": str(type(wrapped)), "repr": repr(wrapped)})
except Exception as e:
    st.error("封装调用抛出异常")
    st.code(traceback.format_exc())
    wrapped = None

# Hints for browser console
st.markdown(
    "- 打开 DevTools → Console，观察父页是否仍有 'Received component message for unregistered ComponentInstance!' 刷屏\n"
    "- 打开 Network 勾选 Disable cache 后硬刷新\n"
)

st.caption(f"本页已重载次数: {st.session_state['_mini_dbg_reruns']}")
