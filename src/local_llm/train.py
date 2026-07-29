from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import torch
from tqdm import tqdm

from local_llm.model import GPTConfig, GPTLanguageModel
from local_llm.tokenizer import CharTokenizer
from local_llm.utils import get_device, set_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a tiny local GPT-style language model.")
    parser.add_argument("--input", type=Path, required=True, help="Plain text training file.")
    parser.add_argument("--out-dir", type=Path, default=Path("runs/tiny"), help="Checkpoint output directory.")
    parser.add_argument("--stage", choices=["pretrain", "sft"], default="pretrain")
    parser.add_argument("--sft-mask", type=Path, default=None, help="JSON mask aligned to the SFT input text.")
    parser.add_argument("--max-steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--block-size", type=int, default=128)
    parser.add_argument("--n-layer", type=int, default=4)
    parser.add_argument("--n-head", type=int, default=4)
    parser.add_argument("--n-embd", type=int, default=128)
    parser.add_argument("--dropout", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--grad-clip", type=float, default=1.0)
    parser.add_argument("--eval-interval", type=int, default=50)
    parser.add_argument("--eval-iters", type=int, default=20)
    parser.add_argument("--log-interval", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, or mps.")
    return parser.parse_args()


def serializable_args(args: argparse.Namespace) -> dict[str, str | int | float | bool]:
    return {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}


def get_batch(
    data: torch.Tensor,
    batch_size: int,
    block_size: int,
    device: torch.device,
    mask_data: torch.Tensor | None = None,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]:
    if len(data) <= block_size:
        raise ValueError("Training data must be longer than block_size.")

    for _ in range(20):
        ix = torch.randint(len(data) - block_size, (batch_size,))
        if mask_data is None:
            break
        batch_mask = torch.stack([mask_data[i + 1 : i + block_size + 1] for i in ix])
        if batch_mask.sum() > 0:
            break
    x = torch.stack([data[i : i + block_size] for i in ix])
    y = torch.stack([data[i + 1 : i + block_size + 1] for i in ix])
    if mask_data is None:
        return x.to(device), y.to(device), None
    return x.to(device), y.to(device), batch_mask.to(device)


@torch.no_grad()
def estimate_loss(
    model: GPTLanguageModel,
    train_data: torch.Tensor,
    val_data: torch.Tensor,
    batch_size: int,
    block_size: int,
    eval_iters: int,
    device: torch.device,
    train_mask: torch.Tensor | None = None,
    val_mask: torch.Tensor | None = None,
) -> dict[str, float]:
    model.eval()
    out = {}
    split_payload = {"train": (train_data, train_mask), "val": (val_data, val_mask)}
    for split, (data, mask_data) in split_payload.items():
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            x, y, loss_mask = get_batch(data, batch_size, block_size, device, mask_data)
            _, loss = model(x, y, loss_mask)
            losses[k] = loss.item()
        out[split] = losses.mean().item()
    model.train()
    return out


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    device = get_device(args.device)

    text = args.input.read_text(encoding="utf-8")
    tokenizer = CharTokenizer.from_text(text)
    encoded = torch.tensor(tokenizer.encode(text), dtype=torch.long)
    mask_tensor = load_sft_mask(args.sft_mask, len(encoded)) if args.stage == "sft" else None

    split_idx = max(1, int(0.9 * len(encoded)))
    train_data = encoded[:split_idx]
    val_data = encoded[split_idx:]
    train_mask = mask_tensor[:split_idx] if mask_tensor is not None else None
    val_mask = mask_tensor[split_idx:] if mask_tensor is not None else None
    if len(val_data) <= args.block_size:
        val_data = train_data
        val_mask = train_mask

    config = GPTConfig(
        vocab_size=tokenizer.vocab_size,
        block_size=args.block_size,
        n_layer=args.n_layer,
        n_head=args.n_head,
        n_embd=args.n_embd,
        dropout=args.dropout,
    )
    model = GPTLanguageModel(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    param_count = sum(param.numel() for param in model.parameters())
    tokens_per_step = args.batch_size * args.block_size

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tokenizer.save(args.out_dir / "tokenizer.json")

    csv_path = args.out_dir / "training_log.csv"
    progress = tqdm(range(args.max_steps), desc=f"training on {device}")
    last_losses: dict[str, float] | None = None
    metrics = []
    step_logs = []
    total_start = time.perf_counter()
    csv_file = csv_path.open("w", encoding="utf-8", newline="")
    csv_writer = csv.DictWriter(
        csv_file,
        fieldnames=[
            "step",
            "train_loss",
            "val_loss",
            "batch_loss",
            "step_ms",
            "tokens_per_sec",
            "tokens_processed",
            "elapsed_sec",
        ],
    )
    csv_writer.writeheader()

    for step in progress:
        step_start = time.perf_counter()
        eval_losses: dict[str, float | None] = {"train": None, "val": None}
        if step % args.eval_interval == 0 or step == args.max_steps - 1:
            last_losses = estimate_loss(
                model,
                train_data,
                val_data,
                args.batch_size,
                args.block_size,
                args.eval_iters,
                device,
                train_mask,
                val_mask,
            )
            progress.set_postfix(train=f"{last_losses['train']:.3f}", val=f"{last_losses['val']:.3f}")
            eval_losses = {"train": last_losses["train"], "val": last_losses["val"]}

        xb, yb, loss_mask = get_batch(train_data, args.batch_size, args.block_size, device, train_mask)
        _, loss = model(xb, yb, loss_mask)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if args.grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        optimizer.step()

        step_ms = (time.perf_counter() - step_start) * 1000
        elapsed_sec = time.perf_counter() - total_start
        tokens_processed = (step + 1) * tokens_per_step
        tokens_per_sec = tokens_processed / max(0.0001, elapsed_sec)
        row = {
            "step": step,
            "train_loss": eval_losses["train"],
            "val_loss": eval_losses["val"],
            "batch_loss": loss.item(),
            "step_ms": step_ms,
            "tokens_per_sec": tokens_per_sec,
            "tokens_processed": tokens_processed,
            "elapsed_sec": elapsed_sec,
        }
        csv_writer.writerow(row)
        if eval_losses["train"] is not None:
            metrics.append(row)
        if step % args.log_interval == 0 or step == args.max_steps - 1:
            line = (
                f"step {step}: batch loss {loss.item():.4f} "
                f"(took {step_ms:.1f} ms, {tokens_per_sec:.0f} tok/s, "
                f"{tokens_processed} tokens)"
            )
            print(line, flush=True)
            step_logs.append(line)
    csv_file.close()

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "config": config.to_dict(),
        "tokenizer_path": "tokenizer.json",
        "last_losses": last_losses,
        "training_args": serializable_args(args),
        "param_count": param_count,
        "tokens_processed": args.max_steps * tokens_per_step,
        "stage": args.stage,
    }
    torch.save(checkpoint, args.out_dir / "checkpoint.pt")
    metrics_payload = {
        "input": str(args.input),
        "device": str(device),
        "param_count": param_count,
        "vocab_size": tokenizer.vocab_size,
        "tokens": len(encoded),
        "train_tokens": len(train_data),
        "val_tokens": len(val_data),
        "tokens_per_step": tokens_per_step,
        "tokens_processed": args.max_steps * tokens_per_step,
        "stage": args.stage,
        "masked_loss": mask_tensor is not None,
        "elapsed_sec": time.perf_counter() - total_start,
        "config": config.to_dict(),
        "training_args": serializable_args(args),
        "metrics": metrics,
        "step_logs": step_logs,
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    print(f"Saved checkpoint to {args.out_dir / 'checkpoint.pt'}")
    print(f"Saved metrics to {args.out_dir / 'metrics.json'}")
    print(f"Saved llm.c-style training log to {csv_path}")


def load_sft_mask(mask_path: Path | None, expected_len: int) -> torch.Tensor:
    if mask_path is None:
        raise ValueError("--stage sft requires --sft-mask")
    payload = json.loads(mask_path.read_text(encoding="utf-8"))
    mask = payload["mask"] if isinstance(payload, dict) else payload
    if len(mask) != expected_len:
        raise ValueError(f"SFT mask length {len(mask)} does not match encoded text length {expected_len}.")
    return torch.tensor(mask, dtype=torch.float32)


if __name__ == "__main__":
    main()
