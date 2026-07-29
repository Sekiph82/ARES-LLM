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

from local_llm.media_backends import backend_prompt_package, choose_backend, format_backend_statuses
from local_llm.video_encode import encode_mp4_from_frames


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
    backend_name: str
    remotion_project: Path | None
    keyframes: list[Path]
    frames: list[Path]
    video_path: Path
    mp4_path: Path | None
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
        "second",
        "seconds",
        "the",
        "to",
        "video",
        "with",
    }
    words = [word.lower() for word in re.findall(r"[A-Za-z0-9]+", brief)]
    unique: list[str] = []
    for word in words:
        if word.isdigit() or len(word) < 3 or word in stop or word in unique:
            continue
        unique.append(word)
    return unique[:limit] or ["ares", "local", "creative", "studio"]


def _duration_from_brief(brief: str) -> float | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(?:sec|secs|second|seconds)\b", brief.lower())
    if not match:
        return None
    return max(1.0, min(60.0, float(match.group(1))))


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


def _draw_moonlit_scene(draw: ImageDraw.ImageDraw, size: tuple[int, int], progress: float) -> None:
    width, height = size
    moon_x = int(width * 0.78)
    moon_y = int(height * 0.18)
    moon_r = max(18, int(min(width, height) * 0.075))
    draw.ellipse((moon_x - moon_r, moon_y - moon_r, moon_x + moon_r, moon_y + moon_r), fill="#e5e7eb")
    draw.ellipse((moon_x - moon_r // 3, moon_y - moon_r, moon_x + moon_r, moon_y + moon_r), fill="#111827")

    horizon = int(height * 0.76)
    mountains = [
        (0, horizon, int(width * 0.20), int(height * 0.45), int(width * 0.42), horizon),
        (int(width * 0.26), horizon, int(width * 0.52), int(height * 0.38), int(width * 0.82), horizon),
        (int(width * 0.62), horizon, int(width * 0.86), int(height * 0.48), width, horizon),
    ]
    for mountain in mountains:
        draw.polygon(mountain, fill="#0b1220")
    draw.rectangle((0, horizon, width, height), fill="#0f172a")
    mist_y = int(horizon - 20 + math.sin(progress * math.pi * 2) * 4)
    draw.line((0, mist_y, width, mist_y), fill="#38bdf8", width=max(1, height // 160))


def _draw_ninja(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, progress: float) -> None:
    cx, cy = center
    s = scale
    black = "#050505"
    cloth = "#111827"
    edge = "#e5e7eb"
    accent = "#ef4444"

    head_r = int(26 * s)
    body_w = int(38 * s)
    body_h = int(72 * s)
    draw.ellipse((cx - head_r, cy - int(92 * s), cx + head_r, cy - int(40 * s)), fill=black, outline=edge, width=max(1, int(2 * s)))
    draw.polygon(
        [
            (cx - int(18 * s), cy - int(66 * s)),
            (cx + int(18 * s), cy - int(66 * s)),
            (cx + int(11 * s), cy - int(54 * s)),
            (cx - int(11 * s), cy - int(54 * s)),
        ],
        fill=edge,
    )
    draw.polygon(
        [
            (cx - body_w, cy - int(38 * s)),
            (cx + body_w, cy - int(38 * s)),
            (cx + int(25 * s), cy + body_h),
            (cx - int(25 * s), cy + body_h),
        ],
        fill=cloth,
        outline=edge,
    )
    scarf = int(math.sin(progress * math.pi * 2) * 10 * s)
    draw.polygon(
        [
            (cx - int(20 * s), cy - int(48 * s)),
            (cx - int(84 * s), cy - int(62 * s) + scarf),
            (cx - int(28 * s), cy - int(32 * s)),
        ],
        fill=accent,
    )
    arm_y = cy - int(8 * s)
    sword_tip = (cx + int(145 * s), cy - int(92 * s) + int(progress * 22 * s))
    sword_base = (cx + int(10 * s), arm_y)
    draw.line((cx - int(52 * s), arm_y + int(18 * s), cx + int(45 * s), arm_y - int(8 * s)), fill=edge, width=max(3, int(6 * s)))
    draw.line((sword_base, sword_tip), fill="#f8fafc", width=max(2, int(4 * s)))
    draw.line((cx - int(16 * s), cy + body_h, cx - int(70 * s), cy + int(118 * s)), fill=black, width=max(6, int(11 * s)))
    draw.line((cx + int(16 * s), cy + body_h, cx + int(62 * s), cy + int(112 * s)), fill=black, width=max(6, int(11 * s)))


def _draw_dragon(draw: ImageDraw.ImageDraw, center: tuple[int, int], scale: float, progress: float) -> None:
    cx, cy = center
    s = scale
    body = "#166534"
    belly = "#f59e0b"
    wing = "#14532d"
    edge = "#bbf7d0"
    fire = "#f97316"

    points: list[tuple[int, int]] = []
    for i in range(9):
        x = cx - int(i * 34 * s)
        y = cy + int(math.sin(i * 0.9 + progress * math.pi * 2) * 26 * s)
        points.append((x, y))
    for index, point in enumerate(points[:-1]):
        next_point = points[index + 1]
        draw.line((point, next_point), fill=body, width=max(12, int(30 * s)))
        draw.line((point, next_point), fill=edge, width=max(2, int(4 * s)))

    head_x, head_y = points[0]
    head = [
        (head_x + int(48 * s), head_y - int(22 * s)),
        (head_x + int(92 * s), head_y),
        (head_x + int(48 * s), head_y + int(26 * s)),
        (head_x + int(22 * s), head_y + int(10 * s)),
        (head_x + int(22 * s), head_y - int(10 * s)),
    ]
    draw.polygon(head, fill=body, outline=edge)
    draw.ellipse((head_x + int(56 * s), head_y - int(10 * s), head_x + int(66 * s), head_y), fill="#f8fafc")
    draw.polygon(
        [
            (head_x + int(24 * s), head_y - int(18 * s)),
            (head_x + int(2 * s), head_y - int(58 * s)),
            (head_x + int(54 * s), head_y - int(28 * s)),
        ],
        fill=wing,
        outline=edge,
    )
    draw.polygon(
        [
            (head_x - int(54 * s), head_y - int(4 * s)),
            (head_x - int(118 * s), head_y - int(86 * s)),
            (head_x - int(8 * s), head_y - int(58 * s)),
        ],
        fill=wing,
        outline=edge,
    )
    draw.polygon(
        [
            (head_x - int(70 * s), head_y + int(12 * s)),
            (head_x - int(142 * s), head_y + int(86 * s)),
            (head_x - int(14 * s), head_y + int(58 * s)),
        ],
        fill=wing,
        outline=edge,
    )
    draw.line((head_x + int(4 * s), head_y + int(14 * s), head_x + int(52 * s), head_y + int(22 * s)), fill=belly, width=max(2, int(5 * s)))
    flame_start = (head_x + int(88 * s), head_y + int(3 * s))
    flame_end = (head_x + int(170 * s), head_y - int(14 * s) + int(progress * 18 * s))
    draw.polygon(
        [
            flame_start,
            (flame_end[0] - int(24 * s), flame_end[1] - int(28 * s)),
            flame_end,
            (flame_end[0] - int(18 * s), flame_end[1] + int(26 * s)),
        ],
        fill=fire,
    )


def _draw_subject_scene(
    image: Image.Image,
    plan: MediaPlan,
    shot: MediaShot,
    progress: float,
    size: tuple[int, int],
) -> bool:
    text = f"{plan.brief} {shot.title} {shot.prompt}".lower()
    has_ninja = "ninja" in text or "samurai" in text
    has_dragon = "dragon" in text
    has_fight = "fight" in text or "battle" in text or "duel" in text
    if not (has_ninja or has_dragon or has_fight):
        return False

    width, height = size
    draw = ImageDraw.Draw(image)
    _draw_moonlit_scene(draw, size, progress)
    scale = min(width / 960, height / 540)
    if has_ninja or has_fight:
        x = int(width * (0.28 + math.sin(progress * math.pi) * 0.06))
        y = int(height * 0.60)
        _draw_ninja(draw, (x, y), scale, progress)
    if has_dragon or has_fight:
        x = int(width * (0.78 - math.sin(progress * math.pi) * 0.05))
        y = int(height * 0.43)
        _draw_dragon(draw, (x, y), scale, progress)
    if has_fight:
        clash_x = int(width * 0.52)
        clash_y = int(height * 0.44)
        for radius in (18, 34, 52):
            r = int(radius * scale * (1.0 + progress * 0.5))
            draw.ellipse((clash_x - r, clash_y - r, clash_x + r, clash_y + r), outline="#facc15", width=max(2, int(4 * scale)))
    return True


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
    subject_scene = _draw_subject_scene(image, plan, shot, progress, size)

    accent = shot.palette[1]
    light = shot.palette[2]
    muted = shot.palette[3]
    center_x = width * (0.52 + math.sin(progress * math.pi * 2) * 0.04)
    center_y = height * (0.48 + math.cos(progress * math.pi * 2) * 0.03)
    radius = int(min(width, height) * (0.17 + progress * 0.04))

    if not subject_scene:
        for layer in range(5):
            offset = layer * int(width * 0.04)
            alpha_color = accent if layer % 2 == 0 else muted
            x0 = int(center_x - radius - offset * 0.35)
            y0 = int(center_y - radius * 0.65 + offset * 0.12)
            x1 = int(center_x + radius + offset)
            y1 = int(center_y + radius * 0.65 + offset * 0.12)
            draw.rounded_rectangle((x0, y0, x1, y1), radius=18, outline=alpha_color, width=3)

    stripe_x = int((progress * width * 1.3) - width * 0.2)
    if not subject_scene:
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
    backend: str = "auto",
    remotion: bool = True,
    mp4: bool = True,
) -> MediaArtifactResult:
    repo = repo.resolve()
    width = max(240, min(1920, width))
    height = max(160, min(1080, height))
    frames_per_shot = max(1, min(48, frames_per_shot))
    fps = max(1, min(30, fps))
    backend_status = choose_backend(backend, brief=brief)
    prompt_package = backend_prompt_package(brief, backend_status.spec)
    plan = plan_media(brief, shot_count=shot_count)
    requested_duration_sec = _duration_from_brief(brief)
    if requested_duration_sec is not None:
        total_frames = min(900, max(len(plan.shots), int(round(requested_duration_sec * fps))))
        frames_per_shot = max(1, total_frames // max(1, len(plan.shots)))
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
    mp4_path = None
    mp4_result = None
    if mp4:
        mp4_result = encode_mp4_from_frames(frames_dir, root / "video.mp4", fps=fps)
        if mp4_result.ok:
            mp4_path = mp4_result.output
    storyboard_image = _write_storyboard_image(root, plan, keyframes)
    storyboard_markdown = _write_storyboard_markdown(root, plan, video_path, keyframes)
    remotion_project = None
    if remotion:
        from local_llm.remotion_artifact import create_remotion_artifact

        remotion_project = create_remotion_artifact(brief, root=root, plan=plan, fps=fps, width=width, height=height)
    manifest = {
        "name": root.name,
        "kind": "local-media",
        "format": "animated-gif",
        "created_at": timestamp,
        "brief": brief,
        "backend": {
            "selected": backend_status.spec.name,
            "display_name": backend_status.spec.display_name,
            "repo_url": backend_status.spec.repo_url,
            "configured": backend_status.configured,
            "reason": backend_status.reason,
            "launch_hint": backend_status.launch_hint,
            "modes": list(backend_status.spec.modes),
            "strengths": list(backend_status.spec.strengths),
            "min_vram_gb": backend_status.spec.min_vram_gb,
        },
        "prompt_package": prompt_package,
        "style": plan.style,
        "size": {"width": width, "height": height},
        "fps": fps,
        "frames_per_shot": frames_per_shot,
        "shot_count": len(plan.shots),
        "duration_sec": round(len(plan.shots) * frames_per_shot / fps, 3),
        "requested_duration_sec": requested_duration_sec,
        "video": video_path.name,
        "video_mp4": mp4_path.name if mp4_path is not None else None,
        "ffmpeg": {
            "attempted": mp4,
            "ok": bool(mp4_result.ok) if mp4_result is not None else False,
            "message": mp4_result.message if mp4_result is not None else "MP4 export was disabled.",
            "command": mp4_result.command if mp4_result is not None else [],
        },
        "storyboard": storyboard_markdown.name,
        "storyboard_image": storyboard_image.name,
        "remotion_project": str(remotion_project.relative_to(root)) if remotion_project is not None else None,
        "keyframes": [str(path.relative_to(root)) for path in keyframes],
        "frames": [str(path.relative_to(root)) for path in frames],
        "plan": asdict(plan),
    }
    manifest_path = root / "ares-media.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return MediaArtifactResult(
        root=root,
        plan=plan,
        backend_name=backend_status.spec.name,
        remotion_project=remotion_project,
        keyframes=keyframes,
        frames=frames,
        video_path=video_path,
        mp4_path=mp4_path,
        storyboard_image=storyboard_image,
        storyboard_markdown=storyboard_markdown,
        manifest_path=manifest_path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create local image/video media artifacts with Ares.")
    parser.add_argument("brief", nargs="*", help="Image, storyboard, or video brief.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--kind", choices=["auto", "gif", "video", "image"], default="auto")
    parser.add_argument("--shots", type=int, default=4)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=540)
    parser.add_argument("--frames-per-shot", type=int, default=12)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--backend", default="auto", help="Media backend name or auto.")
    parser.add_argument("--no-remotion", action="store_true", help="Skip Remotion project export.")
    parser.add_argument("--no-mp4", action="store_true", help="Skip FFmpeg MP4 export.")
    parser.add_argument("--list-backends", action="store_true", help="Print available backend status and exit.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list_backends:
        print(format_backend_statuses())
        return
    if not args.brief:
        raise SystemExit("Provide a media brief, or use --list-backends.")
    result = create_media_artifact(
        " ".join(args.brief),
        repo=args.repo,
        kind=args.kind,
        shot_count=args.shots,
        width=args.width,
        height=args.height,
        frames_per_shot=args.frames_per_shot,
        fps=args.fps,
        backend=args.backend,
        remotion=not args.no_remotion,
        mp4=not args.no_mp4,
    )
    print(f"Created media artifact: {result.root}")
    print(f"Backend: {result.backend_name}")
    print(f"Video: {result.video_path}")
    if result.mp4_path is not None:
        print(f"MP4: {result.mp4_path}")
    print(f"Storyboard: {result.storyboard_markdown}")
    if result.remotion_project is not None:
        print(f"Remotion project: {result.remotion_project}")
    print(f"Keyframes: {len(result.keyframes)}")


if __name__ == "__main__":
    main()
