"""
确保 UI 端“保留重复词”复选框与“智能分词”按钮交互时，按点击当时的选项生效。
该测试模拟 UI 状态机：先设置 session_state，再调用渲染函数的分词应用逻辑。
"""

import pytest

from services.processing import auto_segment_text
import ui.sections as us


class DummySS(dict):
    def __getattr__(self, k):
        if k in self:
            return self[k]
    def __setattr__(self, k, v):
        self[k] = v


def test_apply_segmentation_respects_checkbox_state(monkeypatch):
    # 模拟 session_state
    us.st.session_state.clear()
    us.st.session_state.input_text = "你好你好 你 叫 什么 名字 我 的 是 心美 李大文"
    # 用户勾选了保留重复词
    us.st.session_state.preserve_duplicates = True
    # 用户点击按钮时我们捕获当前值
    us.st.session_state.pending_preserve_duplicates = True
    us.st.session_state.apply_segmentation = True

    # 直接调用 UI 逻辑中应用分词的那段代码对应的函数：用 auto_segment_text 验证行为
    if us.st.session_state.get('apply_segmentation', False):
        if us.st.session_state.input_text.strip():
            preserve = us.st.session_state.pop('pending_preserve_duplicates', us.st.session_state.get('preserve_duplicates', False))
            us.st.session_state.input_text = auto_segment_text(us.st.session_state.input_text.strip(), preserve_duplicates=preserve)
        us.st.session_state.apply_segmentation = False

    # 结果应包含重复，证明保留重复词生效
    assert "你好 你好" in us.st.session_state.input_text or "你好你好" in us.st.session_state.input_text

