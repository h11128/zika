import os
import io
import csv
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.gen_cards import CardGenerator


def make_temp_csv(rows, delimiter=","):
    fd, path = tempfile.mkstemp(suffix=".csv")
    os.close(fd)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["hanzi", "pinyin", "english"])  # header
        writer.writerows(rows)
    return path


def test_read_input_file_csv_and_tsv_detection():
    # CSV
    csv_path = make_temp_csv([["爱", "", "love"], ["abc", "", "not chinese" ]])
    try:
        gen = CardGenerator()
        cards = gen.read_input_file(csv_path)
        # Non-Chinese line should be skipped
        assert any(c["hanzi"] == "爱" for c in cards)
        assert all("abc" != c["hanzi"] for c in cards)
    finally:
        os.remove(csv_path)

    # TSV
    tsv_fd, tsv_path = tempfile.mkstemp(suffix=".tsv")
    os.close(tsv_fd)
    try:
        with open(tsv_path, "w", encoding="utf-8") as f:
            f.write("hanzi\tpinyin\tenglish\n朋友\t\tfriend\n")
        gen = CardGenerator()
        cards = gen.read_input_file(tsv_path)
        assert cards and cards[0]["hanzi"] == "朋友"
    finally:
        os.remove(tsv_path)


def test_process_cards_autofill_pinyin_and_translation():
    gen = CardGenerator()
    cards = [{"hanzi": "爱", "pinyin": "", "english": ""}]
    processed = gen.process_cards(cards, auto_pinyin=True, auto_translate=True, heteronym=False)
    assert processed[0]["pinyin"]  # pinyin generated
    assert processed[0]["english"]  # translation generated from mini dict


@patch("src.gen_cards.PPTXCardGenerator")
@patch("src.gen_cards.PDFCardGenerator")
def test_generate_output_routes_and_unsupported(mock_pdf, mock_pptx):
    gen = CardGenerator()

    # Mock successful generators
    mock_pptx.return_value.generate_pptx.return_value = True
    mock_pdf.return_value.generate_pdf.return_value = True

    cards = [{"hanzi": "爱", "pinyin": "ai4", "english": "love"}]

    # PPTX
    ok = gen.generate_output(cards, "out/test_cards.pptx", "pptx", page_size="A4")
    assert ok
    mock_pptx.assert_called()

    # PDF
    ok = gen.generate_output(cards, "out/test_cards.pdf", "pdf", page_size="A4")
    assert ok
    mock_pdf.assert_called()

    # Unsupported
    ok = gen.generate_output(cards, "out/test.txt", "txt")
    assert ok is False

    # Exception path
    mock_pptx.return_value.generate_pptx.side_effect = Exception("boom")
    ok = gen.generate_output(cards, "out/test_cards.pptx", "pptx")
    assert ok is False


# Additional coverage tests for gen_cards.py CardGenerator class
def test_card_generator_initialization():
    """Test CardGenerator initialization."""
    gen = CardGenerator()
    assert gen is not None
    assert hasattr(gen, 'dictionary')


def test_card_generator_with_dict_path():
    """Test CardGenerator with custom dictionary path."""
    # Test with non-existent path
    gen = CardGenerator(dict_path="/non/existent/path")
    assert gen is not None

    # Test with None path
    gen = CardGenerator(dict_path=None)
    assert gen is not None


def test_card_generator_read_input_file_error_handling():
    """Test CardGenerator read_input_file error handling."""
    gen = CardGenerator()

    # Test with non-existent file - should raise SystemExit
    with pytest.raises(SystemExit):
        gen.read_input_file("/non/existent/file.csv")


def test_card_generator_process_cards_empty():
    """Test CardGenerator process_cards with empty input."""
    gen = CardGenerator()
    result = gen.process_cards([], auto_pinyin=True, auto_translate=True)
    assert result == []


def test_card_generator_generate_output_invalid_format():
    """Test CardGenerator generate_output with invalid format."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "ni3hao3", "english": "hello"}]

    # Test with invalid format
    result = gen.generate_output(cards, "test.invalid", "invalid_format")
    assert result is False


# Additional high-priority tests for src/gen_cards.py core business logic
def test_card_generator_process_cards_translation_fallback():
    """Test translation fallback from dictionary to Google Translate."""
    gen = CardGenerator()
    cards = [{"hanzi": "测试", "pinyin": "", "english": ""}]

    with patch.object(gen.dictionary, 'lookup_translation') as mock_lookup, \
         patch('src.gen_cards.translate_with_google') as mock_google, \
         patch('src.gen_cards.clean_english_text') as mock_clean:

        # Dictionary lookup fails
        mock_lookup.side_effect = Exception("Dictionary error")
        mock_google.return_value = "test"
        mock_clean.return_value = "test"

        result = gen.process_cards(cards, auto_pinyin=False, auto_translate=True)

        # Should fallback to Google Translate
        assert result[0]['english'] == "test"
        mock_google.assert_called_once_with("测试")


def test_card_generator_process_cards_no_translation_found():
    """Test handling when no translation is found."""
    gen = CardGenerator()
    cards = [{"hanzi": "测试", "pinyin": "", "english": ""}]

    with patch.object(gen.dictionary, 'lookup_translation') as mock_lookup, \
         patch('src.gen_cards.translate_with_google') as mock_google:

        # Both dictionary and Google fail
        mock_lookup.return_value = None
        mock_google.return_value = None

        result = gen.process_cards(cards, auto_pinyin=False, auto_translate=True)

        # Should leave english field empty
        assert result[0]['english'] == ""


def test_card_generator_process_cards_pinyin_generation():
    """Test pinyin generation functionality."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "", "english": ""}]

    with patch('src.gen_cards.hanzi_to_pinyin') as mock_pinyin:
        mock_pinyin.return_value = "ni3 hao3"

        result = gen.process_cards(cards, auto_pinyin=True, auto_translate=False)

        # Should generate pinyin
        assert result[0]['pinyin'] == "ni3 hao3"
        mock_pinyin.assert_called_once_with("你好", heteronym=False)


def test_card_generator_process_cards_existing_data_preservation():
    """Test that existing pinyin/english data is preserved."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "existing_pinyin", "english": "existing_english"}]

    with patch('src.gen_cards.hanzi_to_pinyin') as mock_pinyin, \
         patch.object(gen.dictionary, 'lookup_translation') as mock_lookup:

        mock_pinyin.return_value = "ni3 hao3"
        mock_lookup.return_value = "hello"

        result = gen.process_cards(cards, auto_pinyin=True, auto_translate=True)

        # Should preserve existing data
        assert result[0]['pinyin'] == "existing_pinyin"
        assert result[0]['english'] == "existing_english"
        # Should not call generation functions
        mock_pinyin.assert_not_called()
        mock_lookup.assert_not_called()


def test_card_generator_generate_output_pptx_success():
    """Test successful PPTX generation."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "ni3hao3", "english": "hello"}]

    with patch('src.gen_cards.PPTXCardGenerator') as mock_pptx_class:
        mock_pptx = mock_pptx_class.return_value
        mock_pptx.generate_pptx.return_value = True

        result = gen.generate_output(cards, "test.pptx", "pptx")

        # Should succeed
        assert result is True
        mock_pptx.generate_pptx.assert_called_once()


def test_card_generator_generate_output_pdf_success():
    """Test successful PDF generation."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "ni3hao3", "english": "hello"}]

    with patch('src.gen_cards.PDFCardGenerator') as mock_pdf_class:
        mock_pdf = mock_pdf_class.return_value
        mock_pdf.generate_pdf.return_value = True

        result = gen.generate_output(cards, "test.pdf", "pdf")

        # Should succeed
        assert result is True
        mock_pdf.generate_pdf.assert_called_once()


def test_card_generator_generate_output_exception_handling():
    """Test exception handling in output generation."""
    gen = CardGenerator()
    cards = [{"hanzi": "你好", "pinyin": "ni3hao3", "english": "hello"}]

    with patch('src.gen_cards.PPTXCardGenerator') as mock_pptx_class:
        mock_pptx = mock_pptx_class.return_value
        mock_pptx.generate_pptx.side_effect = Exception("Generation failed")

        result = gen.generate_output(cards, "test.pptx", "pptx")

        # Should handle exception and return False
        assert result is False


def test_card_generator_find_column_functionality():
    """Test _find_column helper method."""
    gen = CardGenerator()

    # Test finding exact match
    fieldnames = ['hanzi', 'pinyin', 'english']
    result = gen._find_column(fieldnames, ['hanzi', 'chinese'])
    assert result == 'hanzi'

    # Test finding alternative match
    fieldnames = ['chinese', 'pronunciation', 'meaning']
    result = gen._find_column(fieldnames, ['hanzi', 'chinese'])
    assert result == 'chinese'

    # Test no match found
    fieldnames = ['col1', 'col2', 'col3']
    result = gen._find_column(fieldnames, ['hanzi', 'chinese'])
    assert result is None


def test_card_generator_csv_delimiter_detection():
    """Test CSV delimiter detection functionality."""
    import tempfile
    import os

    gen = CardGenerator()

    # Create temporary TSV file
    fd, tsv_path = tempfile.mkstemp(suffix=".tsv")
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write("hanzi\tpinyin\tenglish\n你好\tni3hao3\thello\n")

        cards = gen.read_input_file(tsv_path)

        # Should correctly parse TSV
        assert len(cards) == 1
        assert cards[0]['hanzi'] == '你好'
        assert cards[0]['pinyin'] == 'ni3hao3'
        assert cards[0]['english'] == 'hello'

    finally:
        if os.path.exists(tsv_path):
            os.remove(tsv_path)

