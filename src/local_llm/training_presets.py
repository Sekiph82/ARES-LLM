from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrainingPreset:
    name: str
    stage: str
    max_steps: int
    batch_size: int
    block_size: int
    n_layer: int
    n_head: int
    n_embd: int
    eval_interval: int
    eval_iters: int
    log_interval: int


TRAINING_PRESETS = {
    "LLM.C CPU Demo": TrainingPreset("LLM.C CPU Demo", "pretrain", 40, 4, 64, 2, 2, 64, 20, 8, 1),
    "Tiny CPU": TrainingPreset("Tiny CPU", "pretrain", 250, 8, 64, 2, 2, 64, 50, 10, 10),
    "Small CPU": TrainingPreset("Small CPU", "pretrain", 700, 8, 96, 3, 3, 96, 70, 12, 10),
    "Longer experiment": TrainingPreset("Longer experiment", "pretrain", 1500, 8, 128, 4, 4, 128, 100, 16, 25),
    "Ares SFT CPU Demo": TrainingPreset("Ares SFT CPU Demo", "sft", 80, 4, 96, 2, 2, 64, 20, 8, 1),
    "Ares SFT Small CPU": TrainingPreset("Ares SFT Small CPU", "sft", 400, 6, 128, 3, 2, 96, 50, 10, 10),
}


def preset_args(preset: TrainingPreset) -> list[str]:
    return [
        "--max-steps",
        str(preset.max_steps),
        "--stage",
        preset.stage,
        "--batch-size",
        str(preset.batch_size),
        "--block-size",
        str(preset.block_size),
        "--n-layer",
        str(preset.n_layer),
        "--n-head",
        str(preset.n_head),
        "--n-embd",
        str(preset.n_embd),
        "--eval-interval",
        str(preset.eval_interval),
        "--eval-iters",
        str(preset.eval_iters),
        "--log-interval",
        str(preset.log_interval),
    ]


def load_metrics(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def ascii_loss_chart(metrics_payload: dict[str, object], width: int = 36) -> str:
    metrics = metrics_payload.get("metrics", [])
    if not isinstance(metrics, list) or not metrics:
        return "No metrics recorded yet."

    vals = [
        float(loss_value(item, "val"))
        for item in metrics
        if isinstance(item, dict) and loss_value(item, "val") is not None
    ]
    if not vals:
        return "No validation losses recorded yet."

    high = max(vals)
    low = min(vals)
    span = max(0.0001, high - low)
    lines = []
    for item in metrics:
        if not isinstance(item, dict) or loss_value(item, "val") is None:
            continue
        step = int(item.get("step", 0))
        train = float(loss_value(item, "train") or 0.0)
        val = float(loss_value(item, "val") or 0.0)
        bars = max(1, int(((high - val) / span) * width)) if len(vals) > 1 else width // 2
        tok_s = float(item.get("tokens_per_sec", 0.0))
        lines.append(f"{step:>5} train={train:.3f} val={val:.3f} tok/s={tok_s:>7.0f} {'#' * bars}")
    return "\n".join(lines)


def loss_value(item: dict[str, object], split: str) -> object | None:
    return item.get(split) if split in item else item.get(f"{split}_loss")
