import pytest

torch = pytest.importorskip("torch")

from local_llm.model import GPTConfig, GPTLanguageModel


def test_model_forward_pass_produces_loss() -> None:
    config = GPTConfig(vocab_size=10, block_size=8, n_layer=1, n_head=2, n_embd=16, dropout=0.0)
    model = GPTLanguageModel(config)
    idx = torch.randint(0, config.vocab_size, (2, config.block_size))

    logits, loss = model(idx, idx)

    assert logits.shape == (2, config.block_size, config.vocab_size)
    assert loss is not None


def test_model_forward_accepts_loss_mask() -> None:
    config = GPTConfig(vocab_size=10, block_size=8, n_layer=1, n_head=2, n_embd=16, dropout=0.0)
    model = GPTLanguageModel(config)
    idx = torch.randint(0, config.vocab_size, (2, config.block_size))
    loss_mask = torch.zeros((2, config.block_size))
    loss_mask[:, -2:] = 1

    _, loss = model(idx, idx, loss_mask)

    assert loss is not None
    assert loss.item() > 0
