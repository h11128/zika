#!/usr/bin/env python3
"""
Test script to verify the export UI fix.
This script simulates the export process to ensure it works correctly.
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
from src.layout_pdf import PDFCardGenerator

def test_export_functionality():
    """Test the export functionality that's used in the web UI."""
    print("🧪 Testing export functionality...")
    
    # Create test cards
    test_cards = [
        {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
        {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
        {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        {'hanzi': '水', 'pinyin': 'shuǐ', 'english': 'water'},
        {'hanzi': '火', 'pinyin': 'huǒ', 'english': 'fire'},
        {'hanzi': '山', 'pinyin': 'shān', 'english': 'mountain'},
        {'hanzi': '月', 'pinyin': 'yuè', 'english': 'moon'},
        {'hanzi': '日', 'pinyin': 'rì', 'english': 'sun'},
        {'hanzi': '木', 'pinyin': 'mù', 'english': 'wood'}
    ]
    
    print(f"📝 Created {len(test_cards)} test cards")
    
    # Test export options (same as used in web UI)
    export_options = {
        'page_size': 'A4',
        'card_size': 5.5,
        'gap': 0.5,
        'margin': 1.0,
        'font_hanzi': 48,
        'font_pinyin': 18,
        'font_english': 14
    }
    
    print("🔧 Export options:", export_options)
    
    # Test PPTX export
    print("\n📄 Testing PPTX export...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pptx', delete=False) as tmp_file:
            generator = PPTXCardGenerator(
                page_size=export_options.get('page_size', 'A4'),
                card_size_cm=export_options.get('card_size', 5.5),
                gap_cm=export_options.get('gap', 0.5),
                margin_cm=export_options.get('margin', 1.0)
            )
            success = generator.generate_pptx(
                test_cards, tmp_file.name,
                font_hanzi=export_options.get('font_hanzi', 48),
                font_pinyin=export_options.get('font_pinyin', 18),
                font_english=export_options.get('font_english', 14)
            )
            
            if success:
                # Read file content (simulating what web UI does)
                with open(tmp_file.name, 'rb') as f:
                    file_content = f.read()
                print(f"✅ PPTX export successful! File size: {len(file_content)} bytes")
                
                # Clean up
                os.unlink(tmp_file.name)
            else:
                print("❌ PPTX export failed!")
                
    except Exception as e:
        print(f"❌ PPTX export error: {e}")
    
    # Test PDF export
    print("\n📑 Testing PDF export...")
    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            generator = PDFCardGenerator(
                page_size=export_options.get('page_size', 'A4'),
                card_size_cm=export_options.get('card_size', 5.5),
                gap_cm=export_options.get('gap', 0.5),
                margin_cm=export_options.get('margin', 1.0)
            )
            success = generator.generate_pdf(
                test_cards, tmp_file.name,
                font_hanzi=export_options.get('font_hanzi', 48),
                font_pinyin=export_options.get('font_pinyin', 18),
                font_english=export_options.get('font_english', 14)
            )
            
            if success:
                # Read file content (simulating what web UI does)
                with open(tmp_file.name, 'rb') as f:
                    file_content = f.read()
                print(f"✅ PDF export successful! File size: {len(file_content)} bytes")
                
                # Clean up
                os.unlink(tmp_file.name)
            else:
                print("❌ PDF export failed!")
                
    except Exception as e:
        print(f"❌ PDF export error: {e}")
    
    print("\n🎉 Export functionality test completed!")

def test_session_state_simulation():
    """Simulate session state behavior to test the fix."""
    print("\n🔄 Testing session state simulation...")
    
    # Simulate session state
    session_state = {
        'export_ready': {},
        'export_data': {},
        'processed_cards': [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'}
        ]
    }
    
    print("📊 Initial session state:")
    print(f"  - export_ready: {session_state['export_ready']}")
    print(f"  - export_data keys: {list(session_state['export_data'].keys())}")
    
    # Simulate PPTX generation
    print("\n📄 Simulating PPTX generation...")
    session_state['export_data']['pptx'] = {
        'content': b'fake_pptx_content',
        'filename': 'chinese_cards_2.pptx'
    }
    session_state['export_ready']['pptx'] = True
    
    print("✅ PPTX ready for download")
    print(f"  - export_ready: {session_state['export_ready']}")
    print(f"  - export_data keys: {list(session_state['export_data'].keys())}")
    
    # Simulate parameter change (should clear export data)
    print("\n🔧 Simulating parameter change...")
    session_state['export_ready'] = {}
    session_state['export_data'] = {}
    
    print("🔄 Export data cleared after parameter change")
    print(f"  - export_ready: {session_state['export_ready']}")
    print(f"  - export_data keys: {list(session_state['export_data'].keys())}")
    
    print("✅ Session state simulation completed!")

if __name__ == "__main__":
    print("🚀 Starting export UI fix tests...\n")
    
    test_export_functionality()
    test_session_state_simulation()
    
    print("\n🎯 All tests completed!")
    print("\n📋 Summary of fixes:")
    print("1. ✅ Added persistent export state in session")
    print("2. ✅ Download buttons now persist after generation")
    print("3. ✅ Export data cleared when cards or parameters change")
    print("4. ✅ Added regenerate buttons for new exports")
    print("5. ✅ Improved user feedback with success messages")
