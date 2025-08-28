"""
TDD测试用例：修复Bug 1 - 智能分词自动删除重复词

这个测试文件按照TDD方式验证智能分词功能的重复词处理。
"""

import pytest
from services.processing import auto_segment_text


class TestAutoSegmentDuplicateBehavior:
    """测试智能分词重复词处理行为（包含保留与去重两种情况）"""
    
    def test_auto_segment_with_duplicates_preserve_option_false(self):
        """当preserve_duplicates=False时，应该删除重复词（当前行为）"""
        input_text = "你好 你 叫 什么 名字 我 的 是 心美 李大文你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        # 当前的行为：删除重复词
        result = auto_segment_text(input_text, preserve_duplicates=False)
        expected = "你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        assert result == expected, f"Expected: {expected}, Got: {result}"
    
    def test_auto_segment_with_duplicates_preserve_option_true(self):
        """当preserve_duplicates=True时，应该保留重复词（新功能）"""
        input_text = "你好 你 叫 什么 名字 我 的 是 心美 李大文你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        # 新的行为：保留重复词
        result = auto_segment_text(input_text, preserve_duplicates=True)
        expected = "你好 你 叫 什么 名字 我 的 是 心美 李大文 你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        assert result == expected, f"Expected: {expected}, Got: {result}"
    
    def test_auto_segment_default_behavior_unchanged(self):
        """默认行为保持不变（向后兼容）"""
        input_text = "你好 你 叫 什么 名字 我 的 是 心美 李大文你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        # 默认行为应该保持删除重复词（向后兼容）
        result = auto_segment_text(input_text)
        expected = "你好 你 叫 什么 名字 我 的 是 心美 李大文"
        
        assert result == expected, f"Expected: {expected}, Got: {result}"
    
    def test_auto_segment_no_duplicates(self):
        """没有重复词的情况"""
        input_text = "今天天气很好"

        # 无论preserve_duplicates设置如何，结果应该相同
        result_false = auto_segment_text(input_text, preserve_duplicates=False)
        result_true = auto_segment_text(input_text, preserve_duplicates=True)

        # 验证两个结果相同（具体分词结果由jieba决定）
        assert result_false == result_true
        assert len(result_false) > 0  # 确保有输出
    
    def test_auto_segment_complex_duplicates(self):
        """复杂重复词情况"""
        input_text = "学习 中文 很 有趣 学习 中文 需要 坚持 学习"
        
        # preserve_duplicates=False: 删除重复
        result_false = auto_segment_text(input_text, preserve_duplicates=False)
        expected_false = "学习 中文 很 有趣 需要 坚持"
        assert result_false == expected_false
        
        # preserve_duplicates=True: 保留重复
        result_true = auto_segment_text(input_text, preserve_duplicates=True)
        expected_true = "学习 中文 很 有趣 学习 中文 需要 坚持 学习"
        assert result_true == expected_true
    
    def test_auto_segment_empty_input(self):
        """空输入"""
        input_text = ""
        
        result_false = auto_segment_text(input_text, preserve_duplicates=False)
        result_true = auto_segment_text(input_text, preserve_duplicates=True)
        
        assert result_false == ""
        assert result_true == ""
    
    def test_auto_segment_single_word_repeated(self):
        """单个词重复"""
        input_text = "你好你好你好"
        
        # preserve_duplicates=False: 只保留一个
        result_false = auto_segment_text(input_text, preserve_duplicates=False)
        expected_false = "你好"
        assert result_false == expected_false
        
        # preserve_duplicates=True: 保留所有
        result_true = auto_segment_text(input_text, preserve_duplicates=True)
        expected_true = "你好 你好 你好"
        assert result_true == expected_true


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
