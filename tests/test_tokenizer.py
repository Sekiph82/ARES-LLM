from local_llm.tokenizer import CharTokenizer


def test_char_tokenizer_round_trip() -> None:
    tokenizer = CharTokenizer.from_text("hello local llm")

    ids = tokenizer.encode("local")

    assert tokenizer.decode(ids) == "local"
    assert tokenizer.vocab_size == len(set("hello local llm"))
