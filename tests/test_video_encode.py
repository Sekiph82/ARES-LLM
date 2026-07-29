from __future__ import annotations

import subprocess

from PIL import Image

from local_llm import video_encode


def test_resolve_ffmpeg_reports_missing_override(monkeypatch, tmp_path) -> None:
    missing = tmp_path / "missing-ffmpeg.exe"
    monkeypatch.setenv("ARES_FFMPEG_PATH", str(missing))

    status = video_encode.resolve_ffmpeg()

    assert not status.available
    assert "missing" in status.reason.lower()


def test_encode_mp4_from_frames_builds_ffmpeg_command(monkeypatch, tmp_path) -> None:
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    for index in range(2):
        Image.new("RGB", (32, 18), "#111827").save(frames_dir / f"shot-01-frame-{index + 1:03d}.png")

    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_text("", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(command, cwd, capture_output, text, check):
        calls.append(command)
        output = tmp_path / "video.mp4"
        output.write_bytes(b"fake mp4")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setenv("ARES_FFMPEG_PATH", str(ffmpeg))
    monkeypatch.setattr(video_encode.subprocess, "run", fake_run)

    result = video_encode.encode_mp4_from_frames(frames_dir, tmp_path / "video.mp4", fps=8)

    assert result.ok
    assert result.output == tmp_path / "video.mp4"
    assert calls
    assert "-f" in calls[0]
    assert (tmp_path / "video.ffconcat").exists()
