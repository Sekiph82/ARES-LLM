# Ares Next Milestones

This milestone pass adds the first practical version of each requested training
and agent upgrade.

## Implemented

- **BPE tokenizer**: `BPETokenizer` trains character-pair merges from local text,
  saves tokenizer metadata, reloads in generation, and works with SFT masks.
- **Validation curves and experiment logging**: every training run writes
  `metrics.json`, `training_log.csv`, `validation_curve.svg`, and appends a
  compact row to `runs/experiments.jsonl`.
- **Public-domain dataset prep**: `local_llm.prepare_public_domain_corpus`
  downloads and cleans Project Gutenberg plain-text sources into a local corpus.
- **Instruction formatting**: `local_llm.prepare_instruction_corpus` converts
  instruction JSONL into Ares chat format with assistant-only loss masking.
- **LoRA adapters**: `--lora-rank` wraps selected transformer linear layers with
  trainable low-rank adapters while freezing the base model.
- **Safer patch application**: patch checks now reject generated/internal
  folders, secret-bearing files, unsafe paths, too many files, and very large
  patch targets before `git apply`.
- **Visual QA for generated sites**: artifacts record optional desktop/mobile
  browser screenshots and blank-page checks when Playwright is installed.
- **Local media generation**: `local_llm.media_artifact` turns image/video
  prompts into a ViMax-inspired local plan, storyboard, keyframe PNGs, frame
  sequence, animated GIF, and manifest.
- **Media backend registry**: Ares can now record backend status and prompt
  handoff packages for ViMax, HunyuanVideo, CogVideoX, Toonflow, and Open
  Generative AI while falling back to the built-in renderer.

## Important Limits

These upgrades still train the small scratch model, not the production coding
brain. Ares' useful coding work continues to use the Ollama `ares-coder` model.

The 13M BPE preset is intentionally an experiment. It is closer to the small
configuration from the external training repo, but it will be slower than the
CPU demo presets and still much smaller than Qwen Coder.

Visual QA is optional. If Playwright is not installed, generated artifacts still
work and record that QA was skipped.

The local media generator is a storyboard and preview renderer. It does not yet
run a large image diffusion or video model locally. HunyuanVideo, CogVideoX,
Toonflow, and Open Generative AI require their own local installs or services
before Ares can hand work to them.
