import services.translation as tr


def test_combine_translations_smart_combines_groups():
    t1 = "run; jog"
    t2 = "sprint"
    combined = tr.combine_translations_smart(t1, t2)
    assert combined in ("run; jog | sprint", "sprint | run; jog")


def test_combine_translations_smart_dedup_case_insensitive():
    t1 = "Run"
    t2 = "run"
    combined = tr.combine_translations_smart(t1, t2)
    assert combined == "Run" or combined == "run"


def test_translate_with_strategy_mixed_combines(monkeypatch):
    class MockDict:
        def lookup_translation(self, text):
            return "run; jog"

    def fake_google(text):
        return "sprint"

    monkeypatch.setattr(tr, "translate_with_google", fake_google)

    out = tr.translate_with_strategy("测试", dictionary=MockDict(), strategy="mixed")
    assert out in ("run; jog | sprint", "sprint | run; jog")


def test_clean_english_text_keeps_non_chinese_brackets():
    raw = "hello (test) [note]"
    cleaned = tr.clean_english_text(raw)
    # no Chinese inside brackets, so keep content; normalize spaces
    assert cleaned == "hello (test) [note]"

