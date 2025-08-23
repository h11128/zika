import services.translation as tr


def test_clean_english_text_returns_none_when_no_ascii_letters():
    # Only punctuation and spaces -> should become None
    assert tr.clean_english_text("； ； ；（中文） ") is None
    assert tr.clean_english_text("   ") is None


def test_clean_english_text_removes_classifier_patterns():
    # Should remove classifier patterns like CL:| and trailing markers
    raw = "hello; CL:|abc; MW:|xyz; TW:|; ; ;"
    assert tr.clean_english_text(raw) == "hello"


def test_combine_translations_smart_containment_dedup():
    # d2 contains d1 -> should dedup and keep only one
    d1 = "to eat"
    d2 = "to eat food"
    combined = tr.combine_translations_smart(d1, d2)
    # containment should dedup, keep one of them
    assert combined in ("to eat", "to eat food")

