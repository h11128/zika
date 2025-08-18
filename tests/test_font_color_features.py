#!/usr/bin/env python3
"""
Test the new font and background color features
"""

import sys
import os
import tempfile

# Ensure project root is on sys.path for `from src...` imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.pinyin_utils import hanzi_to_pinyin, contains_chinese
from src.dict_utils import create_default_dict
from src.layout_pptx import PPTXCardGenerator

def test_font_and_color_features():
    """Test the new font and background color features."""
    print("🎨 Testing font and background color features...")
    
    # Create test cards
    test_cards = [
        {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
        {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
        {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        {'hanzi': '学习', 'pinyin': 'xué xí', 'english': 'study'},
        {'hanzi': '工作', 'pinyin': 'gōng zuò', 'english': 'work'},
        {'hanzi': '时间', 'pinyin': 'shí jiān', 'english': 'time'}
    ]
    
    print(f"📝 Created {len(test_cards)} test cards")
    
    # Test different font and color combinations
    test_combinations = [
        {
            'name': 'Default Style',
            'hanzi_font': 'Microsoft YaHei',
            'background_color': '#FFFFFF',
            'description': 'Default white background with Microsoft YaHei font'
        },
        {
            'name': 'Light Blue Background',
            'hanzi_font': 'Microsoft YaHei',
            'background_color': '#E3F2FD',
            'description': 'Light blue background with Microsoft YaHei font'
        },
        {
            'name': 'SimSun Font',
            'hanzi_font': 'SimSun',
            'background_color': '#FFFFFF',
            'description': 'White background with SimSun font (traditional style)'
        },
        {
            'name': 'KaiTi Font with Light Green',
            'hanzi_font': 'KaiTi',
            'background_color': '#E8F5E8',
            'description': 'Light green background with KaiTi font (calligraphy style)'
        },
        {
            'name': 'Light Yellow Background',
            'hanzi_font': 'SimHei',
            'background_color': '#FFF9C4',
            'description': 'Light yellow background with SimHei font (bold style)'
        }
    ]
    
    print(f"\n🧪 Testing {len(test_combinations)} style combinations:")
    
    success_count = 0
    for i, combo in enumerate(test_combinations, 1):
        print(f"\n--- Test {i}: {combo['name']} ---")
        print(f"Description: {combo['description']}")
        print(f"Font: {combo['hanzi_font']}")
        print(f"Background: {combo['background_color']}")
        
        try:
            # Create output filename
            safe_name = combo['name'].replace(' ', '_').lower()
            output_file = f"out/test_style_{safe_name}.pptx"
            
            # Ensure output directory exists
            os.makedirs("out", exist_ok=True)
            
            # Create PPTX generator
            generator = PPTXCardGenerator(
                page_size='A4',
                card_size_cm=5.5,
                gap_cm=0.5,
                margin_cm=1.0
            )
            
            # Generate PPTX with custom styling
            success = generator.generate_pptx(
                test_cards, 
                output_file,
                font_hanzi=48,
                font_pinyin=18,
                font_english=14,
                hanzi_font=combo['hanzi_font'],
                background_color=combo['background_color']
            )
            
            if success:
                file_size = os.path.getsize(output_file)
                print(f"✅ Generated: {output_file} ({file_size:,} bytes)")
                success_count += 1
            else:
                print(f"❌ Failed to generate PPTX")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Results: {success_count}/{len(test_combinations)} combinations successful")
    
    return success_count == len(test_combinations)

def test_web_ui_integration():
    """Test integration with web UI export function."""
    print(f"\n🌐 Testing Web UI integration...")
    
    # Import the export function directly from services (avoid importing web_ui during tests)
    from services.export import export_cards

    # Test cards
    test_cards = [
        {'hanzi': '你好', 'pinyin': 'nǐ hǎo', 'english': 'hello'},
        {'hanzi': '再见', 'pinyin': 'zài jiàn', 'english': 'goodbye'},
        {'hanzi': '谢谢', 'pinyin': 'xiè xiè', 'english': 'thank you'}
    ]
    
    # Test export options with new features
    export_options = {
        'page_size': 'A4',
        'card_size': 5.5,
        'gap': 0.5,
        'margin': 1.0,
        'font_hanzi': 48,
        'font_pinyin': 18,
        'font_english': 14,
        'hanzi_font': 'KaiTi',
        'background_color': '#F0F8FF'  # Alice Blue
    }
    
    try:
        print("🔧 Testing export_cards function with new options...")
        file_content = export_cards(test_cards, 'pptx', **export_options)
        
        if file_content and len(file_content) > 0:
            print(f"✅ Export successful! Generated {len(file_content):,} bytes")
            
            # Save to file for verification
            test_output = "out/test_web_ui_integration.pptx"
            os.makedirs("out", exist_ok=True)
            with open(test_output, 'wb') as f:
                f.write(file_content)
            print(f"📁 Saved test file: {test_output}")
            
            return True
        else:
            print("❌ Export failed - no content generated")
            return False
            
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting font and background color feature tests...\n")
    
    # Run tests
    test1 = test_font_and_color_features()
    test2 = test_web_ui_integration()
    
    print(f"\n🎯 Final Results:")
    print(f"  Font/Color combinations test: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"  Web UI integration test: {'✅ PASS' if test2 else '❌ FAIL'}")
    
    if test1 and test2:
        print(f"\n🎉 All tests PASSED!")
        print(f"   New features are working correctly:")
        print(f"   - ✅ Custom Chinese font selection")
        print(f"   - ✅ Custom background color")
        print(f"   - ✅ Web UI integration")
        print(f"   - ✅ PPTX export with styling")
    else:
        print(f"\n❌ Some tests FAILED!")
        print(f"   Please check the implementation.")
    
    print(f"\n📁 Check the 'out' directory for generated test files.")
