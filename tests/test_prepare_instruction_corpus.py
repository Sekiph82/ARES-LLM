import json

from local_llm.prepare_instruction_corpus import (
    instruction_to_example,
    load_instruction_examples,
    render_instruction_corpus,
)


def test_instruction_to_example_combines_optional_input() -> None:
    example = instruction_to_example({"instruction": "Summarize", "input": "Ares code", "output": "Done"})

    assert "Input:" in example.user
    assert example.assistant == "Done"


def test_render_instruction_corpus_has_aligned_mask(tmp_path) -> None:
    input_path = tmp_path / "instructions.jsonl"
    input_path.write_text(
        json.dumps({"instruction": "Say hi", "output": "Hi."}) + "\n",
        encoding="utf-8",
    )

    examples = load_instruction_examples(input_path)
    corpus, mask = render_instruction_corpus(examples)

    assert len(corpus) == len(mask)
    assert sum(mask) == len("Hi.<|endoftext|>")
