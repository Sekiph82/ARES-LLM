from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FFmpegStatus:
    available: bool
    executable: Path | None
    reason: str


@dataclass(frozen=True)
class EncodeResult:
    ok: bool
    output: Path | None
    command: list[str]
    message: str


def resolve_ffmpeg() -> FFmpegStatus:
    override = os.environ.get("ARES_FFMPEG_PATH", "").strip()
    if override:
        path = Path(override).expanduser()
        if path.exists():
            return FFmpegStatus(True, path, f"ARES_FFMPEG_PATH points to {path}.")
        return FFmpegStatus(False, None, f"ARES_FFMPEG_PATH points to a missing file: {path}")

    found = shutil.which("ffmpeg")
    if found:
        return FFmpegStatus(True, Path(found), f"ffmpeg was found at {found}.")
    return FFmpegStatus(False, None, "ffmpeg was not found on PATH. Set ARES_FFMPEG_PATH or install FFmpeg.")


def encode_mp4_from_frames(frames_dir: Path, output: Path, fps: int, pattern: str = "shot-*-frame-*.png") -> EncodeResult:
    status = resolve_ffmpeg()
    if not status.available or status.executable is None:
        return EncodeResult(False, None, [], status.reason)

    frames = sorted(frames_dir.glob(pattern))
    if not frames:
        return EncodeResult(False, None, [], f"No frames matched {pattern} in {frames_dir}.")

    list_file = output.with_suffix(".ffconcat")
    duration = 1 / max(1, fps)
    lines = ["ffconcat version 1.0"]
    for frame in frames:
        safe_path = frame.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
        lines.append(f"duration {duration:.8f}")
    safe_last = frames[-1].resolve().as_posix().replace("'", "'\\''")
    lines.append(f"file '{safe_last}'")
    list_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    command = [
        str(status.executable),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-vf",
        "format=yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    try:
        completed = subprocess.run(command, cwd=frames_dir.parent, capture_output=True, text=True, check=False)
    except OSError as exc:
        return EncodeResult(False, None, command, f"Could not run FFmpeg: {exc}")

    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip()
        return EncodeResult(False, None, command, f"FFmpeg failed with exit code {completed.returncode}: {details}")
    return EncodeResult(True, output, command, f"Created MP4 at {output}.")
