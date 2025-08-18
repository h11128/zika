import os
import sys
import types
import tempfile
from pathlib import Path
from unittest.mock import patch

import src.gen_cards as gc


def test_main_missing_input_exits(monkeypatch):
    argv = ["gen_cards.py", "--in", "nonexistent.csv", "--out", "out.pptx", "--format", "pptx"]
    monkeypatch.setattr(sys, "argv", argv)

    called = {"code": None}
    def fake_exit(code=0):
        called["code"] = code
        raise SystemExit(code)

    monkeypatch.setattr(sys, "exit", fake_exit)

    try:
        gc.main()
        assert False, "Expected SystemExit"
    except SystemExit:
        pass

    assert called["code"] == 1


def test_main_success_flow(monkeypatch, tmp_path):
    # Create temp CSV
    csv_path = tmp_path / "words.csv"
    csv_path.write_text("hanzi,pinyin,english\n你,,you\n", encoding="utf-8")
    out_path = tmp_path / "out.pptx"

    argv = ["gen_cards.py", "--in", str(csv_path), "--out", str(out_path), "--format", "pptx"]
    monkeypatch.setattr(sys, "argv", argv)

    # Patch generator to avoid heavy work
    class DummyGen:
        def __init__(self, *a, **k): pass
        def generate_pptx(self, *a, **k): return True
    monkeypatch.setattr(gc, "PPTXCardGenerator", lambda *a, **k: DummyGen())

    # Ensure sys.exit is not called on success
    def forbid_exit(*a, **k):
        raise AssertionError("sys.exit should not be called on success")
    monkeypatch.setattr(sys, "exit", forbid_exit)

    gc.main()

