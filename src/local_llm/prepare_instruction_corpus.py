from __future__ import annotations

import argparse
import json
from pathlib import Path

from local_llm.prepare_sft_corpus import ChatExample, render_example


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert instruction JSONL into Ares SFT corpus and mask files.")
    parser.add_argument("--input", type=Path, required=True, help="JSONL with instruction/input/output fields.")
    parser.add_argument("--output", type=Path, default=Path("data/ares_instruction_sft.txt"))
    parser.add_argument("--mask-output", type=Path, default=Path("data/ares_instruction_sft_mask.json"))
    return parser.parse_args()


def instruction_to_example(item: dict[str, object]) -> ChatExample:
    instruction = str(item.get("instruction") or item.get("prompt") or item.get("user") or "").strip()
    extra_input = str(item.get("input") or "").strip()
    output = str(item.get("output") or item.get("response") or item.get("assistant") or "").strip()
    if not instruction or not output:
        raise ValueError("Instruction rows need instruction/prompt/user and output/response/assistant text.")
    user = instruction if not extra_input else f"{instruction}\n\nInput:\n{extra_input}"
    return ChatExample(user=user, assistant=output)


def load_instruction_examples(path: Path) -> list[ChatExample]:
    examples = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            examples.append(instruction_to_example(json.loads(line)))
        except Exception as exc:
            raise ValueError(f"Invalid instruction row {line_number}: {exc}") from exc
    if not examples:
        raise ValueError(f"No instruction examples found in {path}.")
    return examples


def render_instruction_corpus(examples: list[ChatExample]) -> tuple[str, list[int]]:
    chunks: list[str] = []
    mask: list[int] = []
    for example in examples:
        text, example_mask = render_example(example)
        chunks.append(text)
        mask.extend(example_mask)
    corpus = "".join(chunks)
    if len(corpus) != len(mask):
        raise RuntimeError(f"Instruction corpus and mask length mismatch: {len(corpus)} != {len(mask)}")
    return corpus, mask


def main() -> None:
    args = parse_args()
    examples = load_instruction_examples(args.input)
    corpus, mask = render_instruction_corpus(examples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.mask_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(corpus, encoding="utf-8")
    args.mask_output.write_text(
        json.dumps({"format": "instruction-jsonl assistant-only mask", "mask": mask}),
        encoding="utf-8",
    )
    print(f"Wrote {len(examples)} instruction examples to {args.output}")
    print(f"Wrote assistant-only mask to {args.mask_output}")


if __name__ == "__main__":
    main()
