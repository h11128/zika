#!/usr/bin/env python3
"""
演示多源词典混合功能
"""

from src.dict_utils import create_default_dict

def demo_multi_dictionary():
    print("=== 多源词典混合功能演示 ===\n")
    
    # 创建默认词典（包含 Mini + CEDICT）
    dictionary = create_default_dict('data')
    
    # 添加技术词典
    tech_dict = {
        '算法': ['algorithm', 'computational method'],
        '数据': ['data', 'dataset', 'information'],
        '网络': ['network', 'internet', 'web'],
        '系统': ['system', 'framework'],
        '爱': ['affection', 'romance'],  # 与现有词典有重叠
    }
    dictionary.add_custom_dictionary('technical', tech_dict)
    
    # 添加商务词典
    business_dict = {
        '管理': ['management', 'administration'],
        '市场': ['market', 'marketplace'],
        '客户': ['customer', 'client'],
        '数据': ['business data', 'metrics'],  # 与技术词典有重叠
    }
    dictionary.add_custom_dictionary('business', business_dict)
    
    # 测试词汇
    test_words = ['爱', '数据', '算法', '管理', '世界']
    
    for word in test_words:
        print(f"\n{'='*50}")
        print(f"词汇: {word}")
        print('='*50)
        
        # 显示各个源的翻译
        all_translations = dictionary.get_all_translations(word)
        if all_translations:
            print("各词典源的翻译:")
            for source, translation in all_translations.items():
                print(f"  📚 {source:10}: {translation}")
        else:
            print("  未在任何词典中找到")
        
        # 显示传统单一优先级结果
        traditional = dictionary.lookup_translation(word)
        print(f"\n传统模式 (优先级): {traditional}")
        
        # 显示新的混合结果
        mixed = dictionary.lookup_translation_mixed(word)
        print(f"混合模式 (多源):   {mixed}")
        
        # 分析改进效果
        if mixed and traditional and mixed != traditional:
            if '|' in mixed:
                sources_count = len(mixed.split('|'))
                print(f"✨ 混合模式整合了 {sources_count} 个不同的翻译源!")
            else:
                print("📝 混合模式去除了重复，结果更简洁")
        elif not traditional and mixed:
            print("🆕 混合模式找到了传统模式遗漏的翻译!")
        else:
            print("📋 两种模式结果相同")

def demo_custom_dictionary_api():
    print("\n\n=== 自定义词典 API 演示 ===\n")
    
    dictionary = create_default_dict('data')
    
    # 演示如何添加专业领域词典
    medical_dict = {
        '症状': ['symptom', 'manifestation'],
        '诊断': ['diagnosis', 'medical assessment'],
        '治疗': ['treatment', 'therapy', 'cure'],
    }
    
    legal_dict = {
        '合同': ['contract', 'agreement'],
        '法律': ['law', 'legal statute'],
        '证据': ['evidence', 'proof'],
    }
    
    # 添加多个专业词典
    dictionary.add_custom_dictionary('medical', medical_dict)
    dictionary.add_custom_dictionary('legal', legal_dict)
    
    print("已添加的词典源:")
    for source in dictionary.loaded_sources:
        print(f"  • {source}")
    
    # 测试专业词汇
    test_words = ['症状', '合同', '治疗']
    
    for word in test_words:
        print(f"\n词汇: {word}")
        mixed = dictionary.lookup_translation_mixed(word)
        print(f"多源翻译: {mixed}")

if __name__ == "__main__":
    demo_multi_dictionary()
    demo_custom_dictionary_api()
    
    print("\n" + "="*60)
    print("🎉 多源词典混合功能演示完成!")
    print("="*60)
    print("\n主要特性:")
    print("✅ 支持任意数量的词典源")
    print("✅ 智能去重和合并")
    print("✅ 保持翻译质量优先级")
    print("✅ 易于添加自定义词典")
    print("✅ 向后兼容现有API")
