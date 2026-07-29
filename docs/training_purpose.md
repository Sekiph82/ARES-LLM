# What Ares LLM Training Is For

Ares has two different model paths:

1. **The useful coding agent**

   This is `ares-coder`, an Ollama model based on `qwen2.5-coder:3b`. This is
   the model Ares uses to answer coding questions, inspect the repository,
   create dynamic websites, suggest patches, and help with projects.

2. **The from-scratch training model**

   This is the tiny PyTorch GPT-style model trained by `local_llm.train`. It is
   for learning, experimentation, and measuring how language-model training
   works on your laptop.

The scratch model is not expected to become a strong coding agent on a normal
laptop. It is too small and trained on too little data. Its value is that it
shows the real mechanics:

- tokenization
- batches and context length
- train loss and validation loss
- checkpoints
- sampling/generation
- speed in milliseconds per step
- token throughput

## How Ares Trains Now

Ares now has two local training stages:

1. **Base pretraining**

   This uses `local_llm.prepare_corpus` and `local_llm.train --stage pretrain`.
   It teaches the tiny scratch model to predict the next character from plain
   repository text. This is the classic GPT-style training loop.

2. **Ares SFT**

   This uses `local_llm.prepare_sft_corpus` and `local_llm.train --stage sft`.
   It formats examples as:

   ```text
   <|user|>
   ...
   <|assistant|>
   ...
   ```

   The trainer also writes an assistant-only loss mask. That means the model
   sees the full conversation, but the loss is counted only on the assistant
   answer. This follows the same practical idea used in supervised fine-tuning
   projects such as `FareedKhan-dev/train-llm-from-scratch`: pretrain a base
   model first, then teach it how to answer as an assistant.

## Tokenizers

Ares supports two tokenizer modes:

- **char**: simple, transparent, and useful for first training experiments.
- **bpe**: learns repeated character-pair merges and produces larger text
  chunks. This is closer to the tokenizer style used by practical LLMs, while
  staying small enough to understand.

Use BPE when you want fewer tokens and a more realistic training setup. Use char
when you want the simplest possible debug path.

## LoRA Experiments

Ares can now run tiny LoRA adapter experiments with `--lora-rank`. LoRA freezes
the base model weights and trains small low-rank adapter matrices inside
selected linear layers. This is useful for learning how adapter fine-tuning
works without updating every parameter.

## How Training Affects Ares

Today, training affects Ares in two different ways:

- The **Training tab** can produce tiny checkpoints under `runs/ares`.
- The **main coding agent** still uses Ollama `ares-coder`, because that is the
  model strong enough for real coding help on this laptop.

So training improves the scratch experiment, not the full coding agent yet. To
make training affect the real Ares agent later, Ares would need a controlled
fine-tuning pipeline for a larger base model, plus evaluation and rollback.
That is possible later, but it is not the same as the current safe scratch
training.

## How Often To Train

For this laptop-friendly setup:

- Run **LLM.C CPU Demo** when you want a quick sanity check.
- Run **Tiny CPU** or **Ares SFT CPU Demo** after changing training code or
  adding example data.
- Run **Small CPU** or **Ares SFT Small CPU** only when you want a longer
  experiment and the laptop can work for a while.
- Run **BPE CPU Demo** to test BPE tokenization.
- Run **13M BPE Experiment** only as a larger experiment. It follows the small
  13M-style model shape from the external training repo, but CPU training will
  be much slower than the demo presets.

Do not train forever just because the button exists. Train, check validation
loss, generate a sample, compare behavior, then decide whether another run is
worth it.

## Why Use Ideas From karpathy/llm.c

`karpathy/llm.c` is useful because it treats training as something that should
be visible and measurable. Ares borrows that style in a laptop-friendly Python
form:

- short CPU demo preset
- printed step logs
- per-step timing
- tokens/sec
- token counters
- CSV training log
- compact metrics JSON

The goal is not to copy the C/CUDA implementation into Ares today. The goal is
to make Ares' training tab teach the same core loop clearly while staying
usable on Windows without a dedicated GPU.

## Practical Use

Use the scratch model when you want to learn or experiment:

- test a tokenizer change
- see whether loss goes down
- compare training presets
- generate tiny text samples from a checkpoint
- understand how GPT-style training works

Use `ares-coder` through Ollama when you want Ares to actually help build,
debug, refactor, review, or design projects.
