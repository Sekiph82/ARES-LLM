# Ares Future Task Backlog

This file is the working roadmap for Ares. It is intentionally detailed so the
next development session can continue without rediscovering the project state.

## Roadmap Rules

- Keep Ares usable as a local desktop app first.
- Keep generated artifacts, local settings, API keys, model checkpoints, and
  build outputs out of git.
- Prefer safe preview-and-approve workflows before Ares edits files, shop data,
  or external services.
- Every major feature should include tests, docs, and a simple manual smoke
  check.
- Local models should be optional and replaceable. Ares should work with the
  smallest practical backend first, then allow stronger backends later.
- Do not pretend the scratch model is the production coding brain. The scratch
  model is for learning and experiments; the useful coding agent uses Ollama or
  another capable local model.

## Current Baseline

- Ares desktop app exists and launches from the built Windows executable.
- Ollama-backed coding agent exists with task modes.
- Scratch Transformer training exists with character and compact BPE tokenizer
  support.
- Training metrics, validation curves, experiment logs, SFT formatting, and
  LoRA adapters exist.
- Safe patch checks and patch backup flow exist.
- Website/app artifact generation exists with optional Playwright visual QA.
- Local media artifact generation exists with storyboard, PNG frames, GIF, MP4
  when FFmpeg is available, Remotion project files, and backend handoff
  manifests.
- Short Video Studio exists with script planning, scene planning, procedural
  assets, scene motion, subtitles, voiceover, music, audio mix, MP4 export,
  aspect templates, config JSON, and `studio.html`.
- Health check CLI and Settings panel readiness check exist.
- Local config loading exists through committed example defaults, ignored local
  overrides, and environment-variable overrides.
- Ollama model refresh/test/create controls exist in Settings.
- Diff panel shows patch summary, touched files, additions/deletions, safety
  status, save, reject, check, and apply actions.
- Commerce tab exists in read-only setup mode, but real Shopify/Etsy OAuth and
  shop management are not complete.

## Priority 0: Stability And Safety

### P0.1 Application Health Check

Status: Implemented

Goal: Add one command and one GUI button that checks whether Ares is ready.

Tasks:

- Check Python package import health.
- Check Ollama availability.
- Check selected Ollama model availability.
- Check FFmpeg availability.
- Check Playwright availability.
- Check write permissions for `artifacts/` and `runs/`.
- Check that git worktree is readable.
- Show clear pass/warn/fail rows in the Settings panel.

Acceptance Criteria:

- `python -m local_llm.healthcheck` prints a readable report.
- Desktop Settings panel has a `Run Health Check` button.
- Health check never exposes secrets.
- Tests cover missing Ollama, missing FFmpeg, and clean success paths through
  mocked checks.

### P0.2 Local Configuration System

Status: Implemented

Goal: Move machine-specific settings to ignored local config files.

Tasks:

- Add `config/ares.example.json` committed to git.
- Add ignored `config/ares.local.json`.
- Add loader with environment-variable override support.
- Store model names, artifact defaults, media backend paths, and commerce
  connector modes in config.
- Add Settings UI fields that write only to local config.

Acceptance Criteria:

- README explains copying example config without using personal file paths.
- Tests verify local config overrides example defaults.
- `.gitignore` protects local config.

### P0.3 Error Reporting

Status: Pending

Goal: Make failures understandable inside the GUI.

Tasks:

- Add structured app errors with title, reason, and next action.
- Show command output snippets when FFmpeg, Playwright, or Ollama fails.
- Save error details to `runs/ares-errors.jsonl`.
- Add a `Copy Error` button.

Acceptance Criteria:

- A failed media render produces a clear message.
- The app does not freeze when a background task fails.
- Tests cover serialization of error records.

## Priority 1: Coding Agent

### P1.1 Real Patch Preview Panel

Status: First pass implemented

Goal: Let Ares show proposed code changes before applying them.

Tasks:

- Parse unified diffs from model output.
- Show file list, additions, deletions, and affected paths.
- Render per-file diff text in the Diff panel.
- Detect unsafe files before enabling apply.
- Add `Reject Patch` and `Save Patch` actions.

Acceptance Criteria:

- Patch preview works for multi-file diffs.
- Unsafe patch targets keep `Apply` disabled.
- Unit tests cover patch extraction and file path validation.

### P1.2 Apply Patch With Backup

Status: In Progress

Goal: Make file editing useful but safe.

Tasks:

- Keep current backup-before-edit behavior.
- Add restore-from-backup command.
- Record applied patch metadata in session history.
- Require clean safety check before apply.
- After apply, show git diff stat and changed files.

Acceptance Criteria:

- Applying a patch creates a restorable backup.
- Failed apply leaves files unchanged.
- Tests cover successful apply, rejected apply, and restore.

### P1.3 Run Tests Workflow

Status: In Progress

Goal: Let Ares run repo tests without opening a terminal.

Tasks:

- Add configurable test commands.
- Add default command: `python -m pytest -q`.
- Stream output to the app.
- Save test runs under `runs/tests/`.
- Show pass/fail badge in the app header.

Acceptance Criteria:

- User can click `Run Tests` from the app.
- Long test runs do not freeze the GUI.
- Last test result is visible in Sessions.

### P1.4 Repo Index And Symbol Map Upgrade

Status: In Progress

Goal: Improve how Ares understands codebases.

Tasks:

- Expand file ranking beyond filename and text snippets.
- Extract Python imports, classes, functions, dataclasses, and CLI entrypoints.
- Add JavaScript/TypeScript symbol extraction later.
- Add dependency graph JSON under `runs/index/`.
- Show file tree and relevant files in the Files panel.

Acceptance Criteria:

- Index can be rebuilt from the app.
- Coding prompts include better task-relevant context.
- Tests cover Python symbol extraction.

### P1.5 Agent Task Loop

Status: Pending

Goal: Let Ares perform multi-step coding tasks with checkpoints.

Tasks:

- Add plan generation.
- Add step execution log.
- Add stop/cancel button.
- Add maximum edit count per task.
- Require preview before file writes.
- Add automatic tests after edits when configured.

Acceptance Criteria:

- Ares can complete a small edit-test-report loop.
- User can cancel between steps.
- Ares never writes files without the safe patch flow.

## Priority 2: Website And App Builder

### P2.1 Better App Templates

Status: Pending

Goal: Generate richer apps instead of simple static pages.

Tasks:

- Add templates for dashboard, CRM, inventory, portfolio, landing page, game,
  admin panel, and ecommerce admin.
- Add template-specific interaction patterns.
- Add template-specific visual QA expectations.
- Add generated `README.md` with run/open instructions.

Acceptance Criteria:

- Prompts like "create a CRM" and "create a dashboard" produce clearly
  different layouts.
- Generated app has useful interactions, not only static cards.
- Visual QA screenshots pass desktop and mobile blank checks.

### P2.2 Browser Screenshots And Visual QA Upgrade

Status: In Progress

Goal: Make generated websites visually reliable.

Tasks:

- Detect text overflow in common UI containers.
- Detect blank or mostly blank pages.
- Capture desktop and mobile screenshots.
- Add optional contrast checks.
- Add screenshot thumbnails in the Ares app.

Acceptance Criteria:

- Manifest records visual QA pass/fail.
- Screenshots are saved in the artifact folder.
- At least one test covers screenshot manifest output with mocked Playwright.

### P2.3 App Artifact Revision Flow

Status: Pending

Goal: Let the user ask Ares to modify a generated website/app.

Tasks:

- Add artifact selector.
- Load previous artifact manifest and files.
- Ask model for a patch against the selected artifact.
- Preview patch before applying.
- Re-run visual QA after changes.

Acceptance Criteria:

- A generated app can be revised without starting a new artifact folder.
- Revision history is saved.
- Failed revision can be restored.

## Priority 3: Short Video Studio

### P3.1 Replace Procedural Assets With Real Image Backends

Status: Pending

Goal: Stop relying only on generated abstract local images.

Tasks:

- Add asset provider interface.
- Add providers:
  - procedural fallback
  - local image folder
  - web image search handoff
  - imaginAIry command
  - future Stable Diffusion/ComfyUI bridge
- Save provider metadata per scene.
- Allow provider selection in config.

Acceptance Criteria:

- Short videos can use real user-provided images.
- If no backend exists, procedural fallback still works.
- Manifest records which provider created each scene asset.

### P3.2 Scene Motion And Composition

Status: First pass implemented

Goal: Make videos feel like videos, not still slides.

Tasks:

- Add Ken Burns pan/zoom filters per scene.
- Add transitions between scenes.
- Add text overlays from subtitles.
- Add title card and ending card.
- Add basic brand/logo overlay support.

Acceptance Criteria:

- MP4 has visible motion in each scene.
- Subtitles can be burned into the video.
- Aspect templates keep text inside safe areas.

### P3.3 Voiceover Quality

Status: Pending

Goal: Improve audio beyond basic Windows SAPI.

Tasks:

- Add TTS provider interface.
- Keep Windows SAPI as default on Windows.
- Add optional local Piper TTS integration.
- Add optional edge-tts integration if installed.
- Normalize voiceover volume.
- Save voiceover script separately from scene plan.

Acceptance Criteria:

- User can choose voice provider in config.
- Missing TTS backend fails gracefully.
- Voiceover text no longer sounds like raw command text.

### P3.4 Background Music And Audio Mastering

Status: Pending

Goal: Make audio more pleasant and configurable.

Tasks:

- Add music styles: calm, cinematic, upbeat, dramatic, minimal.
- Add volume sliders in config.
- Add fade-in and fade-out.
- Duck background music under voiceover.
- Save audio pipeline details to manifest.

Acceptance Criteria:

- Final audio is not painfully loud.
- Music starts and ends cleanly.
- MP4 contains the mixed audio track.

### P3.5 Studio UI

Status: First pass implemented

Goal: Turn `studio.html` into a useful local review/config page.

Tasks:

- Show generated video preview.
- Show scene cards with image, narration, caption, and duration.
- Allow editing config values in the page.
- Add copyable commands for re-rendering.
- Add links to script, subtitles, asset plan, and manifest.

Acceptance Criteria:

- Opening `studio.html` gives a clear review screen.
- User can inspect every scene.
- Config edits are documented even if full write-back comes later.

### P3.6 MoneyPrinterTurbo-Style Production Flow

Status: Pending

Goal: Make Ares behave more like a full short-content producer.

Tasks:

- Add topic research step.
- Add hook variations.
- Add script rewrite options.
- Add platform presets:
  - YouTube Shorts
  - TikTok
  - Instagram Reels
  - Etsy product video
  - Shopify product ad
- Add product/title/CTA extraction.
- Add batch rendering for multiple script variants.

Acceptance Criteria:

- User can request "make a product video for this listing" and get a complete
  artifact.
- Ares can produce multiple versions from one topic.
- Each variant has separate manifest and export files.

## Priority 4: Commerce Connectors

### P4.1 Shopify OAuth Setup

Status: Pending

Goal: Connect Shopify safely without asking the user to paste secrets into git.

Tasks:

- Create local connector config shape.
- Add OAuth/sign-in instructions inside the app.
- Store tokens only in ignored local config or OS credential store.
- Start read-only scopes first.
- Fetch shop info, products, orders, and inventory summaries.

Acceptance Criteria:

- User can sign in or configure Shopify without committing secrets.
- Commerce tab shows read-only shop summary.
- Tests mock Shopify API responses.

### P4.2 Etsy OAuth Setup

Status: Pending

Goal: Connect Etsy safely in read-only mode first.

Tasks:

- Add Etsy OAuth flow helper.
- Store tokens locally only.
- Fetch shop profile, listings, orders, and listing quality fields.
- Add setup status to Commerce tab.

Acceptance Criteria:

- User can connect Etsy without storing keys in repo.
- Commerce tab shows read-only Etsy summary.
- Tests mock Etsy API responses.

### P4.3 Commerce Copilot

Status: Pending

Goal: Let Ares help manage shops with previews and approvals.

Tasks:

- Add listing audit.
- Add SEO/title/tag suggestions.
- Add image/video content suggestions.
- Add inventory warnings.
- Add order/customer response draft mode.
- Keep write actions disabled until preview/approval exists.

Acceptance Criteria:

- Ares can generate safe listing improvement suggestions.
- No shop write action happens silently.
- Commerce sessions are logged.

## Priority 5: Training And Self-Learning

### P5.1 Training Dashboard

Status: Pending

Goal: Make training understandable in the GUI.

Tasks:

- Show preset selector.
- Show dataset selector.
- Show live loss updates.
- Show validation curve preview.
- Show estimated time and last checkpoint.
- Add cancel training button.

Acceptance Criteria:

- User can start a tiny training run from the app.
- Metrics update without freezing.
- Completed run appears in session history.

### P5.2 Dataset Manager

Status: Pending

Goal: Make datasets easy and safe to prepare.

Tasks:

- List local datasets.
- Add public-domain dataset download helper.
- Add instruction JSONL validator.
- Add dataset size/token estimate.
- Add train/validation split preview.

Acceptance Criteria:

- Bad instruction rows are reported clearly.
- Dataset prep never overwrites without confirmation.
- Dataset metadata is saved.

### P5.3 LoRA Fine-Tuning Workflow

Status: In Progress

Goal: Make small adapter training useful for experiments.

Tasks:

- Add adapter naming.
- Save adapter metadata.
- Add adapter load path for generation.
- Add GUI preset for LoRA.
- Add docs explaining adapter limits.

Acceptance Criteria:

- User can train and load a small adapter from CLI.
- App shows which adapter is selected.
- Tests cover adapter metadata.

### P5.4 Self-Learning Memory Loop

Status: Pending

Goal: Let Ares improve its local behavior without unsafe autonomous retraining.

Tasks:

- Save useful user preferences to local memory.
- Save project facts and recurring instructions.
- Add memory review screen before long-term save.
- Add memory search for agent context.
- Add delete/edit memory controls.

Acceptance Criteria:

- Ares remembers approved preferences.
- User can inspect and delete memory.
- Memory is separate from model weights.

### P5.5 From-Scratch Model Experiments

Status: In Progress

Goal: Continue learning-focused LLM training without confusing it with the
production coding agent.

Tasks:

- Add 13M parameter preset documentation.
- Add estimated RAM/time notes.
- Add validation loss comparisons.
- Add generation samples per checkpoint.
- Add small reasoning dataset formatting.

Acceptance Criteria:

- Each experiment has metrics, config, and sample output.
- README clearly explains why long training runs are needed.
- Scratch model remains optional.

## Priority 6: Local Model And Backend Management

### P6.1 Ollama Model Manager

Status: First pass implemented

Goal: Manage local coding models from Ares.

Tasks:

- List installed Ollama models.
- Pull recommended model.
- Create/update `ares-coder`.
- Test model response.
- Show model size and rough RAM expectations.

Acceptance Criteria:

- Settings panel shows installed models.
- User can switch between models.
- Missing Ollama produces a helpful setup message.

### P6.2 Media Backend Manager

Status: Pending

Goal: Make optional video/image backends visible and configurable.

Tasks:

- Show backend status for FFmpeg, Remotion, imaginAIry, HunyuanVideo,
  CogVideoX, Toonflow, ViMax-style handoff, ComfyUI, and local folders.
- Add provider priority order.
- Add test prompt button per provider.
- Save provider status to local config.

Acceptance Criteria:

- Ares shows what it can actually use on the laptop.
- Missing backends are marked optional.
- The generator chooses the best available provider.

## Priority 7: Desktop UI Upgrade

### P7.1 Layout Polish

Status: Pending

Goal: Make the current desktop UI cleaner and easier to use.

Tasks:

- Keep New Chat as the primary session action.
- Keep Sessions always visible in the sidebar.
- Move Settings to a clear button location.
- Remove unnecessary status text from the sidebar.
- Improve spacing and scaling for smaller laptop screens.
- Keep Enter to send and Ctrl+Enter for new paragraph.

Acceptance Criteria:

- Main task box is immediately visible.
- Sidebar does not feel crowded.
- Keyboard behavior is tested manually.

### P7.2 Richer UI Framework Investigation

Status: Pending

Goal: Decide whether to stay with Tkinter or move to a richer UI.

Tasks:

- Compare Tkinter, PySide/PyQt, Tauri, Electron, and local web UI.
- Consider packaging size, reliability, and ease of updates.
- Prototype one panel in the best candidate.
- Decide before doing a full rewrite.

Acceptance Criteria:

- Decision note exists in `docs/`.
- Prototype proves file access, background tasks, and app packaging.
- Current Tkinter app remains usable during investigation.

## Priority 8: Documentation And Release

### P8.1 User Manual

Status: Pending

Goal: Create a clear manual for non-developers.

Tasks:

- Explain installing Ares.
- Explain Ollama setup.
- Explain Chat, Files, Diff, Training, Commerce, Sessions, and Settings.
- Explain creating websites/apps.
- Explain creating short videos.
- Explain what training does and does not do.

Acceptance Criteria:

- Manual has screenshots or screenshot placeholders.
- Manual avoids local machine paths.
- New user can follow it from a clean clone.

### P8.2 Developer Guide

Status: Pending

Goal: Make future development easier.

Tasks:

- Document source layout.
- Document test commands.
- Document artifact formats.
- Document safety rules.
- Document how to add a new backend provider.

Acceptance Criteria:

- A new contributor can run tests and create a sample artifact.
- Backends can be added without reading the whole codebase.

### P8.3 Release Packaging

Status: Pending

Goal: Make Ares downloadable without committing local builds.

Tasks:

- Keep build scripts generic.
- Add release workflow notes.
- Add checksum generation.
- Document desktop shortcut creation.
- Consider GitHub Releases for EXE uploads later.

Acceptance Criteria:

- Repo stays clean after build.
- Build outputs remain ignored.
- Release instructions do not include personal paths.

## Suggested Next Implementation Order

1. P1.3 Run Tests Workflow deepening with saved test history and badges.
2. P3.1 Real image backend provider interface for Short Video Studio.
3. P3.3 Voiceover quality with local Piper or another stronger TTS provider.
4. P4.1 Shopify OAuth Setup.
5. P4.2 Etsy OAuth Setup.
6. P5.1 Training Dashboard.
7. P1.5 Agent Task Loop.
8. P2.3 App Artifact Revision Flow.

## Definition Of Done For Future Tasks

- Source code implemented.
- Tests added or updated.
- Documentation updated.
- Manual smoke test completed.
- Generated artifacts and local config are not staged.
- `git diff --check` passes.
- Full test suite passes unless the limitation is documented.
- Commit message clearly describes the completed work.
