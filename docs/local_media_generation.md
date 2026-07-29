# Local Media Generation

Ares includes a small ViMax-inspired local media pipeline. It turns a prompt
into a storyboard, keyframe PNGs, a frame sequence, and an animated GIF.

The goal is a local creative planning tool:

1. Plan the idea into shots.
2. Keep one style and palette across shots.
3. Render keyframes and motion frames locally.
4. Save a storyboard and manifest for later review.

It does not download or run a large diffusion or video model. The first version
uses deterministic procedural drawing through Pillow, which is light enough for
ordinary laptops and useful for previews, concept boards, and app mockups.

## Run It

```powershell
python -m local_llm.media_artifact "Create a cinematic Ares launch video with code, dashboard, and logo"
```

Optional controls:

```powershell
python -m local_llm.media_artifact "Generate product images for a Shopify launch" --shots 5 --width 960 --height 540 --frames-per-shot 10 --fps 8
```

Generated media is written under:

```text
artifacts\media-<brief-slug>-<timestamp>\
```

Each run includes:

- `video.gif`
- `storyboard.png`
- `storyboard.md`
- `ares-media.json`
- `keyframes\shot-*.png`
- `frames\shot-*-frame-*.png`

## How This Helps Ares

This gives Ares the same kind of production shape as agentic video tools:
planning, shot design, visual consistency, render outputs, and a manifest. The
heavy model piece can be added later behind the same interface.

Future upgrades can plug in local models such as Stable Diffusion, ComfyUI,
AnimateDiff, or other locally runnable image/video systems. The artifact format
can stay the same while the renderer becomes stronger.
