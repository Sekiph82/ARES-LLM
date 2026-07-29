from local_llm.prepare_public_domain_corpus import clean_gutenberg_text


def test_clean_gutenberg_text_removes_boilerplate() -> None:
    raw = """Header
*** START OF THE PROJECT GUTENBERG EBOOK DEMO ***

Chapter 1


Hello   world.

*** END OF THE PROJECT GUTENBERG EBOOK DEMO ***
Footer
"""

    cleaned = clean_gutenberg_text(raw)

    assert "START OF" not in cleaned
    assert "END OF" not in cleaned
    assert "Hello world." in cleaned
