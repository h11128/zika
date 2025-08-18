import os
import sys
import tempfile
import unittest

# Ensure project root is on sys.path for imports like `from src...` and `from services...`
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.dict_utils import create_default_dict
from services.processing import parse_input_text, auto_segment_text, generate_missing_data
from services.export import export_cards
from services import cache as preview_cache


class TestDictUtils(unittest.TestCase):
    def test_lookup_mini_dict(self):
        d = create_default_dict("data")
        # Mini dict should be loaded
        stats = d.get_statistics()
        self.assertGreater(stats['mini_dict_entries'], 0, "mini_cedict.json should be loaded")
        # Lookup a known word
        trans = d.lookup_translation("爱")
        self.assertIsNotNone(trans)
        self.assertIn("love", trans)


class TestProcessingFlow(unittest.TestCase):
    def test_parse_and_generate_missing_data(self):
        text = "爱 朋友 水"
        cards = parse_input_text(text)
        self.assertEqual(len(cards), 3)
        d = create_default_dict("data")
        processed = generate_missing_data(cards, auto_pinyin=True, auto_translate=True, dictionary=d)
        # Check each card has pinyin and english filled
        for c in processed:
            self.assertTrue(c['pinyin'], f"Missing pinyin for {c['hanzi']}")
            self.assertTrue(c['english'], f"Missing translation for {c['hanzi']}")

    def test_auto_segment_text_basic(self):
        segmented = auto_segment_text("我爱我的家人朋友们")
        self.assertIsInstance(segmented, str)
        self.assertGreater(len(segmented.split()), 0)


class TestExportService(unittest.TestCase):
    def setUp(self):
        self.cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
        ]

    def test_export_pptx(self):
        content = export_cards(self.cards, 'pptx', page_size='A4', card_size=5.5, gap=0.5, margin=1.0)
        self.assertIsInstance(content, (bytes, bytearray))
        self.assertGreater(len(content), 0)

    def test_export_pdf(self):
        content = export_cards(self.cards, 'pdf', page_size='A4', card_size=5.5, gap=0.5, margin=1.0)
        self.assertIsInstance(content, (bytes, bytearray))
        self.assertGreater(len(content), 0)


class TestPreviewHTML(unittest.TestCase):
    def setUp(self):
        self.cards = [
            {'hanzi': '爱', 'pinyin': 'ài', 'english': 'love'},
            {'hanzi': '家', 'pinyin': 'jiā', 'english': 'home'},
            {'hanzi': '朋友', 'pinyin': 'péng yǒu', 'english': 'friend'},
            {'hanzi': '水', 'pinyin': 'shuǐ', 'english': 'water'},
            {'hanzi': '火', 'pinyin': 'huǒ', 'english': 'fire'},
            {'hanzi': '山', 'pinyin': 'shān', 'english': 'mountain'},
        ]

    def test_simple_grid_html_contains_color(self):
        color = '#E3F2FD'
        html = preview_cache.create_simple_grid_html(self.cards, hanzi_font='Microsoft YaHei', background_color=color)
        self.assertIn(color, html)
        self.assertIn('simple-card', html)

    def test_page_preview_html_contains_color(self):
        color = '#E3F2FD'
        html = preview_cache.create_page_preview_html(
            self.cards, page_num=0,
            card_size=5.5, gap=0.5, margin=1.0,
            font_hanzi=48, font_pinyin=18, font_english=14,
            page_size='A4', hanzi_font='Microsoft YaHei', background_color=color,
            rows=3, cols=3, auto_fill=True
        )
        self.assertIn(color, html)
        self.assertIn('page-card', html)


if __name__ == '__main__':
    unittest.main()

