#!/usr/bin/env python3
"""
Test script to verify export functionality works correctly
"""

import sys
import os
# Ensure project root is on sys.path for `from src...` imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.pinyin_utils import hanzi_to_pinyin, contains_chinese
from src.dict_utils import create_default_dict
from src.layout_pptx import PPTXCardGenerator
from src.layout_pdf import PDFCardGenerator

def test_export_workflow():
    """Test the complete export workflow"""
    print("🧪 测试导出工作流程")
    print("=" * 50)
    
    # Create test cards
    test_input = "爱 家 朋友 水 火 山 月 日 木 天 地 人"
    words = [word.strip() for word in test_input.split() if word.strip()]
    
    cards = []
    for word in words:
        if contains_chinese(word):
            cards.append({
                'hanzi': word,
                'pinyin': '',
                'english': ''
            })
    
    print(f"1. 创建了 {len(cards)} 张卡片")
    
    # Generate missing data
    dictionary = create_default_dict("data")
    
    for card in cards:
        if not card['pinyin']:
            card['pinyin'] = hanzi_to_pinyin(card['hanzi'])
        if not card['english']:
            translation = dictionary.lookup_translation(card['hanzi'])
            if translation:
                card['english'] = translation
    
    print(f"2. 生成拼音和翻译完成")
    
    # Test PPTX export
    try:
        pptx_generator = PPTXCardGenerator(
            page_size='A4',
            card_size_cm=5.5,
            gap_cm=0.5,
            margin_cm=1.0
        )
        
        success = pptx_generator.generate_pptx(
            cards, 
            "out/test_export_fix.pptx",
            hanzi_font_size=48,
            pinyin_font_size=18,
            english_font_size=14
        )
        
        if success:
            print("3. ✅ PPTX 导出成功")
        else:
            print("3. ❌ PPTX 导出失败")
            
    except Exception as e:
        print(f"3. ❌ PPTX 导出异常: {e}")
    
    # Test PDF export
    try:
        pdf_generator = PDFCardGenerator(
            page_size='A4',
            card_size_cm=5.5,
            gap_cm=0.5,
            margin_cm=1.0
        )
        
        success = pdf_generator.generate_pdf(
            cards, 
            "out/test_export_fix.pdf",
            hanzi_font_size=48,
            pinyin_font_size=18,
            english_font_size=14
        )
        
        if success:
            print("4. ✅ PDF 导出成功")
        else:
            print("4. ❌ PDF 导出失败")
            
    except Exception as e:
        print(f"4. ❌ PDF 导出异常: {e}")
    
    print("\n📊 测试结果:")
    print(f"- 输入文本: {test_input}")
    print(f"- 卡片数量: {len(cards)}")
    print(f"- 预期页数: {(len(cards) + 8) // 9}")
    
    # Show first few cards
    print("\n🀄 前3张卡片:")
    for i, card in enumerate(cards[:3]):
        print(f"  {i+1}. {card['hanzi']} | {card['pinyin']} | {card['english']}")

if __name__ == "__main__":
    test_export_workflow()
