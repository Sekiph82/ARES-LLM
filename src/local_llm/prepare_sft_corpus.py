from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from local_llm.prepare_corpus import build_corpus


EOT = "<|endoftext|>"


@dataclass(frozen=True)
class ChatExample:
    user: str
    assistant: str


BASE_EXAMPLES = [
    ChatExample(
        user="What is Ares?",
        assistant=(
            "Ares is a local coding workspace. It uses a strong local Ollama coding model for real project work "
            "and a tiny PyTorch model for transparent training experiments."
        ),
    ),
    ChatExample(
        user="Should you edit files without showing the user what changed?",
        assistant=(
            "No. For coding work, Ares should inspect the repository, keep edits scoped, preview risky changes, "
            "run tests when possible, and explain the result clearly."
        ),
    ),
    ChatExample(
        user="Create a website/app when the user asks for a dashboard, landing page, app, portal, or tool.",
        assistant=(
            "I will route that request to the website/app builder, create a runnable local artifact, and keep the UI "
            "polished, responsive, and appropriate for the user's domain."
        ),
    ),
    ChatExample(
        user="How should Ares learn from local shop or project context?",
        assistant=(
            "Ares should save durable lessons in local memory and use approved training examples for experiments. "
            "It should not silently retrain itself forever without evaluation."
        ),
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a chat/SFT corpus and assistant-only loss mask for Ares.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("data/ares_sft_corpus.txt"))
    parser.add_argument("--mask-output", type=Path, default=Path("data/ares_sft_mask.json"))
    parser.add_argument("--max-files", type=int, default=20)
    parser.add_argument("--max-chars-per-file", type=int, default=4000)
    return parser.parse_args()


def render_example(example: ChatExample) -> tuple[str, list[int]]:
    user_header = "<|user|>\n"
    assistant_header = "<|assistant|>\n"
    text = f"{user_header}{example.user}{EOT}{assistant_header}{example.assistant}{EOT}\n"
    mask = (
        [0] * len(user_header)
        + [0] * len(example.user)
        + [0] * len(EOT)
        + [0] * len(assistant_header)
        + [1] * len(example.assistant)
        + [1] * len(EOT)
        + [0]
    )
    return text, mask


def build_sft_corpus(repo: Path, max_files: int, max_chars_per_file: int) -> tuple[str, list[int]]:
    examples = list(BASE_EXAMPLES)
    repo_context = build_corpus(repo, max_files=max_files, max_chars_per_file=max_chars_per_file)
    examples.append(
        ChatExample(
            user="Summarize the current Ares repository context.",
            assistant=repo_context[:12000],
        )
    )

    chunks: list[str] = []
    mask: list[int] = []
    for example in examples:
        text, example_mask = render_example(example)
        chunks.append(text)
        mask.extend(example_mask)
    corpus = "".join(chunks)
    if len(corpus) != len(mask):
        raise RuntimeError(f"SFT corpus and mask length mismatch: {len(corpus)} != {len(mask)}")
    return corpus, mask


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    output = args.output if args.output.is_absolute() else repo / args.output
    mask_output = args.mask_output if args.mask_output.is_absolute() else repo / args.mask_output
    output.parent.mkdir(parents=True, exist_ok=True)
    mask_output.parent.mkdir(parents=True, exist_ok=True)

    corpus, mask = build_sft_corpus(repo, args.max_files, args.max_chars_per_file)
    output.write_text(corpus, encoding="utf-8")
    mask_output.write_text(
        json.dumps(
            {
                "format": "char-level assistant-only mask",
                "source": str(repo),
                "text_path": str(output),
                "assistant_chars": int(sum(mask)),
                "total_chars": len(mask),
                "mask": mask,
            }
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(corpus):,} SFT characters to {output}")
    print(f"Wrote assistant-only mask to {mask_output}")


if __name__ == "__main__":
    main()
