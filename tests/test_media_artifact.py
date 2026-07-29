from __future__ import annotations

import json

from PIL import Image

from local_llm.ares_app import should_create_media_artifact
from local_llm.media_backends import backend_names, choose_backend, media_backend_status
from local_llm.media_artifact import create_media_artifact, plan_media


def test_plan_media_creates_shots() -> None:
    plan = plan_media("Create a cinematic Ares coding launch video", shot_count=3)

    assert "Ares" in plan.title
    assert plan.style == "technical coding montage"
    assert len(plan.shots) == 3
    assert plan.shots[0].index == 1
    assert plan.shots[0].palette


def test_create_media_artifact_writes_video_storyboard_and_manifest(tmp_path) -> None:
    result = create_media_artifact(
        "Generate a local product video for Ares",
        repo=tmp_path,
        shot_count=2,
        width=320,
        height=180,
        frames_per_shot=2,
        fps=4,
    )

    assert result.video_path.exists()
    assert result.storyboard_image.exists()
    assert result.storyboard_markdown.exists()
    assert result.manifest_path.exists()
    assert len(result.keyframes) == 2
    assert len(result.frames) == 4

    with Image.open(result.video_path) as image:
        assert image.size == (320, 180)
        assert getattr(image, "is_animated", False)

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["kind"] == "local-media"
    assert manifest["format"] == "animated-gif"
    assert manifest["backend"]["selected"] == "procedural"
    assert manifest["prompt_package"]["enhanced_prompt"]
    assert manifest["shot_count"] == 2
    assert manifest["size"] == {"width": 320, "height": 180}


def test_media_requests_route_to_media_artifacts() -> None:
    assert should_create_media_artifact("Create a cinematic video for my Shopify product")
    assert should_create_media_artifact("generate images for a website launch")
    assert not should_create_media_artifact("Explain how tokenization works")


def test_media_backend_registry_has_requested_projects() -> None:
    names = set(backend_names())

    assert {"vimax", "hunyuanvideo", "cogvideo", "toonflow", "open-generative-ai", "procedural"} <= names
    assert media_backend_status("procedural").configured
    assert choose_backend("auto", "Create a realistic cinematic film").spec.name == "procedural"
