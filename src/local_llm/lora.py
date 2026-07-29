from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class LoRAConfig:
    rank: int = 4
    alpha: float = 8.0
    dropout: float = 0.0


class LoRALinear(nn.Module):
    """Low-rank adapter wrapper for a Linear layer."""

    def __init__(self, base: nn.Linear, config: LoRAConfig) -> None:
        super().__init__()
        if config.rank <= 0:
            raise ValueError("LoRA rank must be greater than 0.")
        self.base = base
        self.rank = config.rank
        self.alpha = config.alpha
        self.scaling = config.alpha / config.rank
        self.dropout = nn.Dropout(config.dropout)
        self.lora_a = nn.Linear(base.in_features, config.rank, bias=False)
        self.lora_b = nn.Linear(config.rank, base.out_features, bias=False)
        nn.init.kaiming_uniform_(self.lora_a.weight, a=5**0.5)
        nn.init.zeros_(self.lora_b.weight)
        for param in self.base.parameters():
            param.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base(x) + self.lora_b(self.lora_a(self.dropout(x))) * self.scaling


def apply_lora_adapters(
    model: nn.Module,
    config: LoRAConfig,
    target_suffixes: tuple[str, ...] = ("c_attn", "c_proj", "0", "2"),
) -> int:
    """Replace selected Linear modules with LoRA wrappers and freeze the rest."""

    for param in model.parameters():
        param.requires_grad = False

    replaced = 0
    for module_name, module in list(model.named_modules()):
        for child_name, child in list(module.named_children()):
            full_name = f"{module_name}.{child_name}" if module_name else child_name
            if isinstance(child, nn.Linear) and should_wrap(full_name, target_suffixes):
                setattr(module, child_name, LoRALinear(child, config))
                replaced += 1
    if replaced == 0:
        raise ValueError("No Linear modules matched the LoRA target suffixes.")
    return replaced


def should_wrap(module_name: str, target_suffixes: tuple[str, ...]) -> bool:
    if module_name == "lm_head":
        return False
    return module_name.endswith(target_suffixes)


def trainable_parameter_count(model: nn.Module) -> int:
    return sum(param.numel() for param in model.parameters() if param.requires_grad)
