from __future__ import annotations

import argparse
import html
import json
import math
import os
import platform
import random
import re
import subprocess
import wave
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from local_llm.media_artifact import slugify
from local_llm.video_encode import resolve_ffmpeg


@dataclass(frozen=True)
class AspectTemplate:
    name: str
    width: int
    height: int
    label: str


@dataclass(frozen=True)
class ShortVideoScene:
    index: int
    title: str
    narration: str
    visual_prompt: str
    caption: str
    duration_sec: float
    asset_query: str
    transition: str


@dataclass(frozen=True)
class ShortVideoPlan:
    topic: str
    title: str
    hook: str
    script: str
    call_to_action: str
    scenes: list[ShortVideoScene]


@dataclass(frozen=True)
class ShortVideoConfig:
    aspect: str = "auto"
    duration_sec: float | None = None
    fps: int = 24
    scene_count: int = 5
    voiceover: bool = True
    background_music: bool = True
    subtitles: bool = True
    mp4: bool = True


@dataclass(frozen=True)
class ShortVideoResult:
    root: Path
    plan: ShortVideoPlan
    config: ShortVideoConfig
    frames: list[Path]
    assets: list[Path]
    asset_plan_path: Path
    config_path: Path
    subtitles_path: Path
    voiceover_path: Path | None
    music_path: Path | None
    mixed_audio_path: Path | None
    video_path: Path | None
    web_ui_path: Path
    manifest_path: Path


ASPECT_TEMPLATES = {
    "landscape": AspectTemplate("landscape", 1280, 720, "16:9 landscape"),
    "portrait": AspectTemplate("portrait", 720, 1280, "9:16 portrait"),
    "square": AspectTemplate("square", 1080, 1080, "1:1 square"),
}
PALETTES = [
    ("#101820", "#f97316", "#e5e7eb", "#38bdf8"),
    ("#151515", "#ef4444", "#f8fafc", "#facc15"),
    ("#0f172a", "#22c55e", "#f5f5f4", "#a78bfa"),
    ("#111827", "#06b6d4", "#f8fafc", "#fb7185"),
    ("#171717", "#f59e0b", "#fafafa", "#84cc16"),
]
TRANSITIONS = ("cut", "push", "zoom", "flash", "wipe")


def choose_aspect(topic: str, requested: str = "auto") -> AspectTemplate:
    requested = requested.strip().lower()
    if requested in ASPECT_TEMPLATES:
        return ASPECT_TEMPLATES[requested]
    text = topic.lower()
    if any(word in text for word in ("tiktok", "reels", "shorts", "youtube short", "portrait", "phone")):
        return ASPECT_TEMPLATES["portrait"]
    if any(word in text for word in ("instagram post", "square")):
        return ASPECT_TEMPLATES["square"]
    return ASPECT_TEMPLATES["landscape"]


def _keywords(topic: str, limit: int = 10) -> list[str]:
    stop = {
        "about",
        "ares",
        "create",
        "generate",
        "make",
        "short",
        "shorts",
        "second",
        "seconds",
        "youtube",
        "tiktok",
        "reels",
        "instagram",
        "video",
        "with",
        "for",
        "and",
        "the",
        "into",
    }
    words = [word.lower() for word in re.findall(r"[A-Za-z0-9]+", topic)]
    unique: list[str] = []
    for word in words:
        if len(word) < 3 or word.isdigit() or word in stop or word in unique:
            continue
        unique.append(word)
    return unique[:limit] or ["local", "creative", "launch"]


def _title(topic: str) -> str:
    words = _keywords(topic, limit=5)
    return " ".join(word.capitalize() for word in words)


def _topic_label(topic: str) -> str:
    title = _title(topic)
    return title.lower() if title else topic.strip()


def _duration_from_topic(topic: str, fallback: float = 20.0) -> float:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds)\b", topic.lower())
    if match:
        return max(3.0, min(90.0, float(match.group(1))))
    return fallback


def plan_short_video(topic: str, config: ShortVideoConfig | None = None) -> ShortVideoPlan:
    config = config or ShortVideoConfig()
    duration = config.duration_sec or _duration_from_topic(topic)
    scene_count = max(3, min(10, config.scene_count))
    scene_duration = duration / scene_count
    keywords = _keywords(topic, limit=scene_count + 2)
    title = _title(topic)
    topic_label = _topic_label(topic)
    hook = f"What if {topic_label} could save hours of work?"
    cta = "Save this idea and ask Ares to build the next version."
    beats = [
        ("Hook", "Open with a bold promise and immediate visual contrast."),
        ("Problem", "Show the friction, delay, or confusing part of the topic."),
        ("Reveal", "Introduce the key idea with a clear before-and-after moment."),
        ("Proof", "Show the result, workflow, or benefit in action."),
        ("CTA", "End with a memorable final frame and simple next action."),
    ]
    scenes: list[ShortVideoScene] = []
    for index in range(scene_count):
        keyword = keywords[index % len(keywords)]
        beat_name, beat_direction = beats[index % len(beats)]
        narration = f"{beat_direction} Focus on {keyword} while showing {topic_label}."
        caption = f"{beat_name}: {keyword.capitalize()}"
        scenes.append(
            ShortVideoScene(
                index=index + 1,
                title=f"{beat_name}: {keyword.capitalize()}",
                narration=narration,
                visual_prompt=f"{keyword}, cinematic short video frame, strong foreground, clean background, high contrast",
                caption=caption,
                duration_sec=scene_duration,
                asset_query=f"{keyword} {title} short video asset",
                transition=TRANSITIONS[index % len(TRANSITIONS)],
            )
        )
    script = "\n".join(f"{scene.index}. {scene.narration}" for scene in scenes)
    return ShortVideoPlan(topic=topic, title=title, hook=hook, script=script, call_to_action=cta, scenes=scenes)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for candidate in ("arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if sum(len(part) for part in current) + len(current) + len(word) > width and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _draw_text_box(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font: ImageFont.ImageFont, max_chars: int, fill: str) -> None:
    x, y = xy
    for line in _wrap(text, max_chars):
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += bbox[3] - bbox[1] + 8


def render_scene_asset(scene: ShortVideoScene, plan: ShortVideoPlan, target: Path, aspect: AspectTemplate) -> None:
    palette = PALETTES[(scene.index - 1) % len(PALETTES)]
    bg, accent, text, alt = palette
    image = Image.new("RGB", (aspect.width, aspect.height), bg)
    draw = ImageDraw.Draw(image)
    rng = random.Random(f"{plan.topic}-{scene.index}")

    for y in range(aspect.height):
        ratio = y / max(1, aspect.height - 1)
        shade = int(18 + ratio * 28)
        draw.line((0, y, aspect.width, y), fill=(shade, shade + 5, shade + 12))

    for _ in range(24):
        x = rng.randrange(0, aspect.width)
        y = rng.randrange(0, aspect.height)
        size = rng.randrange(max(6, aspect.width // 80), max(18, aspect.width // 28))
        color = accent if rng.random() > 0.45 else alt
        if scene.index % 3 == 0:
            draw.ellipse((x, y, x + size, y + size), outline=color, width=max(2, aspect.width // 260))
        elif scene.index % 3 == 1:
            draw.rounded_rectangle((x, y, x + size * 2, y + size), radius=10, outline=color, width=max(2, aspect.width // 260))
        else:
            draw.polygon((x, y + size, x + size, y, x + size * 2, y + size, x + size, y + size * 2), outline=color)

    center_x = aspect.width // 2
    center_y = int(aspect.height * 0.47)
    scale = min(aspect.width, aspect.height)
    if "ninja" in plan.topic.lower() or "dragon" in plan.topic.lower():
        draw.line((int(aspect.width * 0.20), center_y + 80, int(aspect.width * 0.44), center_y - 70), fill=text, width=max(4, scale // 110))
        draw.ellipse((int(aspect.width * 0.18), center_y - 50, int(aspect.width * 0.26), center_y + 30), outline=text, width=max(3, scale // 160))
        draw.polygon(
            (
                int(aspect.width * 0.62),
                center_y,
                int(aspect.width * 0.82),
                center_y - 80,
                int(aspect.width * 0.90),
                center_y,
                int(aspect.width * 0.78),
                center_y + 70,
            ),
            fill="#166534",
            outline=alt,
        )
        draw.polygon(
            (
                int(aspect.width * 0.88),
                center_y - 10,
                int(aspect.width * 0.98),
                center_y - 42,
                int(aspect.width * 0.98),
                center_y + 28,
            ),
            fill="#f97316",
        )
    else:
        radius = int(scale * 0.18)
        draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), outline=accent, width=max(6, scale // 70))
        draw.polygon(
            (
                center_x - radius // 2,
                center_y + radius // 2,
                center_x,
                center_y - radius,
                center_x + radius,
                center_y + radius // 3,
            ),
            outline=alt,
        )

    margin = int(aspect.width * 0.06)
    title_font = _font(max(28, aspect.width // 22), bold=True)
    body_font = _font(max(16, aspect.width // 54))
    caption_font = _font(max(24, aspect.width // 34), bold=True)
    draw.text((margin, margin), plan.title, font=title_font, fill=text)
    draw.text((margin, margin + int(aspect.height * 0.10)), scene.title, font=caption_font, fill=accent)
    _draw_text_box(draw, (margin, int(aspect.height * 0.75)), scene.narration, body_font, max(24, aspect.width // 24), text)
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)


def write_srt(plan: ShortVideoPlan, target: Path) -> Path:
    def stamp(seconds: float) -> str:
        millis = int(round(seconds * 1000))
        ms = millis % 1000
        total = millis // 1000
        s = total % 60
        m = (total // 60) % 60
        h = total // 3600
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    lines: list[str] = []
    cursor = 0.0
    for scene in plan.scenes:
        start = cursor
        end = cursor + scene.duration_sec
        lines.extend([str(scene.index), f"{stamp(start)} --> {stamp(end)}", scene.caption, ""])
        cursor = end
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_script(plan: ShortVideoPlan, target: Path) -> Path:
    lines = [f"# {plan.title}", "", f"Topic: {plan.topic}", "", f"Hook: {plan.hook}", "", "## Script", plan.script, "", f"CTA: {plan.call_to_action}", ""]
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_asset_plan(plan: ShortVideoPlan, target: Path) -> Path:
    asset_plan = {
        "topic": plan.topic,
        "strategy": "local procedural scene generation with backend-ready asset prompts",
        "scenes": [
            {
                "scene": scene.index,
                "caption": scene.caption,
                "asset_query": scene.asset_query,
                "visual_prompt": scene.visual_prompt,
                "local_asset": f"assets/scene-{scene.index:02d}.png",
            }
            for scene in plan.scenes
        ],
    }
    target.write_text(json.dumps(asset_plan, indent=2), encoding="utf-8")
    return target


def write_video_config(config: ShortVideoConfig, aspect: AspectTemplate, target: Path) -> Path:
    payload = {
        "config": asdict(config),
        "selected_aspect": asdict(aspect),
        "aspect_templates": {name: asdict(template) for name, template in ASPECT_TEMPLATES.items()},
        "export": {
            "container": "mp4",
            "video_codec": "libx264 through FFmpeg when available",
            "audio": "mixed voiceover and background music WAV",
        },
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def _write_tone_wav(target: Path, duration_sec: float, frequency: float = 220.0, volume: float = 0.15) -> Path:
    sample_rate = 22050
    frames = int(duration_sec * sample_rate)
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            value = int(32767 * volume * math.sin(2 * math.pi * frequency * index / sample_rate))
            wav.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))
    return target


def create_background_music(target: Path, duration_sec: float) -> Path:
    sample_rate = 22050
    frames = int(duration_sec * sample_rate)
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            t = index / sample_rate
            base = math.sin(2 * math.pi * 110 * t) * 0.08
            pulse = math.sin(2 * math.pi * 220 * t) * 0.035
            beat = 0.06 if int(t * 2) % 2 == 0 and (t * 2) % 1 < 0.08 else 0.0
            value = int(32767 * (base + pulse + beat))
            wav.writeframesraw(max(-32767, min(32767, value)).to_bytes(2, byteorder="little", signed=True))
    return target


def create_voiceover(plan: ShortVideoPlan, target: Path) -> Path:
    text = f"{plan.hook}\n\n{plan.script}\n\n{plan.call_to_action}"
    text_path = target.with_suffix(".txt")
    text_path.write_text(text, encoding="utf-8")
    if platform.system().lower() == "windows":
        escaped_text = text.replace("'", "''")
        escaped_target = str(target).replace("'", "''")
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$s.SetOutputToWaveFile('{escaped_target}'); "
                f"$s.Speak('{escaped_text}'); "
                "$s.Dispose();"
            ),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, check=False)
            if completed.returncode == 0 and target.exists() and target.stat().st_size > 1000:
                return target
        except OSError:
            pass
    return _write_tone_wav(target, sum(scene.duration_sec for scene in plan.scenes), frequency=180.0, volume=0.04)


def mix_audio(voiceover: Path | None, music: Path | None, target: Path) -> Path | None:
    if voiceover is None and music is None:
        return None
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg.available or ffmpeg.executable is None:
        return voiceover or music
    if voiceover is not None and music is not None:
        command = [
            str(ffmpeg.executable),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(voiceover),
            "-i",
            str(music),
            "-filter_complex",
            "[0:a]volume=1.0[a0];[1:a]volume=0.22[a1];[a0][a1]amix=inputs=2:duration=longest",
            str(target),
        ]
    else:
        source = voiceover or music
        assert source is not None
        command = [str(ffmpeg.executable), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), str(target)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return target if completed.returncode == 0 and target.exists() else (voiceover or music)


def compose_video(root: Path, assets: list[Path], audio: Path | None, target: Path, fps: int, durations: list[float]) -> Path | None:
    ffmpeg = resolve_ffmpeg()
    if not ffmpeg.available or ffmpeg.executable is None:
        return None
    concat = root / "video.ffconcat"
    lines = ["ffconcat version 1.0"]
    for asset, duration in zip(assets, durations):
        safe_path = asset.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
        lines.append(f"duration {duration:.8f}")
    if assets:
        safe_path = assets[-1].resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    concat.write_text("\n".join(lines) + "\n", encoding="utf-8")
    command = [
        str(ffmpeg.executable),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
    ]
    if audio is not None and audio.exists():
        command.extend(["-i", str(audio), "-shortest"])
    command.extend(["-vf", f"fps={fps},format=yuv420p", "-movflags", "+faststart", str(target)])
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
    return target if completed.returncode == 0 and target.exists() else None


def write_config_ui(root: Path, plan: ShortVideoPlan, config: ShortVideoConfig, aspect: AspectTemplate, manifest_name: str, config_name: str) -> Path:
    scene_cards = "\n".join(
        f"<article><h3>{html.escape(scene.title)}</h3><p>{html.escape(scene.narration)}</p><small>{html.escape(scene.visual_prompt)}</small></article>"
        for scene in plan.scenes
    )
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(plan.title)} - Ares Short Video Studio</title>
  <style>
    body {{ margin: 0; background: #151515; color: #f5f5f4; font-family: Segoe UI, Arial, sans-serif; }}
    main {{ width: min(1120px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0; }}
    h1 {{ font-size: clamp(32px, 6vw, 68px); margin: 0 0 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }}
    article, .panel {{ border: 1px solid #3a3a3a; border-radius: 8px; padding: 16px; background: #202020; }}
    h3 {{ margin: 0 0 8px; color: #f97316; }}
    p {{ color: #d4d4d8; line-height: 1.5; }}
    code {{ color: #38bdf8; }}
    label {{ display: grid; gap: 6px; margin: 10px 0; color: #d4d4d8; }}
    input, select {{ background: #111; color: #f5f5f4; border: 1px solid #3a3a3a; border-radius: 6px; padding: 10px; }}
  </style>
</head>
<body>
  <main>
    <h1>{html.escape(plan.title)}</h1>
    <section class="panel">
      <p><strong>Topic:</strong> {html.escape(plan.topic)}</p>
      <p><strong>Aspect:</strong> {aspect.label} | <strong>FPS:</strong> {config.fps}</p>
      <p><strong>Manifest:</strong> <code>{manifest_name}</code></p>
      <p><strong>Config:</strong> <code>{config_name}</code></p>
    </section>
    <h2>Config</h2>
    <section class="grid">
      <label>Aspect<select><option>{html.escape(aspect.name)}</option></select></label>
      <label>Duration seconds<input value="{config.duration_sec or ''}"></label>
      <label>Frames per second<input value="{config.fps}"></label>
      <label>Scenes<input value="{config.scene_count}"></label>
    </section>
    <h2>Scenes</h2>
    <section class="grid">{scene_cards}</section>
  </main>
</body>
</html>
"""
    path = root / "studio.html"
    path.write_text(content, encoding="utf-8")
    return path


def create_short_video(topic: str, repo: Path, config: ShortVideoConfig | None = None) -> ShortVideoResult:
    config = config or ShortVideoConfig()
    duration = config.duration_sec or _duration_from_topic(topic)
    config = ShortVideoConfig(
        aspect=config.aspect,
        duration_sec=duration,
        fps=max(1, min(30, config.fps)),
        scene_count=max(3, min(10, config.scene_count)),
        voiceover=config.voiceover,
        background_music=config.background_music,
        subtitles=config.subtitles,
        mp4=config.mp4,
    )
    aspect = choose_aspect(topic, config.aspect)
    plan = plan_short_video(topic, config)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = repo.resolve() / "artifacts" / f"short-video-{slugify(topic)}-{timestamp}"
    assets_dir = root / "assets"
    root.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    script_path = write_script(plan, root / "script.md")
    subtitles_path = write_srt(plan, root / "subtitles.srt")
    asset_plan_path = write_asset_plan(plan, root / "asset_plan.json")
    config_path = write_video_config(config, aspect, root / "ares-short-video.config.json")
    assets: list[Path] = []
    for scene in plan.scenes:
        asset = assets_dir / f"scene-{scene.index:02d}.png"
        render_scene_asset(scene, plan, asset, aspect)
        assets.append(asset)

    voiceover = create_voiceover(plan, root / "voiceover.wav") if config.voiceover else None
    music = create_background_music(root / "background_music.wav", duration) if config.background_music else None
    mixed_audio = mix_audio(voiceover, music, root / "audio_mix.wav")
    video = compose_video(root, assets, mixed_audio, root / "short_video.mp4", config.fps, [scene.duration_sec for scene in plan.scenes]) if config.mp4 else None
    web_ui = write_config_ui(root, plan, config, aspect, "ares-short-video.json", config_path.name)

    manifest = {
        "kind": "short-video",
        "topic": topic,
        "created_at": timestamp,
        "aspect": asdict(aspect),
        "config": asdict(config),
        "plan": asdict(plan),
        "script": script_path.name,
        "subtitles": subtitles_path.name,
        "asset_plan": asset_plan_path.name,
        "video_config": config_path.name,
        "assets": [str(path.relative_to(root)) for path in assets],
        "voiceover": voiceover.name if voiceover is not None else None,
        "background_music": music.name if music is not None else None,
        "audio_mix": mixed_audio.name if mixed_audio is not None else None,
        "video": video.name if video is not None else None,
        "web_ui": web_ui.name,
        "pipeline": [
            "topic-to-script",
            "scene-planning",
            "asset-search-generation",
            "subtitles",
            "voiceover-tts",
            "background-music",
            "ffmpeg-composition",
            "aspect-template",
            "config-system",
            "web-ui-config",
        ],
    }
    manifest_path = root / "ares-short-video.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return ShortVideoResult(
        root=root,
        plan=plan,
        config=config,
        frames=assets,
        assets=assets,
        asset_plan_path=asset_plan_path,
        config_path=config_path,
        subtitles_path=subtitles_path,
        voiceover_path=voiceover,
        music_path=music,
        mixed_audio_path=mixed_audio,
        video_path=video,
        web_ui_path=web_ui,
        manifest_path=manifest_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a full Ares short-video production artifact.")
    parser.add_argument("topic", nargs="+")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--aspect", choices=["auto", "landscape", "portrait", "square"], default="auto")
    parser.add_argument("--duration", type=float, default=None)
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--scenes", type=int, default=5)
    parser.add_argument("--no-voiceover", action="store_true")
    parser.add_argument("--no-music", action="store_true")
    parser.add_argument("--no-mp4", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = create_short_video(
        " ".join(args.topic),
        repo=args.repo,
        config=ShortVideoConfig(
            aspect=args.aspect,
            duration_sec=args.duration,
            fps=args.fps,
            scene_count=args.scenes,
            voiceover=not args.no_voiceover,
            background_music=not args.no_music,
            mp4=not args.no_mp4,
        ),
    )
    print(f"Created short-video artifact: {result.root}")
    if result.video_path is not None:
        print(f"Video: {result.video_path}")
    print(f"Script: {result.root / 'script.md'}")
    print(f"Subtitles: {result.subtitles_path}")
    print(f"Studio UI: {result.web_ui_path}")


if __name__ == "__main__":
    main()
