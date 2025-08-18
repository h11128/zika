import os
import gzip
from src.extract_cedict import extract_cedict


def test_extract_cedict_missing_file(monkeypatch):
    # Ensure function returns False if input missing
    monkeypatch.setattr("os.path.exists", lambda p: False)
    assert extract_cedict() is False


def test_extract_cedict_happy_path(tmp_path, monkeypatch):
    # Create data directory and place gz file according to function's expected paths
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    gz_path = data_dir / "cedict_ts.u8"
    out_txt = data_dir / "cedict_ts.txt"

    content = "朋友 朋友 [peng2 you3] /friend/\n"
    with gzip.open(gz_path, "wt", encoding="utf-8") as f:
        f.write(content)

    # Change working directory so default relative paths resolve to our tmp data dir
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ok = extract_cedict()
    finally:
        os.chdir(old_cwd)

    assert ok is True
    # Output file should be created with some content
    assert out_txt.exists()
    assert out_txt.read_text(encoding="utf-8").strip()

