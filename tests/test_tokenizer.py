from local_llm.tokenizer import BPETokenizer, CharTokenizer, load_tokenizer


def test_char_tokenizer_round_trip() -> None:
    tokenizer = CharTokenizer.from_text("hello local llm")

    ids = tokenizer.encode("local")

    assert tokenizer.decode(ids) == "local"
    assert tokenizer.vocab_size == len(set("hello local llm"))


def test_bpe_tokenizer_round_trip_and_save(tmp_path) -> None:
    tokenizer = BPETokenizer.train("low lower lowest local local", vocab_size=18)

    ids, spans = tokenizer.encode_with_spans("lower local")
    assert tokenizer.decode(ids) == "lower local"
    assert len(ids) == len(spans)
    assert tokenizer.vocab_size > len(set("low lower lowest local local"))

    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    loaded = load_tokenizer(path)

    assert loaded.decode(loaded.encode("lower local")) == "lower local"
