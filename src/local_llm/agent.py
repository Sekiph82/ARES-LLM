from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from local_llm.agent_core import DEFAULT_MODEL, MODE_INSTRUCTIONS, ask_agent
from local_llm.patches import extract_unified_diffs, save_patches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ask a local Ollama coding model about this repository.")
    parser.add_argument("task", nargs="+", help="Coding task or question.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--mode", default="answer", choices=sorted(MODE_INSTRUCTIONS))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--max-files", type=int, default=40)
    parser.add_argument("--max-chars-per-file", type=int, default=6000)
    parser.add_argument("--max-total-chars", type=int, default=60000)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--num-ctx", type=int, default=8192)
    parser.add_argument("--save", action="store_true", help="Save the model response under runs/agent.")
    parser.add_argument("--save-patches", action="store_true", help="Extract diff blocks into .patch files.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo = args.repo.resolve()
    task = " ".join(args.task)

    result = ask_agent(
        max_files=args.max_files,
        max_chars_per_file=args.max_chars_per_file,
        max_total_chars=args.max_total_chars,
        model=args.model,
        mode=args.mode,
        repo=repo,
        task=task,
        temperature=args.temperature,
        num_ctx=args.num_ctx,
    )
    print(result.response)
    print(
        f"\n[Ares session {result.session.id}] "
        f"context files: {result.included_files}/{result.total_files}, "
        f"estimated tokens: prompt {result.session.estimated_prompt_tokens}, "
        f"response {result.session.estimated_response_tokens}"
    )

    if args.save:
        out_dir = repo / "runs" / "agent"
        out_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = out_dir / f"response-{timestamp}.md"
        out_path.write_text(result.response, encoding="utf-8")
        print(f"\nSaved response to {out_path}")
    if args.save_patches:
        bundle = extract_unified_diffs(result.response)
        paths = save_patches(bundle, repo / "runs" / "agent" / "patches", result.session.id)
        if paths:
            print("\nSaved patches:")
            for path in paths:
                print(path)
        else:
            print("\nNo unified diff blocks found to save.")


if __name__ == "__main__":
    main()
