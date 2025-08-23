import services.export as ex


class DummyGen:
    def __init__(self, *a, **k):
        pass

    def generate_pptx(self, cards, path, **opts):
        with open(path, "wb") as f:
            f.write(b"ok")
        return True


def test_export_cards_cleanup_oserror(monkeypatch):
    # Use dummy generator to ensure a file exists
    monkeypatch.setattr(ex, "PPTXCardGenerator", DummyGen)

    # Make os.unlink raise to cover the cleanup exception handler
    def boom(path):
        raise OSError("unlink failed")

    monkeypatch.setattr(ex.os, "unlink", boom)

    content = ex.export_cards([{"hanzi": "测"}], "pptx")
    assert content == b"ok"

