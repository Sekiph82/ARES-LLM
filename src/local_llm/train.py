from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import torch
from tqdm import tqdm

from local_llm.lora import LoRAConfig, apply_lora_adapters, trainable_parameter_count
from local_llm.model import GPTConfig, GPTLanguageModel
from local_llm.tokenizer import build_tokenizer
from local_llm.utils import get_device, set_seed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a tiny local GPT-style language model.")
    parser.add_argument("--input", type=Path, required=True, help="Plain text training file.")
    parser.add_argument("--out-dir", type=Path, default=Path("runs/tiny"), help="Checkpoint output directory.")
    parser.add_argument("--stage", choices=["pretrain", "sft"], default="pretrain")
    parser.add_argument("--sft-mask", type=Path, default=None, help="JSON mask aligned to the SFT input text.")
    parser.add_argument("--tokenizer", choices=["char", "bpe"], default="char")
    parser.add_argument("--bpe-vocab-size", type=int, default=512)
    parser.add_argument("--experiment-name", default=None)
    parser.add_argument("--experiment-log", type=Path, default=Path("runs/experiments.jsonl"))
    parser.add_argument("--lora-rank", type=int, default=0)
    parser.add_argument("--lora-alpha", type=float, default=8.0)
    parser.add_argument("--lora-dropout", type=float, default=0.0)
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
    tokenizer = build_tokenizer(text, kind=args.tokenizer, bpe_vocab_size=args.bpe_vocab_size)
    token_ids, token_spans = tokenizer.encode_with_spans(text)
    encoded = torch.tensor(token_ids, dtype=torch.long)
    mask_tensor = load_sft_mask(args.sft_mask, len(text), token_spans) if args.stage == "sft" else None

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
    lora_config = None
    lora_modules = 0
    if args.lora_rank > 0:
        lora_config = LoRAConfig(rank=args.lora_rank, alpha=args.lora_alpha, dropout=args.lora_dropout)
        lora_modules = apply_lora_adapters(model, lora_config)
    optimizer = torch.optim.AdamW((param for param in model.parameters() if param.requires_grad), lr=args.learning_rate)
    param_count = sum(param.numel() for param in model.parameters())
    trainable_params = trainable_parameter_count(model)
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
        "tokenizer": args.tokenizer,
        "lora": lora_config.__dict__ if lora_config else None,
    }
    torch.save(checkpoint, args.out_dir / "checkpoint.pt")
    metrics_payload = {
        "input": str(args.input),
        "device": str(device),
        "param_count": param_count,
        "trainable_param_count": trainable_params,
        "vocab_size": tokenizer.vocab_size,
        "tokens": len(encoded),
        "train_tokens": len(train_data),
        "val_tokens": len(val_data),
        "tokens_per_step": tokens_per_step,
        "tokens_processed": args.max_steps * tokens_per_step,
        "stage": args.stage,
        "tokenizer": args.tokenizer,
        "lora_modules": lora_modules,
        "lora": lora_config.__dict__ if lora_config else None,
        "masked_loss": mask_tensor is not None,
        "elapsed_sec": time.perf_counter() - total_start,
        "config": config.to_dict(),
        "training_args": serializable_args(args),
        "metrics": metrics,
        "step_logs": step_logs,
    }
    (args.out_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    write_validation_curve(metrics_payload, args.out_dir / "validation_curve.svg")
    append_experiment_log(args.experiment_log, metrics_payload, args)
    print(f"Saved checkpoint to {args.out_dir / 'checkpoint.pt'}")
    print(f"Saved metrics to {args.out_dir / 'metrics.json'}")
    print(f"Saved llm.c-style training log to {csv_path}")
    print(f"Saved validation curve to {args.out_dir / 'validation_curve.svg'}")


def load_sft_mask(
    mask_path: Path | None,
    expected_chars: int,
    token_spans: list[tuple[int, int]],
) -> torch.Tensor:
    if mask_path is None:
        raise ValueError("--stage sft requires --sft-mask")
    payload = json.loads(mask_path.read_text(encoding="utf-8"))
    mask = payload["mask"] if isinstance(payload, dict) else payload
    if len(mask) != expected_chars:
        raise ValueError(f"SFT mask length {len(mask)} does not match text length {expected_chars}.")
    token_mask = [1.0 if any(mask[pos] for pos in range(start, end)) else 0.0 for start, end in token_spans]
    return torch.tensor(token_mask, dtype=torch.float32)


def write_validation_curve(metrics_payload: dict[str, object], path: Path) -> None:
    metrics = [item for item in metrics_payload.get("metrics", []) if isinstance(item, dict)]
    points = [
        (float(item.get("step", 0)), float(item["val_loss"]))
        for item in metrics
        if item.get("val_loss") is not None
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    if not points:
        path.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"240\"></svg>\n", encoding="utf-8")
        return

    width, height = 720, 300
    pad = 42
    min_step, max_step = min(step for step, _ in points), max(step for step, _ in points)
    min_loss, max_loss = min(loss for _, loss in points), max(loss for _, loss in points)
    step_span = max(1.0, max_step - min_step)
    loss_span = max(0.0001, max_loss - min_loss)
    coords = []
    for step, loss in points:
        x = pad + ((step - min_step) / step_span) * (width - pad * 2)
        y = height - pad - ((max_loss - loss) / loss_span) * (height - pad * 2)
        coords.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(coords)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="100%" height="100%" fill="#101216"/>
  <text x="{pad}" y="26" fill="#f6f7f9" font-family="Segoe UI, Arial" font-size="16">Validation Loss</text>
  <line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="#4b5563"/>
  <line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" stroke="#4b5563"/>
  <polyline points="{polyline}" fill="none" stroke="#f97316" stroke-width="3"/>
  <text x="{pad}" y="{height - 12}" fill="#aab2bf" font-family="Segoe UI, Arial" font-size="12">step {int(min_step)} to {int(max_step)}</text>
  <text x="{width - 180}" y="{height - 12}" fill="#aab2bf" font-family="Segoe UI, Arial" font-size="12">loss {min_loss:.3f} to {max_loss:.3f}</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def append_experiment_log(path: Path, metrics_payload: dict[str, object], args: argparse.Namespace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    losses = metrics_payload.get("metrics", [])
    last_loss = None
    if isinstance(losses, list) and losses:
        last = losses[-1]
        if isinstance(last, dict):
            last_loss = last.get("val_loss")
    record = {
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "name": args.experiment_name or Path(str(args.out_dir)).name,
        "out_dir": str(args.out_dir),
        "stage": args.stage,
        "tokenizer": args.tokenizer,
        "param_count": metrics_payload.get("param_count"),
        "trainable_param_count": metrics_payload.get("trainable_param_count"),
        "tokens_processed": metrics_payload.get("tokens_processed"),
        "last_val_loss": last_loss,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


if __name__ == "__main__":
    main()
