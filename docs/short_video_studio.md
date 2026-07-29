# Ares Short Video Studio

Ares Short Video Studio is the MoneyPrinterTurbo-style production path for
video prompts.

It creates a complete local production folder:

1. Topic to script.
2. Scene planning.
3. Local asset search/generation metadata.
4. Scene image generation.
5. Subtitles as `.srt`.
6. Voiceover/TTS as `voiceover.wav`.
7. Background music as `background_music.wav`.
8. Audio mix as `audio_mix.wav`.
9. FFmpeg video composition as `short_video.mp4`.
10. Aspect-ratio template selection.
11. Local `studio.html` config/review UI.

## Run

```powershell
python -m local_llm.short_video "create a 15 seconds YouTube short about Ares coding agent"
```

Useful options:

```powershell
python -m local_llm.short_video "make a TikTok product video" --aspect portrait --duration 20 --scenes 5
python -m local_llm.short_video "create a square promo video" --aspect square --no-voiceover
```

## Output

Generated folders are written under:

```text
artifacts\short-video-<topic-slug>-<timestamp>\
```

Each folder includes:

- `script.md`
- `subtitles.srt`
- `asset_plan.json`
- `ares-short-video.config.json`
- `voiceover.wav`
- `background_music.wav`
- `audio_mix.wav`
- `short_video.mp4`
- `assets\scene-*.png`
- `studio.html`
- `ares-short-video.json`

## Aspect Templates

- `landscape`: 1280x720
- `portrait`: 720x1280
- `square`: 1080x1080
- `auto`: chooses portrait for TikTok/Reels/YouTube Shorts style prompts.

## Limits

This is now a full production pipeline, but the first asset generator is still
local and illustrative. Real stock search, diffusion-image generation,
high-quality TTS, and advanced audio mastering can plug into the same artifact
format later.
