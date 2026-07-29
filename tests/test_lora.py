import pytest

torch = pytest.importorskip("torch")

from local_llm.lora import LoRAConfig, LoRALinear, apply_lora_adapters, trainable_parameter_count
from local_llm.model import GPTConfig, GPTLanguageModel


def test_apply_lora_adapters_freezes_base_and_adds_trainable_params() -> None:
    model = GPTLanguageModel(GPTConfig(vocab_size=16, block_size=8, n_layer=1, n_head=2, n_embd=16))

    replaced = apply_lora_adapters(model, LoRAConfig(rank=2, alpha=4.0))

    assert replaced > 0
    assert any(isinstance(module, LoRALinear) for module in model.modules())
    assert trainable_parameter_count(model) > 0
    assert trainable_parameter_count(model) < sum(param.numel() for param in model.parameters())
