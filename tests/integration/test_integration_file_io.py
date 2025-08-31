#!/usr/bin/env python3
"""
File I/O Integration Tests for Chinese Learning Cards Application

Tests file operations and I/O workflows:
1. CSV file parsing and validation
2. Dictionary file loading and caching
3. PPTX/PDF file generation and validation
4. Temporary file handling and cleanup
5. File format validation and error handling
6. Large file processing workflows
"""

import os
import sys
import tempfile
import pytest
import csv
import json
from pathlib import Path
from io import StringIO, BytesIO
from zipfile import ZipFile
import shutil

# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services.processing import parse_input_text, generate_missing_data
from services.export import export_cards
from src.dict_utils import create_default_dict, ChineseDict
from src.gen_cards import main as gen_cards_main
from core.constants import DEFAULT_PAGE_SIZE, DEFAULT_CARD_SIZE


class TestCSVFileIntegration:
    """Test CSV file parsing and processing integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dictionary = create_default_dict("data")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_csv_file_complete_workflow(self):
        """Test complete CSV file processing workflow."""
        # Create test CSV file
        csv_path = Path(self.temp_dir) / "test_cards.csv"
        csv_content = """hanzi,pinyin,english
爱,,love
家,jiā,home
朋友,,friend
水,,
火,huǒ,fire
学习,,study
工作,,work"""
        
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Read and parse CSV file
        cards = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cards.append({
                    'hanzi': row.get('hanzi', '').strip(),
                    'pinyin': row.get('pinyin', '').strip(),
                    'english': row.get('english', '').strip()
                })
        
        assert len(cards) == 7
        
        # Process cards
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True,
            dictionary=self.dictionary
        )
        
        # Verify processing
        for card in processed_cards:
            assert card['hanzi']
            assert card['pinyin']  # Should be generated if missing
            # English might be empty if not in dictionary
        
        # Export to file
        output_path = Path(self.temp_dir) / "output.pptx"
        pptx_content = export_cards(processed_cards, 'pptx')
        
        with open(output_path, 'wb') as f:
            f.write(pptx_content)
        
        # Verify file was created and has reasonable size
        assert output_path.exists()
        assert output_path.stat().st_size > 1000
    
    def test_csv_with_different_encodings(self):
        """Test CSV files with different encodings."""
        # Test UTF-8 with BOM
        csv_path_bom = Path(self.temp_dir) / "test_bom.csv"
        csv_content = "hanzi,pinyin,english\n爱,ài,love\n家,jiā,home"
        
        with open(csv_path_bom, 'w', encoding='utf-8-sig') as f:
            f.write(csv_content)
        
        # Should handle UTF-8 with BOM
        cards = []
        with open(csv_path_bom, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cards.append({
                    'hanzi': row.get('hanzi', '').strip(),
                    'pinyin': row.get('pinyin', '').strip(),
                    'english': row.get('english', '').strip()
                })
        
        assert len(cards) == 2
        assert cards[0]['hanzi'] == '爱'
    
    def test_csv_with_malformed_data(self):
        """Test CSV with malformed or incomplete data."""
        csv_path = Path(self.temp_dir) / "malformed.csv"
        malformed_content = """hanzi,pinyin,english
爱,ài,love
,jiā,home
朋友,,
hello,world,english
水
火,huǒ,
,,,
"""
        
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(malformed_content)
        
        # Parse with validation
        valid_cards = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hanzi = (row.get('hanzi') or '').strip()
                # Only include rows with valid Chinese characters
                if hanzi and any('\u4e00' <= char <= '\u9fff' for char in hanzi):
                    valid_cards.append({
                        'hanzi': hanzi,
                        'pinyin': (row.get('pinyin') or '').strip(),
                        'english': (row.get('english') or '').strip()
                    })
        
        # Should filter out invalid entries
        assert len(valid_cards) == 4  # 爱, 朋友, 水, 火
        hanzi_list = [card['hanzi'] for card in valid_cards]
        assert '爱' in hanzi_list
        assert '朋友' in hanzi_list
        assert '水' in hanzi_list
        assert '火' in hanzi_list
        assert 'hello' not in hanzi_list


class TestDictionaryFileIntegration:
    """Test dictionary file loading and integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_mini_dictionary_loading(self):
        """Test mini dictionary loading and usage."""
        # Test loading from data directory
        dict_obj = create_default_dict("data")
        stats = dict_obj.get_statistics()
        
        assert stats['mini_dict_entries'] > 0
        
        # Test lookup functionality
        translation = dict_obj.lookup_translation("爱")
        assert translation
        assert "love" in translation.lower()
        
        # Test word info
        info = dict_obj.get_word_info("爱")
        assert info['source'] in ['mini_dict', 'cedict']
    
    def test_custom_dictionary_creation(self):
        """Test creating and using custom dictionary."""
        # Create custom mini dictionary
        custom_dict = {
            "测试": ["test", "testing"],
            "示例": ["example", "sample"],
            "集成": ["integration", "integrate"]
        }
        
        custom_dict_path = Path(self.temp_dir) / "mini_cedict.json"
        with open(custom_dict_path, 'w', encoding='utf-8') as f:
            json.dump(custom_dict, f, ensure_ascii=False, indent=2)
        
        # Create ChineseDict with custom dictionary
        dict_obj = create_default_dict(str(self.temp_dir))
        
        # Test lookup
        translation = dict_obj.lookup_translation("测试")
        assert translation
        assert "test" in translation
        
        # Test with cards
        cards = [
            {'hanzi': '测试', 'pinyin': '', 'english': ''},
            {'hanzi': '示例', 'pinyin': '', 'english': ''},
            {'hanzi': '集成', 'pinyin': '', 'english': ''}
        ]
        
        processed_cards = generate_missing_data(
            cards, auto_pinyin=True, auto_translate=True,
            dictionary=dict_obj
        )
        
        # Verify translations from custom dictionary
        hanzi_to_card = {card['hanzi']: card for card in processed_cards}
        assert 'test' in hanzi_to_card['测试']['english']
        assert 'example' in hanzi_to_card['示例']['english']
        assert 'integration' in hanzi_to_card['集成']['english']
    
    def test_dictionary_fallback_behavior(self):
        """Test dictionary fallback when words not found."""
        dict_obj = create_default_dict("data")
        
        # Test with words likely not in dictionary
        rare_cards = [
            {'hanzi': '罕见词汇', 'pinyin': '', 'english': ''},
            {'hanzi': '不存在', 'pinyin': '', 'english': ''},
        ]
        
        processed_cards = generate_missing_data(
            rare_cards, auto_pinyin=True, auto_translate=True,
            dictionary=dict_obj
        )
        
        # Should still generate pinyin even if translation not found
        for card in processed_cards:
            assert card['pinyin']  # Pinyin should always be generated
            # English might be empty if not in dictionary


class TestExportFileIntegration:
    """Test export file generation and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sample_cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
            {'hanzi': '水', 'pinyin': 'shuǐ', 'english': 'water'},
            {'hanzi': '火', 'pinyin': 'huǒ', 'english': 'fire'},
        ]
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_pptx_file_generation_and_validation(self):
        """Test PPTX file generation and structure validation."""
        # Generate PPTX content
        pptx_content = export_cards(
            self.sample_cards, 'pptx',
            page_size='A4', card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0
        )
        
        # Save to file
        pptx_path = Path(self.temp_dir) / "test_output.pptx"
        with open(pptx_path, 'wb') as f:
            f.write(pptx_content)
        
        # Validate PPTX structure (PPTX is a ZIP file)
        assert pptx_path.exists()
        assert pptx_path.stat().st_size > 1000
        
        # Verify it's a valid ZIP file
        with ZipFile(pptx_path, 'r') as zip_file:
            file_list = zip_file.namelist()
            # PPTX should contain these essential files
            assert '[Content_Types].xml' in file_list
            assert any('slide' in f for f in file_list)
            assert any('presentation.xml' in f for f in file_list)
    
    def test_pdf_file_generation_and_validation(self):
        """Test PDF file generation and validation."""
        # Generate PDF content
        pdf_content = export_cards(
            self.sample_cards, 'pdf',
            page_size='A4', card_size_cm=5.5, gap_cm=0.5, margin_cm=1.0
        )
        
        # Save to file
        pdf_path = Path(self.temp_dir) / "test_output.pdf"
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        # Validate PDF structure
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 1000
        
        # Basic PDF validation (should start with %PDF)
        with open(pdf_path, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF'
    
    def test_large_dataset_export(self):
        """Test export with large number of cards."""
        # Generate large dataset
        large_cards = []
        for i in range(100):  # 100 cards = multiple pages
            large_cards.append({
                'hanzi': f'字{i}',
                'pinyin': f'zì{i}',
                'english': f'character{i}'
            })
        
        # Test PPTX export
        pptx_content = export_cards(large_cards, 'pptx')
        assert len(pptx_content) > 10000  # Should be substantial
        
        # Test PDF export
        pdf_content = export_cards(large_cards, 'pdf')
        assert len(pdf_content) > 10000  # Should be substantial
        
        # Save and validate files
        pptx_path = Path(self.temp_dir) / "large_output.pptx"
        pdf_path = Path(self.temp_dir) / "large_output.pdf"
        
        with open(pptx_path, 'wb') as f:
            f.write(pptx_content)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_content)
        
        assert pptx_path.exists()
        assert pdf_path.exists()
    
    def test_export_with_special_characters(self):
        """Test export with special characters and edge cases."""
        special_cards = [
            {'hanzi': '你好！', 'pinyin': 'nǐ hǎo!', 'english': 'hello!'},
            {'hanzi': '测试"引号"', 'pinyin': 'cè shì', 'english': 'test "quotes"'},
            {'hanzi': '换行\n测试', 'pinyin': 'huàn háng', 'english': 'newline\ntest'},
            {'hanzi': '特殊字符@#$', 'pinyin': 'tè shū', 'english': 'special@#$'},
        ]
        
        # Should handle special characters without crashing
        pptx_content = export_cards(special_cards, 'pptx')
        pdf_content = export_cards(special_cards, 'pdf')
        
        assert isinstance(pptx_content, (bytes, bytearray))
        assert isinstance(pdf_content, (bytes, bytearray))
        assert len(pptx_content) > 1000
        assert len(pdf_content) > 1000


class TestTemporaryFileHandling:
    """Test temporary file handling and cleanup."""
    
    def test_temporary_file_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]
        
        # Get initial temp file count
        temp_dir = tempfile.gettempdir()
        initial_files = set(os.listdir(temp_dir))
        
        # Generate multiple exports
        for _ in range(5):
            pptx_content = export_cards(cards, 'pptx')
            pdf_content = export_cards(cards, 'pdf')
            assert pptx_content
            assert pdf_content
        
        # Check that no temp files are left behind
        final_files = set(os.listdir(temp_dir))
        new_files = final_files - initial_files
        
        # Filter for files that might be related to our exports
        export_related = [f for f in new_files if 'pptx' in f or 'pdf' in f]
        assert len(export_related) == 0, f"Temporary files not cleaned up: {export_related}"
    
    def test_export_error_handling_and_cleanup(self):
        """Test that temporary files are cleaned up even when errors occur."""
        # Test with invalid parameters that might cause errors
        cards = [{'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'}]

        # Get initial temp file count for our specific pattern
        temp_dir = tempfile.gettempdir()
        initial_files = set(os.listdir(temp_dir))

        # This should work normally
        content = export_cards(cards, 'pptx', card_size_cm=5.5)
        assert content

        # Test with potentially problematic parameters
        try:
            # Very small card size might cause issues
            content = export_cards(cards, 'pptx', card_size_cm=0.1)
            assert content  # Should still work or handle gracefully
        except Exception:
            pass  # If it fails, that's okay, but shouldn't leave temp files

        # Verify no new temp files left behind
        final_files = set(os.listdir(temp_dir))
        new_files = final_files - initial_files
        export_related = [f for f in new_files if 'pptx' in f or 'pdf' in f]
        assert len(export_related) == 0, f"Temporary files not cleaned up: {export_related}"
