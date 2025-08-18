#!/usr/bin/env python3
"""
Test CC-CEDICT integration
"""

import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dict_utils import create_default_dict

def test_cedict_integration():
    """Test the CEDICT integration."""
    print("🧪 Testing CC-CEDICT integration...")
    
    # Create dictionary instance
    print("📚 Loading dictionaries...")
    dict_obj = create_default_dict("data")
    
    # Show statistics
    print("\n📊 Dictionary statistics:")
    stats = dict_obj.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test the problematic words that were missing
    test_words = [
        "叫",      # to call
        "什么",    # what
        "名字",    # name
        "你好",    # hello (should be in mini dict)
        "爱",      # love (should be in mini dict)
        "朋友",    # friend (should be in mini dict)
        "电脑",    # computer (should be in mini dict)
        "学习",    # study (might be in CEDICT)
        "工作",    # work (might be in CEDICT)
        "时间",    # time (might be in CEDICT)
    ]
    
    print(f"\n🔍 Testing {len(test_words)} words:")
    print("=" * 60)
    
    found_count = 0
    for word in test_words:
        translation = dict_obj.lookup_translation(word)
        info = dict_obj.get_word_info(word)
        
        if translation:
            found_count += 1
            print(f"✅ {word:6} -> {translation}")
            print(f"   Source: {info['source']}")
        else:
            print(f"❌ {word:6} -> No translation found")
        print()
    
    print("=" * 60)
    print(f"📈 Results: {found_count}/{len(test_words)} words found ({found_count/len(test_words)*100:.1f}%)")
    
    # Test some CEDICT-specific words
    print(f"\n🔍 Testing CEDICT-specific words:")
    cedict_words = [
        "计算机",   # computer (CEDICT version)
        "手机",     # mobile phone
        "互联网",   # internet
        "软件",     # software
        "硬件",     # hardware
    ]
    
    cedict_found = 0
    for word in cedict_words:
        translation = dict_obj.lookup_translation(word)
        info = dict_obj.get_word_info(word)
        
        if translation:
            cedict_found += 1
            print(f"✅ {word:8} -> {translation}")
            print(f"   Source: {info['source']}")
        else:
            print(f"❌ {word:8} -> No translation found")
    
    print(f"\n📈 CEDICT Results: {cedict_found}/{len(cedict_words)} words found")
    
    # Overall assessment
    total_found = found_count + cedict_found
    total_tested = len(test_words) + len(cedict_words)
    
    print(f"\n🎯 Overall Assessment:")
    print(f"   Total words tested: {total_tested}")
    print(f"   Total words found: {total_found}")
    print(f"   Success rate: {total_found/total_tested*100:.1f}%")
    
    if stats['cedict_entries'] > 0:
        print(f"   ✅ CEDICT successfully loaded with {stats['cedict_entries']:,} entries")
    else:
        print(f"   ❌ CEDICT not loaded or empty")
    
    return total_found >= total_tested * 0.8  # 80% success rate

if __name__ == "__main__":
    print("🚀 Starting CC-CEDICT integration test...\n")
    
    success = test_cedict_integration()
    
    if success:
        print("\n🎉 CC-CEDICT integration test PASSED!")
        print("   The dictionary now has much better coverage for Chinese words.")
    else:
        print("\n❌ CC-CEDICT integration test FAILED!")
        print("   Please check the CEDICT file and loading logic.")
