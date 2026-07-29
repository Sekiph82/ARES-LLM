from __future__ import annotations

import json

from local_llm.media_artifact import create_media_artifact
from local_llm.remotion_artifact import create_remotion_artifact


def test_create_remotion_artifact_writes_project_files(tmp_path) -> None:
    project = create_remotion_artifact(
        "Create a ninja and dragon fight video",
        root=tmp_path,
        fps=24,
        width=1280,
        height=720,
    )

    assert (project / "package.json").exists()
    assert (project / "src" / "index.ts").exists()
    assert (project / "src" / "Root.tsx").exists()
    assert (project / "src" / "Video.tsx").exists()
    assert (project / "src" / "style.css").exists()
    assert (project / "public" / "scene-data.json").exists()

    package = json.loads((project / "package.json").read_text(encoding="utf-8"))
    scene_data = json.loads((project / "public" / "scene-data.json").read_text(encoding="utf-8"))

    assert "remotion" in package["dependencies"]
    assert package["scripts"]["preview"] == "remotion studio src/index.ts"
    assert scene_data["title"] == "Ninja Dragon Fight"
    assert len(scene_data["shots"]) == 4


def test_media_artifact_includes_remotion_project(tmp_path) -> None:
    result = create_media_artifact(
        "create a 15 seconds video for a ninja and dragon fight scene",
        repo=tmp_path,
        shot_count=2,
        width=320,
        height=180,
        frames_per_shot=2,
        fps=4,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.remotion_project is not None
    assert result.remotion_project.exists()
    assert manifest["remotion_project"] == "remotion"
    assert (result.remotion_project / "src" / "Video.tsx").exists()
