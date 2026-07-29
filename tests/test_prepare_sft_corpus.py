from local_llm.prepare_sft_corpus import ChatExample, build_sft_corpus, render_example


def test_render_example_masks_only_assistant_text() -> None:
    text, mask = render_example(ChatExample(user="Question?", assistant="Answer."))

    assert len(text) == len(mask)
    assert sum(mask) == len("Answer.<|endoftext|>")
    assert text.startswith("<|user|>")
    assert "<|assistant|>" in text


def test_build_sft_corpus_has_aligned_mask(tmp_path) -> None:
    (tmp_path / "sample.py").write_text("def hello():\n    return 'hi'\n", encoding="utf-8")

    text, mask = build_sft_corpus(tmp_path, max_files=2, max_chars_per_file=1000)

    assert len(text) == len(mask)
    assert sum(mask) > 0
    assert "Summarize the current Ares repository context." in text
