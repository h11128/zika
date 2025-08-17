#!/usr/bin/env python3
"""
Test script for auto-segmentation functionality
"""

import jieba
import re

def auto_segment_text(text: str) -> str:
    """Automatically segment Chinese text into words/characters."""
    if not text.strip():
        return ""
    
    # Remove existing spaces and punctuation
    text = re.sub(r'[^\u4e00-\u9fff]', '', text)
    
    if not text:
        return ""
    
    # Use jieba for initial segmentation
    segments = list(jieba.cut(text, cut_all=False))
    
    # Post-process: split long words and handle single characters
    final_segments = []
    for segment in segments:
        if len(segment) == 1:
            # Single character - keep as is
            final_segments.append(segment)
        elif len(segment) == 2:
            # Two characters - usually a word, keep as is
            final_segments.append(segment)
        elif len(segment) >= 3:
            # Long segment - check if it should be split
            # For learning cards, prefer shorter segments
            if len(segment) <= 4:
                # Keep 3-4 character words
                final_segments.append(segment)
            else:
                # Split longer segments into smaller parts
                # Try to split into 2-character words first
                for i in range(0, len(segment), 2):
                    if i + 1 < len(segment):
                        final_segments.append(segment[i:i+2])
                    else:
                        final_segments.append(segment[i])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_segments = []
    for segment in final_segments:
        if segment not in seen:
            seen.add(segment)
            unique_segments.append(segment)
    
    return " ".join(unique_segments)

def test_segmentation():
    """Test various Chinese text segmentation scenarios."""
    test_cases = [
        "我爱我的家人朋友们",
        "今天天气很好",
        "学习中文很有趣",
        "北京大学是一所著名的大学",
        "我们一起去吃饭吧",
        "春天来了花开了",
        "中国人民解放军",
        "人工智能技术发展",
        "红黄蓝绿黑白灰",
        "爸爸妈妈哥哥姐姐"
    ]
    
    print("🔤 自动分词测试")
    print("=" * 50)
    
    for i, text in enumerate(test_cases, 1):
        result = auto_segment_text(text)
        print(f"{i:2d}. 输入: {text}")
        print(f"    输出: {result}")
        print(f"    词数: {len(result.split())}")
        print()

if __name__ == "__main__":
    test_segmentation()
