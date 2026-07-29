# Ares Research Notes

These notes summarize the external repositories reviewed on July 29, 2026 and
the practical ideas folded into Ares.

## Training From Scratch

- `rasbt/LLMs-from-scratch`: step-by-step GPT pretraining and fine-tuning path.
  Ares keeps the same learning-first approach with transparent tokenizer, model,
  training, and generation modules.
- `angelos-p/llm-from-scratch`: laptop-scale GPT workshop framing, small model
  configurations, learning-rate/training hygiene. Ares now records metrics and
  uses gradient clipping.
- `FareedKhan-dev/train-llm-from-scratch`: full pipeline mindset from raw text
  to SFT/RL-style alignment. Ares adds a corpus preparation step so local project
  text can become training data.
- `jingyaogong/minimind`: compact end-to-end LLM lifecycle, including SFT,
  LoRA, reward learning, tool use, and distillation as later milestones.
- `rasbt/reasoning-from-scratch`: reasoning should be layered on top of a base
  model with explicit training/evaluation phases. Ares adds an agent `reason`
  mode before doing any real reasoning fine-tuning.
- `karpathy/llm.c`: training should be simple, visible, measurable, and close
  to the metal. Ares keeps the laptop-friendly PyTorch model but borrows the
  useful training instrumentation: CPU demo preset, per-step timing, tokens/sec,
  processed-token counts, `training_log.csv`, and compact metrics.

## Coding Agent And App Ideas

- `gptme/gptme`: local-first agent with tools, patch-oriented edits, lessons,
  context management, persistent history, and a small extensible core. Ares adds
  agent modes, session logs, patch extraction, shared agent core logic, and a
  dedicated artifact builder instead of making the core prompt do everything.
- `abhigyanpatwari/GitNexus`: repo understanding should start from a code map,
  then feed only relevant context. Ares adds a repository map and task-aware file
  ranking.
- `Fosowl/agenticSeek`: local privacy and autonomous task planning are first
  class goals. Ares keeps the local Ollama model path and avoids cloud defaults.
- `nexu-io/open-design`, `iOfficeAI/AionUi`, `NanmiCoder/cc-haha`, and
  `opactorai/Claudable`: desktop apps should wrap local agents in a usable
  workspace rather than forcing terminal use. Open Design's strongest idea for
  Ares is the design contract: a project-level `DESIGN.md` that shapes generated
  artifacts. Ares now includes `DESIGN.md`, a `design` mode, and a website/app
  artifact generator that writes `index.html`, `styles.css`, `app.js`, and
  `README.md` under `artifacts/`.
- `chenhg5/cc-connect`: remote chat bridges are useful later, but Ares should
  first stabilize the local app and logs.
- `AgriciDaniel/claude-seo`: skill packs and specialist modes scale better than
  one giant prompt. Ares adds explicit modes as a first step toward skills.
- `getagentseal/codeburn`: local usage visibility matters. Ares records prompt
  and response size estimates in `runs/agent/sessions.jsonl`.

## Deferred Ideas

- True automatic patch application with approval and rollback.
- Tree-sitter or AST-level code graph.
- Browser screenshot and visual regression checks for generated artifacts.
- SFT/LoRA adapters for a larger pretrained model.
- Remote/mobile access to the local agent.
- Plugin or skill marketplace.
