# Local Media Generation

Ares includes a ViMax-inspired local media pipeline. It turns a prompt into a
storyboard, keyframe PNGs, a frame sequence, an animated GIF, and an MP4 when
FFmpeg is available.

The goal is a local creative planning tool:

1. Plan the idea into shots.
2. Keep one style and palette across shots.
3. Render keyframes and motion frames locally.
4. Save a storyboard and manifest for later review.

It does not download or run a large diffusion or video model by default. The
first renderer uses deterministic procedural drawing through Pillow, which is
light enough for ordinary laptops and useful for previews, concept boards, and
app mockups.

## Run It

```powershell
python -m local_llm.media_artifact "Create a cinematic Ares launch video with code, dashboard, and logo"
```

Optional controls:

```powershell
python -m local_llm.media_artifact "Generate product images for a Shopify launch" --shots 5 --width 960 --height 540 --frames-per-shot 10 --fps 8
```

List backend status:

```powershell
python -m local_llm.media_artifact --list-backends
```

Generated media is written under:

```text
artifacts\media-<brief-slug>-<timestamp>\
```

Each run includes:

- `video.gif`
- `video.mp4` when FFmpeg is available
- `storyboard.png`
- `storyboard.md`
- `ares-media.json`
- `remotion\`
- `keyframes\shot-*.png`
- `frames\shot-*-frame-*.png`

## How This Helps Ares

This gives Ares the same kind of production shape as agentic video tools:
planning, shot design, visual consistency, render outputs, and a manifest. The
heavy model piece can be added later behind the same interface.

## Combined Backend Design

Ares now has a backend registry for the repositories you requested:

- **ViMax**: agent loop, idea/script/novel-to-video planning, storyboard review,
  and render checkpoints.
- **HunyuanVideo**: large text-to-video and image-to-video foundation model
  bridge for CUDA workstations.
- **CogVideoX**: text/image-to-video bridge with prompt optimization and
  Diffusers-oriented workflows.
- **Toonflow**: short-drama workflow ideas: scriptwriting, characters,
  storyboard, and animation.
- **Open Generative AI**: self-hosted studio shape with a model catalog and
  image/video generation integrations.
- **Remotion**: React video export, editable animated compositions, and MP4
  rendering through Node.js.
- **Ares Procedural Renderer**: always-available local fallback.
- **FFmpeg**: local MP4 encoding, future audio/video muxing, and media
  inspection.
- **MoneyPrinterTurbo**: topic-to-short-video automation shape: hook, script,
  captions, voice, assets, and social-video packaging.
- **imaginAIry**: optional Stable Diffusion and Stable Video Diffusion command
  backend for real image/video generation when separately installed.
- **InfiniteTalk**: optional audio-driven talking-video and dubbing backend.
- **PyTorch Image Models**: optional timm model zoo for future visual scoring
  and image classification checks.
- **Deep Learning For Image Processing**: reference roadmap for classification,
  detection, segmentation, and keypoint QA.

Configure optional external backends with environment variables:

```text
ARES_VIMAX_DIR
ARES_HUNYUANVIDEO_DIR
ARES_COGVIDEO_DIR
ARES_TOONFLOW_URL
ARES_OPEN_GENERATIVE_AI_URL
ARES_FFMPEG_PATH
ARES_MONEYPRINTER_DIR
ARES_IMAGINAIRY_CMD
ARES_INFINITETALK_DIR
```

When an external backend is not configured, Ares still creates the local
storyboard/GIF artifact and writes a handoff-ready `prompt_package` into
`ares-media.json`.

## Remotion Export

Every Ares media artifact now includes a `remotion\` folder. This is a real
React video project inspired by Remotion's code-first workflow.

Open the generated `remotion\` folder and run:

```powershell
npm install
npm run preview
```

Render MP4:

```powershell
npm run render
```

The generated project includes:

- `package.json`
- `src\index.ts`
- `src\Root.tsx`
- `src\Video.tsx`
- `src\style.css`
- `public\scene-data.json`

Remotion has its own license terms, including special commercial-use conditions
in some cases. Check the Remotion license before using rendered videos
commercially.

## FFmpeg MP4 Export

Ares uses FFmpeg when it is available. It writes PNG frames first, then creates
`video.mp4` using a concat file so frame timing stays stable.

Disable MP4 export:

```powershell
python -m local_llm.media_artifact "Create a product video" --no-mp4
```

FFmpeg licensing depends on the build and enabled codecs. Check the FFmpeg
license and your installed build before commercial distribution.

Future upgrades can execute those bridges directly, call local HTTP services,
or plug in local models such as Stable Diffusion, ComfyUI, AnimateDiff, or other
locally runnable image/video systems. The artifact format can stay the same
while the renderer becomes stronger.
