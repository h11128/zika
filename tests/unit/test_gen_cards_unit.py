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

