from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from local_llm.agent_core import DEFAULT_MODEL


@dataclass(frozen=True)
class ShortVideoDefaults:
    aspect: str = "auto"
    fps: int = 24
    scene_count: int = 5
    voiceover: bool = True
    background_music: bool = True


@dataclass(frozen=True)
class AresConfig:
    ollama_base_url: str = "http://127.0.0.1:11434"
    default_model: str = DEFAULT_MODEL
    recommended_model: str = "qwen2.5-coder:3b"
    test_command: list[str] | None = None
    short_video: ShortVideoDefaults = ShortVideoDefaults()


def config_dir(repo: Path) -> Path:
    return repo / "config"


def example_config_path(repo: Path) -> Path:
    return config_dir(repo) / "ares.example.json"


def local_config_path(repo: Path) -> Path:
    return config_dir(repo) / "ares.local.json"


def default_config() -> AresConfig:
    return AresConfig(test_command=["python", "-m", "pytest", "-q"])


def load_config(repo: Path) -> AresConfig:
    payload = asdict(default_config())
    for path in (example_config_path(repo), local_config_path(repo)):
        if path.exists():
            payload = _deep_merge(payload, json.loads(path.read_text(encoding="utf-8")))
    payload = _apply_env_overrides(payload)
    return _config_from_payload(payload)


def write_example_config(repo: Path) -> Path:
    path = example_config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(asdict(default_config()), indent=2) + "\n", encoding="utf-8")
    return path


def save_local_config(repo: Path, config: AresConfig) -> Path:
    path = local_config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2) + "\n", encoding="utf-8")
    return path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_env_overrides(payload: dict[str, Any]) -> dict[str, Any]:
    env_map = {
        "ARES_OLLAMA_BASE_URL": "ollama_base_url",
        "ARES_MODEL": "default_model",
        "ARES_RECOMMENDED_MODEL": "recommended_model",
    }
    updated = dict(payload)
    for env_name, key in env_map.items():
        value = os.environ.get(env_name)
        if value:
            updated[key] = value
    return updated


def _config_from_payload(payload: dict[str, Any]) -> AresConfig:
    allowed = {field.name for field in fields(AresConfig)}
    clean = {key: value for key, value in payload.items() if key in allowed}
    short_video_payload = clean.get("short_video")
    if isinstance(short_video_payload, dict):
        allowed_short = {field.name for field in fields(ShortVideoDefaults)}
        clean["short_video"] = ShortVideoDefaults(
            **{key: value for key, value in short_video_payload.items() if key in allowed_short}
        )
    elif not isinstance(short_video_payload, ShortVideoDefaults):
        clean["short_video"] = ShortVideoDefaults()
    if clean.get("test_command") is None:
        clean["test_command"] = ["python", "-m", "pytest", "-q"]
    return AresConfig(**clean)
