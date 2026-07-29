from __future__ import annotations

import argparse
from pathlib import Path

import torch

from local_llm.model import GPTConfig, GPTLanguageModel
from local_llm.tokenizer import CharTokenizer
from local_llm.utils import get_device, set_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate text from a local LLM checkpoint.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--prompt", default="\n")
    parser.add_argument("--max-new-tokens", type=int, default=100)
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)

    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=False)
    tokenizer_path = args.checkpoint.parent / checkpoint.get("tokenizer_path", "tokenizer.json")
    tokenizer = CharTokenizer.load(tokenizer_path)

    config = GPTConfig.from_dict(checkpoint["config"])
    model = GPTLanguageModel(config).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()

    prompt_ids = tokenizer.encode(args.prompt)
    idx = torch.tensor([prompt_ids], dtype=torch.long, device=device)
    output = model.generate(
        idx,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
    )
    print(tokenizer.decode(output[0].tolist()))


if __name__ == "__main__":
    main()
