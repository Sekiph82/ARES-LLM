from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class MediaShot:
    index: int
    title: str
    prompt: str
    duration_sec: float
    camera: str
    motion: str
    palette: list[str]


@dataclass(frozen=True)
class MediaPlan:
    title: str
    brief: str
    style: str
    shots: list[MediaShot]


@dataclass(frozen=True)
class MediaArtifactResult:
    root: Path
    plan: MediaPlan
    keyframes: list[Path]
    frames: list[Path]
    video_path: Path
    storyboard_image: Path
    storyboard_markdown: Path
    manifest_path: Path


PALETTES = [
    ["#0f172a", "#ef4444", "#f8fafc", "#94a3b8", "#111827"],
    ["#111827", "#22c55e", "#f5f5f4", "#38bdf8", "#27272a"],
    ["#18181b", "#f97316", "#f4f4f5", "#a1a1aa", "#3f3f46"],
    ["#101828", "#f59e0b", "#e0f2fe", "#64748b", "#1e293b"],
    ["#141414", "#e11d48", "#fafafa", "#737373", "#262626"],
]
CAMERAS = ["wide establishing shot", "slow push-in", "orbit pan", "low-angle reveal", "close detail pass"]
MOTIONS = ["parallax drift", "light sweep", "rising panels", "tracking glow", "cinematic zoom"]
STYLE_KEYWORDS = {
    "shop": "commerce launch film",
    "store": "commerce launch film",
    "product": "premium product reveal",
    "code": "technical coding montage",
    "coding": "technical coding montage",
    "dashboard": "software dashboard promo",
    "game": "interactive game teaser",
    "logo": "brand identity motion",
}


def slugify(text: str, fallback: str = "ares-media") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug[:48].strip("-") or fallback


def _rng_from_text(text: str) -> random.Random:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _keywords(brief: str, limit: int = 8) -> list[str]:
    stop = {
        "a",
        "an",
        "and",
        "app",
        "build",
        "create",
        "for",
        "from",
        "generate",
        "make",
        "of",
        "render",
        "the",
        "to",
        "video",
        "with",
    }
    words = [word.lower() for word in re.findall(r"[A-Za-z0-9]+", brief)]
    unique: list[str] = []
    for word in words:
        if len(word) < 3 or word in stop or word in unique:
            continue
        unique.append(word)
    return unique[:limit] or ["ares", "local", "creative", "studio"]


def _title_from_brief(brief: str) -> str:
    words = _keywords(brief, limit=5)
    return " ".join(word.capitalize() for word in words)


def _style_from_brief(brief: str) -> str:
    text = brief.lower()
    for keyword, style in STYLE_KEYWORDS.items():
        if keyword in text:
            return style
    return "local cinematic storyboard"


def plan_media(brief: str, shot_count: int = 4) -> MediaPlan:
    shot_count = max(1, min(8, shot_count))
    rng = _rng_from_text(brief)
    words = _keywords(brief, limit=shot_count + 2)
    title = _title_from_brief(brief)
    style = _style_from_brief(brief)
    palette = rng.choice(PALETTES)
    shots: list[MediaShot] = []
    beats = [
        "Open with the main idea and establish the world.",
        "Show the core object, user, or interface in motion.",
        "Reveal the strongest feature with a clear visual rhythm.",
        "Close with a confident final frame and next action.",
    ]
    for index in range(shot_count):
        word = words[index % len(words)]
        beat = beats[index % len(beats)]
        shots.append(
            MediaShot(
                index=index + 1,
                title=f"{word.capitalize()} Beat",
                prompt=f"{beat} Keep visual focus on {word} for: {brief}",
                duration_sec=1.5,
                camera=CAMERAS[(index + rng.randrange(len(CAMERAS))) % len(CAMERAS)],
                motion=MOTIONS[(index + rng.randrange(len(MOTIONS))) % len(MOTIONS)],
                palette=palette,
            )
        )
    return MediaPlan(title=title, brief=brief, style=style, shots=shots)


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "arialbd.ttf" if bold else "arial.ttf",
        "segoeuib.ttf" if bold else "segoeui.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1.0 - t) + b[i] * t) for i in range(3))


def _draw_gradient(draw: ImageDraw.ImageDraw, size: tuple[int, int], top: str, bottom: str) -> None:
    width, height = size
    top_rgb = _hex_to_rgb(top)
    bottom_rgb = _hex_to_rgb(bottom)
    for y in range(height):
        color = _blend(top_rgb, bottom_rgb, y / max(1, height - 1))
        draw.line([(0, y), (width, y)], fill=color)


def _load_logo(repo: Path, max_width: int) -> Image.Image | None:
    logo_path = repo / "assets" / "ares_logo.png"
    if not logo_path.exists():
        return None
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except OSError:
        return None
    ratio = max_width / max(1, logo.width)
    return logo.resize((max_width, max(1, int(logo.height * ratio))), Image.Resampling.LANCZOS)


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: str,
    width: int,
    line_gap: int = 6,
) -> None:
    x, y = xy
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        lines.extend(textwrap.wrap(paragraph, width=width) or [""])
    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line or "Ag", font=font)
        y += (bbox[3] - bbox[1]) + line_gap


def _fit_font(text: str, max_size: int, min_size: int, max_width: int, bold: bool = False) -> ImageFont.ImageFont:
    probe = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(probe)
    for size in range(max_size, min_size - 1, -1):
        font = _font(size, bold=bold)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _font(min_size, bold=bold)


def _ellipsize(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    probe = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(probe)
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return text
    suffix = "..."
    trimmed = text
    while trimmed:
        candidate = trimmed.rstrip() + suffix
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            return candidate
        trimmed = trimmed[:-1]
    return suffix


def render_frame(
    plan: MediaPlan,
    shot: MediaShot,
    frame_index: int,
    frames_per_shot: int,
    size: tuple[int, int],
    repo: Path,
) -> Image.Image:
    width, height = size
    progress = frame_index / max(1, frames_per_shot - 1)
    rng = _rng_from_text(f"{plan.brief}-{shot.index}")
    image = Image.new("RGB", size, shot.palette[0])
    draw = ImageDraw.Draw(image)
    _draw_gradient(draw, size, shot.palette[0], shot.palette[4])

    accent = shot.palette[1]
    light = shot.palette[2]
    muted = shot.palette[3]
    center_x = width * (0.52 + math.sin(progress * math.pi * 2) * 0.04)
    center_y = height * (0.48 + math.cos(progress * math.pi * 2) * 0.03)
    radius = int(min(width, height) * (0.17 + progress * 0.04))

    for layer in range(5):
        offset = layer * int(width * 0.04)
        alpha_color = accent if layer % 2 == 0 else muted
        x0 = int(center_x - radius - offset * 0.35)
        y0 = int(center_y - radius * 0.65 + offset * 0.12)
        x1 = int(center_x + radius + offset)
        y1 = int(center_y + radius * 0.65 + offset * 0.12)
        draw.rounded_rectangle((x0, y0, x1, y1), radius=18, outline=alpha_color, width=3)

    stripe_x = int((progress * width * 1.3) - width * 0.2)
    draw.polygon(
        [
            (stripe_x, 0),
            (stripe_x + int(width * 0.16), 0),
            (stripe_x - int(width * 0.12), height),
            (stripe_x - int(width * 0.28), height),
        ],
        fill=accent,
    )

    for _ in range(28):
        x = rng.randrange(0, width)
        y = rng.randrange(0, height)
        dot = rng.randrange(1, 4)
        draw.rectangle((x, y, x + dot, y + dot), fill=muted)

    logo = _load_logo(repo, max_width=max(80, width // 7))
    if logo is not None:
        image.paste(logo, (width - logo.width - 28, 22), logo)

    logo_space = (logo.width + 42) if logo is not None else 0
    title_width = max(140, width - logo_space - 70)
    title_font = _fit_font(plan.title, max(24, width // 24), 14, title_width, bold=True)
    body_font = _font(max(14, width // 48))
    small_font = _font(max(12, width // 62), bold=True)
    draw.text((32, 26), _ellipsize(plan.title, title_font, title_width), font=title_font, fill=light)
    draw.text((34, 76), f"Shot {shot.index:02d} / {len(plan.shots):02d}", font=small_font, fill=accent)
    _draw_wrapped(draw, (34, height - 130), shot.prompt, body_font, light, width=58)
    draw.text((34, height - 40), f"{shot.camera} | {shot.motion}", font=small_font, fill=muted)
    return image


def _write_storyboard_markdown(root: Path, plan: MediaPlan, video_path: Path, keyframes: list[Path]) -> Path:
    lines = [
        f"# {plan.title}",
        "",
        f"Brief: {plan.brief}",
        f"Style: {plan.style}",
        f"Video: {video_path.name}",
        "",
        "## Shots",
        "",
    ]
    for shot, keyframe in zip(plan.shots, keyframes):
        lines.extend(
            [
                f"### Shot {shot.index}: {shot.title}",
                "",
                f"- Prompt: {shot.prompt}",
                f"- Camera: {shot.camera}",
                f"- Motion: {shot.motion}",
                f"- Keyframe: {keyframe.relative_to(root)}",
                "",
            ]
        )
    path = root / "storyboard.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_storyboard_image(root: Path, plan: MediaPlan, keyframes: list[Path]) -> Path:
    thumbs: list[Image.Image] = []
    for path in keyframes:
        thumbs.append(Image.open(path).convert("RGB").resize((320, 180), Image.Resampling.LANCZOS))
    width = 680
    height = 130 + len(thumbs) * 220
    image = Image.new("RGB", (width, height), "#151515")
    draw = ImageDraw.Draw(image)
    draw.text((28, 24), plan.title, font=_font(28, bold=True), fill="#f8fafc")
    draw.text((30, 62), plan.style, font=_font(15), fill="#f97316")
    y = 108
    for shot, thumb in zip(plan.shots, thumbs):
        image.paste(thumb, (28, y))
        draw.text((370, y + 8), f"Shot {shot.index}: {shot.title}", font=_font(17, bold=True), fill="#f8fafc")
        _draw_wrapped(draw, (370, y + 40), shot.prompt, _font(13), "#d4d4d8", width=35)
        y += 220
    path = root / "storyboard.png"
    image.save(path)
    return path


def create_media_artifact(
    brief: str,
    repo: Path,
    kind: str = "auto",
    shot_count: int = 4,
    width: int = 960,
    height: int = 540,
    frames_per_shot: int = 12,
    fps: int = 8,
) -> MediaArtifactResult:
    repo = repo.resolve()
    width = max(240, min(1920, width))
    height = max(160, min(1080, height))
    frames_per_shot = max(1, min(48, frames_per_shot))
    fps = max(1, min(30, fps))
    plan = plan_media(brief, shot_count=shot_count)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = repo / "artifacts" / f"media-{slugify(brief)}-{timestamp}"
    frames_dir = root / "frames"
    keyframes_dir = root / "keyframes"
    frames_dir.mkdir(parents=True, exist_ok=True)
    keyframes_dir.mkdir(parents=True, exist_ok=True)

    frames: list[Path] = []
    keyframes: list[Path] = []
    rendered: list[Image.Image] = []
    for shot in plan.shots:
        for frame_index in range(frames_per_shot):
            image = render_frame(plan, shot, frame_index, frames_per_shot, (width, height), repo)
            frame_path = frames_dir / f"shot-{shot.index:02d}-frame-{frame_index + 1:03d}.png"
            image.save(frame_path)
            frames.append(frame_path)
            rendered.append(image)
            if frame_index == 0:
                keyframe_path = keyframes_dir / f"shot-{shot.index:02d}.png"
                image.save(keyframe_path)
                keyframes.append(keyframe_path)

    video_path = root / ("video.gif" if kind in {"auto", "gif", "video"} else "image-sequence.gif")
    if rendered:
        rendered[0].save(
            video_path,
            save_all=True,
            append_images=rendered[1:],
            duration=int(1000 / fps),
            loop=0,
        )
    storyboard_image = _write_storyboard_image(root, plan, keyframes)
    storyboard_markdown = _write_storyboard_markdown(root, plan, video_path, keyframes)
    manifest = {
        "name": root.name,
        "kind": "local-media",
        "format": "animated-gif",
        "created_at": timestamp,
        "brief": brief,
        "style": plan.style,
        "size": {"width": width, "height": height},
        "fps": fps,
        "frames_per_shot": frames_per_shot,
        "shot_count": len(plan.shots),
        "video": video_path.name,
        "storyboard": storyboard_markdown.name,
        "storyboard_image": storyboard_image.name,
        "keyframes": [str(path.relative_to(root)) for path in keyframes],
        "frames": [str(path.relative_to(root)) for path in frames],
        "plan": asdict(plan),
    }
    manifest_path = root / "ares-media.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return MediaArtifactResult(
        root=root,
        plan=plan,
        keyframes=keyframes,
        frames=frames,
        video_path=video_path,
        storyboard_image=storyboard_image,
        storyboard_markdown=storyboard_markdown,
        manifest_path=manifest_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create local image/video media artifacts with Ares.")
    parser.add_argument("brief", nargs="+", help="Image, storyboard, or video brief.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--kind", choices=["auto", "gif", "video", "image"], default="auto")
    parser.add_argument("--shots", type=int, default=4)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--frames-per-shot", type=int, default=12)
    parser.add_argument("--fps", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = create_media_artifact(
        " ".join(args.brief),
        repo=args.repo,
        kind=args.kind,
        shot_count=args.shots,
        width=args.width,
        height=args.height,
        frames_per_shot=args.frames_per_shot,
        fps=args.fps,
    )
    print(f"Created media artifact: {result.root}")
    print(f"Video: {result.video_path}")
    print(f"Storyboard: {result.storyboard_markdown}")
    print(f"Keyframes: {len(result.keyframes)}")


if __name__ == "__main__":
    main()
