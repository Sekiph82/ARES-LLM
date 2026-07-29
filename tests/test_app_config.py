import json

from local_llm.app_config import load_config, save_local_config


def test_load_config_uses_example_and_local_override(tmp_path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "ares.example.json").write_text(
        json.dumps({"default_model": "ares-coder", "short_video": {"fps": 12}}),
        encoding="utf-8",
    )
    (config_dir / "ares.local.json").write_text(
        json.dumps({"default_model": "custom-coder", "short_video": {"scene_count": 7}}),
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.default_model == "custom-coder"
    assert config.short_video.fps == 12
    assert config.short_video.scene_count == 7


def test_save_local_config_writes_ignored_config_shape(tmp_path) -> None:
    path = save_local_config(tmp_path, load_config(tmp_path))

    assert path.as_posix().endswith("config/ares.local.json")
    assert "default_model" in path.read_text(encoding="utf-8")
