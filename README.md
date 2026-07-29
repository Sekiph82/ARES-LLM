# ARES-LLM

A small local GPT-style language model built from scratch in PyTorch.

Canonical repository:
[github.com/Sekiph82/ARES-LLM](https://github.com/Sekiph82/ARES-LLM)

This project has two tracks:

- **From-scratch learning model**: a character-level tokenizer, a compact
  decoder-only Transformer, a training script, and a generation script.
- **Local coding agent**: an Ollama-powered assistant that reads this repository
  and asks a local coding model for implementation guidance.

It is a practical foundation for following the same learning arc as
[rasbt/LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) while
also building toward a useful local coding workflow.

## What This Can Do

- Train a tiny local language model on a plain text file.
- Save checkpoints with the model config and tokenizer vocabulary.
- Generate text from a prompt using temperature and top-k sampling.
- Ask a local Ollama coding model questions about this repository using
  task-aware context.
- Use agent modes: `answer`, `plan`, `patch`, `review`, `reason`, and
  `design`.
- Save session metadata and extracted patch suggestions.
- Create dynamic website/app artifacts with responsive UI, real JavaScript
  interactions, and a reusable `DESIGN.md` design contract.
- Create local media artifacts with storyboard planning, generated keyframe
  PNGs, frame sequences, and animated GIF output.
- Create full short-video production artifacts with topic-to-script planning,
  scene assets, subtitles, voiceover/TTS, background music, FFmpeg composition,
  aspect-ratio templates, MP4 export, and a local studio UI.
- Use a desktop workspace with Chat, Files, Diff, Training, Sessions, and
  Settings panels.
- Preview and check patch suggestions before applying them with a backup.
- Run tests, inspect git status/diff stats, browse session history, and view a
  Python symbol index from the app.
- Train the scratch model with CPU pretraining/SFT presets and generate from a
  saved checkpoint.
- Train with a character tokenizer or compact BPE tokenizer.
- Save validation curve SVGs and append experiment summaries to
  `runs/experiments.jsonl`.
- Prepare public-domain text and instruction JSONL for local training.
- Run optional LoRA adapter training for small fine-tuning experiments.
- Run smoke tests for the tokenizer and model forward pass.

The from-scratch model is not intended to compete with production LLMs. For
coding-agent work, use a pretrained local coding model through Ollama.
See [docs/training_purpose.md](docs/training_purpose.md) for the difference
between Ares' useful coding model and the scratch training experiment.
See [docs/self_learning.md](docs/self_learning.md) for how Ares' safer local
memory loop works.

## Setup

```powershell
git clone https://github.com/Sekiph82/ARES-LLM.git
cd ARES-LLM
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PyTorch installation fails on your machine, install it from the official
selector first, then run the editable install again:

```powershell
python -m pip install torch
python -m pip install -e ".[dev]"
```

## Ollama Coding Agent Setup

Install Ollama, then pull a coding model. For a 16 GB RAM laptop without a
dedicated GPU, start with:

```powershell
ollama pull qwen2.5-coder:3b
```

Try it directly:

```powershell
ollama run qwen2.5-coder:3b
```

Create the Ares-flavored local coding model:

```powershell
ollama create ares-coder -f ollama\Modelfile
```

Then ask the local coding agent about this repo:

```powershell
python -m local_llm.agent "Explain the model architecture"
```

Use a specific mode:

```powershell
python -m local_llm.agent "Add better training metrics" --mode plan
python -m local_llm.agent "Suggest a patch for tokenizer tests" --mode patch --save-patches
python -m local_llm.agent "Design a dynamic SaaS dashboard" --mode design
```

Or save the response:

```powershell
python -m local_llm.agent "Suggest the next tests to add" --save
```

The coding agent reads a repository map, ranks relevant files for the task, logs
session metadata under `runs/agent/sessions.jsonl`, and can save diff blocks
under `runs/agent/patches`. Automatic file editing will come later after the
patch workflow is made safe and testable.

## Create Dynamic Websites And Apps

Ares can generate a local website/app project from a brief. The generator uses
the Ollama `ares-coder` model first and falls back to a polished self-contained
starter if the model does not return a complete file bundle.

```powershell
python -m local_llm.web_artifact "Create a dynamic project dashboard with filters, metrics, and excellent UI"
```

Generated projects are written to:

```text
artifacts\<brief-slug>-<timestamp>\
```

Each artifact includes:

- `index.html`
- `styles.css`
- `app.js`
- `README.md`
- `ares-artifact.json`

For browser screenshots and visual QA, install the optional visual dependencies
and Chromium browser once:

```powershell
python -m pip install -e ".[visual]"
python -m playwright install chromium
```

When enabled, generated artifacts include desktop and mobile screenshots under
`visual-qa\`, and the manifest records whether the page passed the blank-screen
check.

The root `DESIGN.md` file acts like an Open Design-style brand contract for
Ares. Edit it when you want Ares to use a different visual style for generated
websites and apps.

## Create Local Images And Videos

Ares has two local video paths:

- **Short Video Studio** for video prompts: full production pipeline.
- **Media Artifact** for image/storyboard/keyframe prompts: lightweight preview
  renderer and backend handoff package.

Create a full short-video production artifact:

```powershell
python -m local_llm.short_video "create a 15 seconds YouTube short about Ares coding agent"
```

Each short-video artifact includes:

- `script.md`
- `subtitles.srt`
- `asset_plan.json`
- `ares-short-video.config.json`
- `voiceover.wav`
- `background_music.wav`
- `audio_mix.wav`
- `short_video.mp4` when FFmpeg is available
- `assets\scene-*.png`
- `studio.html`
- `ares-short-video.json`

Ares can create lightweight local media artifacts inspired by agentic video
generation workflows. It plans the prompt into shots, keeps a consistent visual
style, renders keyframe PNGs, writes a storyboard, and assembles an animated
GIF locally with Pillow. It also records backend handoff data for ViMax,
HunyuanVideo, CogVideoX, Toonflow, Open Generative AI, Remotion, FFmpeg,
MoneyPrinterTurbo, imaginAIry, InfiniteTalk, timm, and computer-vision learning
references.

```powershell
python -m local_llm.media_artifact "Create a cinematic Ares launch video with code, dashboard, and logo"
```

Check local media backend status:

```powershell
python -m local_llm.media_artifact --list-backends
```

Generated media is written to:

```text
artifacts\media-<brief-slug>-<timestamp>\
```

Each media artifact includes:

- `video.gif`
- `video.mp4` when FFmpeg is available
- `storyboard.png`
- `storyboard.md`
- `ares-media.json`
- `remotion\`
- `keyframes\shot-*.png`
- `frames\shot-*-frame-*.png`

The `remotion\` folder is an editable React video project. If Node.js is
installed, open that folder and run:

```powershell
npm install
npm run preview
npm run render
```

Ares detects FFmpeg from `PATH` or `ARES_FFMPEG_PATH`. When available, it
encodes generated PNG frames into `video.mp4` automatically.

This first version is a local procedural storyboard and preview renderer, not a
large diffusion/video model. See [docs/local_media_generation.md](docs/local_media_generation.md)
for details and upgrade ideas.

## Ares Desktop App

Ares is the no-terminal desktop app for this project. It uses:

- `ares-coder` through Ollama for coding-agent answers.
- The from-scratch PyTorch model for local training experiments.
- A local workspace with New Chat, files, diffs, training, commerce, sessions,
  and settings.
- A mode selector for answer, plan, patch, review, reasoning, and design.
- Automatic website/app routing when the task asks Ares to create or build a
  website, app, dashboard, landing page, portal, or tool.
- Automatic local media routing when the task asks Ares to create or generate
  videos, images, animations, GIFs, storyboards, clips, or keyframes.
- Keyboard-first chat: `Enter` sends, `Ctrl+Enter` inserts a new paragraph.
- A **Diff** panel for previewing, checking, and applying patch suggestions with
  automatic backups under `runs/backups`.
- A **Files** panel with git status, diff stats, and Python symbol extraction.
- A **Training** panel with CPU presets, live process output, loss chart, and
  scratch-checkpoint generation.
- A **Commerce** panel for read-only Shopify/Etsy connection checks and shop
  snapshots.

## Shopify And Etsy

Ares can start managing shop context through a read-only Commerce panel. It does
not store API secrets in the repo. Configure credentials through environment
variables before opening Ares:

```powershell
$env:ARES_SHOPIFY_SHOP = "your-shop.myshopify.com"
$env:ARES_SHOPIFY_ADMIN_TOKEN = "your-admin-api-token"
$env:ARES_ETSY_API_KEY = "keystring:shared_secret"
$env:ARES_ETSY_ACCESS_TOKEN = "oauth-access-token"
$env:ARES_ETSY_SHOP_ID = "your-shop-id"
```

Details are in [docs/commerce_setup.md](docs/commerce_setup.md).

Refresh the Ares logo and icon from the checked-in repo PNG:

```powershell
python scripts\update_ares_assets.py
```

Build the app inside the local repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_ares_app.ps1
```

This creates the executable at:

```text
dist\Ares.exe
```

## Train A Tiny Model

```powershell
python -m local_llm.train --input data/tiny_corpus.txt --out-dir runs/tiny --max-steps 300
```

The default config is intentionally small enough for quick CPU experiments. For
better output, train longer and use a larger text file.

The training loop now includes `llm.c`-style visibility:

- step timing in milliseconds
- tokens/sec
- tokens processed
- validation-loss checkpoints
- `metrics.json`
- `training_log.csv`
- `validation_curve.svg`
- `runs/experiments.jsonl`

For a very short CPU demo, use:

```powershell
python -m local_llm.train --input data/tiny_corpus.txt --out-dir runs/llmc-demo --max-steps 40 --batch-size 4 --block-size 64 --n-layer 2 --n-head 2 --n-embd 64 --eval-interval 20 --eval-iters 8 --log-interval 1 --device cpu
```

Use BPE instead of the character tokenizer:

```powershell
python -m local_llm.train --input data/tiny_corpus.txt --out-dir runs/bpe-demo --tokenizer bpe --bpe-vocab-size 512 --max-steps 80 --batch-size 4 --block-size 96 --n-layer 2 --n-head 2 --n-embd 64 --device cpu
```

Prepare a larger public-domain corpus:

```powershell
python -m local_llm.prepare_public_domain_corpus --output data\public_domain_corpus.txt --max-chars 2000000
```

The training flow also includes a small supervised fine-tuning path inspired by
[FareedKhan-dev/train-llm-from-scratch](https://github.com/FareedKhan-dev/train-llm-from-scratch):
chat-format examples plus assistant-only masked loss.

```powershell
python -m local_llm.prepare_sft_corpus --repo . --output data\ares_sft_corpus.txt --mask-output data\ares_sft_mask.json
python -m local_llm.train --input data\ares_sft_corpus.txt --sft-mask data\ares_sft_mask.json --stage sft --out-dir runs\ares-sft --max-steps 80 --batch-size 4 --block-size 96 --n-layer 2 --n-head 2 --n-embd 64 --eval-interval 20 --eval-iters 8 --log-interval 1 --device cpu
```

Convert instruction JSONL into the same SFT format:

```powershell
python -m local_llm.prepare_instruction_corpus --input data\instructions.jsonl --output data\ares_instruction_sft.txt --mask-output data\ares_instruction_sft_mask.json
```

Run a small LoRA adapter experiment:

```powershell
python -m local_llm.train --input data\tiny_corpus.txt --out-dir runs\lora-demo --lora-rank 4 --lora-alpha 8 --max-steps 80 --batch-size 4 --block-size 96 --n-layer 2 --n-head 2 --n-embd 64 --device cpu
```

The `13M BPE Experiment` preset follows the same small-model shape described in
the training repo you shared: BPE vocabulary around 50k, 128-dimensional
embeddings, one transformer block, eight heads, and 128-token context. It is
available as an experiment, not as the default laptop-friendly run.

## Generate Text

```powershell
python -m local_llm.generate --checkpoint runs/tiny/checkpoint.pt --prompt "To be"
```

Useful options:

```powershell
python -m local_llm.generate --checkpoint runs/tiny/checkpoint.pt --prompt "The model" --max-new-tokens 120 --temperature 0.8 --top-k 20
```

## Run Tests

```powershell
pytest
```

## Project Layout

```text
src/local_llm/
  tokenizer.py   Character tokenizer.
  model.py       GPT-style decoder-only Transformer.
  train.py       Pretraining loop for plain text.
  prepare_public_domain_corpus.py
  prepare_instruction_corpus.py
  prepare_sft_corpus.py
  lora.py
  visual_qa.py
  generate.py    Local text generation CLI.
  agent.py       Ollama-powered coding assistant CLI.
  web_artifact.py
  media_artifact.py
  design_system.py
  patch_ops.py
  repo_index.py
  training_presets.py
  memory.py
  commerce.py
  repo_context.py
  ollama_client.py
  utils.py       Reproducibility and device helpers.
data/
  tiny_corpus.txt
DESIGN.md
tests/
```

## Next Milestones

1. Add a BPE tokenizer.
2. Add validation curves and experiment logging.
3. Train on a larger public-domain dataset.
4. Add instruction fine-tuning data formatting.
5. Add LoRA fine-tuning for small adapters.
6. Add safe patch application to the local coding agent.
7. Add browser screenshots and visual QA for generated website/app artifacts.
8. Add local image/video artifact generation.
