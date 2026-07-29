from __future__ import annotations

import json

from PIL import Image

from local_llm.ares_app import should_create_short_video
from local_llm.short_video import ShortVideoConfig, choose_aspect, create_short_video, plan_short_video


def test_plan_short_video_has_script_scenes_and_cta() -> None:
    plan = plan_short_video("create a YouTube short about Ares coding agent", ShortVideoConfig(scene_count=4))

    assert plan.title == "Coding Agent"
    assert plan.hook
    assert plan.call_to_action
    assert len(plan.scenes) == 4
    assert "1." in plan.script


def test_choose_aspect_uses_vertical_for_shorts() -> None:
    aspect = choose_aspect("Create a TikTok short about Ares")

    assert aspect.name == "portrait"
    assert aspect.height > aspect.width


def test_create_short_video_writes_full_pipeline(tmp_path) -> None:
    result = create_short_video(
        "create a 6 seconds short video about Ares coding agent",
        repo=tmp_path,
        config=ShortVideoConfig(
            aspect="landscape",
            duration_sec=6,
            fps=4,
            scene_count=3,
            voiceover=False,
            background_music=True,
            mp4=False,
        ),
    )

    assert result.root.exists()
    assert (result.root / "script.md").exists()
    assert result.subtitles_path.exists()
    assert result.asset_plan_path.exists()
    assert result.config_path.exists()
    assert result.music_path is not None and result.music_path.exists()
    assert result.web_ui_path.exists()
    assert result.manifest_path.exists()
    assert len(result.assets) == 3
    with Image.open(result.assets[0]) as image:
        assert image.size == (1280, 720)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["kind"] == "short-video"
    assert manifest["pipeline"] == [
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
    ]
    assert manifest["video"] is None
    assert manifest["asset_plan"] == "asset_plan.json"
    assert manifest["video_config"] == "ares-short-video.config.json"


def test_short_video_routing_prefers_video_not_image() -> None:
    assert should_create_short_video("create a 15 seconds video for a ninja and dragon fight")
    assert should_create_short_video("make a TikTok short about my product")
    assert not should_create_short_video("make this answer short")
    assert not should_create_short_video("generate images for a website")
