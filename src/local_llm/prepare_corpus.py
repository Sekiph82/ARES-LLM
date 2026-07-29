from __future__ import annotations

import argparse
from pathlib import Path

from local_llm.repo_context import collect_repo_files


ARES_PREAMBLE = """Ares is a local coding assistant project.
Ares combines a pretrained Ollama coding model with a small from-scratch PyTorch language model.
Ares should be careful, practical, and honest about what it can and cannot do.
Ares reads repository files, explains code, proposes small patches, and helps run local training experiments.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a plain text corpus for Ares scratch-model training.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("data/ares_corpus.txt"))
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--max-chars-per-file", type=int, default=10000)
    return parser.parse_args()


def build_corpus(repo: Path, max_files: int, max_chars_per_file: int) -> str:
    files = collect_repo_files(repo, max_files=max_files, max_chars_per_file=max_chars_per_file)
    chunks = [ARES_PREAMBLE.strip()]
    for file in files:
        chunks.append(f"\n\n# File: {file.path.as_posix()}\n{file.text.strip()}")
    return "\n".join(chunks).strip() + "\n"


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    output = args.output
    if not output.is_absolute():
        output = repo / output
    output.parent.mkdir(parents=True, exist_ok=True)
    corpus = build_corpus(repo, args.max_files, args.max_chars_per_file)
    output.write_text(corpus, encoding="utf-8")
    print(f"Wrote {len(corpus):,} characters to {output}")


if __name__ == "__main__":
    main()
