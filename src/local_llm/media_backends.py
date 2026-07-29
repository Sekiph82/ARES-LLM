from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaBackendSpec:
    name: str
    display_name: str
    repo_url: str
    modes: tuple[str, ...]
    strengths: tuple[str, ...]
    min_vram_gb: int | None
    local_setup: str
    bridge_kind: str
    env_var: str | None = None


@dataclass(frozen=True)
class MediaBackendStatus:
    spec: MediaBackendSpec
    configured: bool
    reason: str
    launch_hint: str


BACKENDS: dict[str, MediaBackendSpec] = {
    "procedural": MediaBackendSpec(
        name="procedural",
        display_name="Ares Procedural Renderer",
        repo_url="local",
        modes=("text-to-storyboard", "text-to-gif", "keyframes", "remotion-export"),
        strengths=("always available", "fast laptop previews", "consistent Ares branding", "React video handoff"),
        min_vram_gb=None,
        local_setup="No setup required. Uses Pillow inside Ares.",
        bridge_kind="internal",
    ),
    "remotion": MediaBackendSpec(
        name="remotion",
        display_name="Remotion React Video",
        repo_url="https://github.com/remotion-dev/remotion",
        modes=("react-video", "programmatic-rendering", "mp4-export", "video-apps"),
        strengths=("React code as source of truth", "editable animations", "data-driven video rendering"),
        min_vram_gb=None,
        local_setup="Install Node.js, then run npm install inside an Ares remotion artifact folder.",
        bridge_kind="project",
    ),
    "vimax": MediaBackendSpec(
        name="vimax",
        display_name="ViMax Agentic Video Pipeline",
        repo_url="https://github.com/HKUDS/ViMax",
        modes=("idea-to-video", "script-to-video", "novel-to-video", "storyboard-review"),
        strengths=("agent planning", "script and storyboard workflow", "render checkpoints"),
        min_vram_gb=None,
        local_setup="Set ARES_VIMAX_DIR to a local ViMax checkout with its own environment configured.",
        bridge_kind="command",
        env_var="ARES_VIMAX_DIR",
    ),
    "hunyuanvideo": MediaBackendSpec(
        name="hunyuanvideo",
        display_name="HunyuanVideo",
        repo_url="https://github.com/Tencent-Hunyuan/HunyuanVideo",
        modes=("text-to-video", "image-to-video", "video foundation model"),
        strengths=("high motion quality", "large open video model", "prompt rewrite workflow"),
        min_vram_gb=45,
        local_setup="Set ARES_HUNYUANVIDEO_DIR to a local HunyuanVideo checkout with CUDA models installed.",
        bridge_kind="command",
        env_var="ARES_HUNYUANVIDEO_DIR",
    ),
    "cogvideo": MediaBackendSpec(
        name="cogvideo",
        display_name="CogVideoX",
        repo_url="https://github.com/zai-org/CogVideo",
        modes=("text-to-video", "image-to-video", "diffusers"),
        strengths=("Diffusers integration", "prompt optimization", "smaller public video models"),
        min_vram_gb=8,
        local_setup="Set ARES_COGVIDEO_DIR to a local CogVideo checkout with its model environment installed.",
        bridge_kind="command",
        env_var="ARES_COGVIDEO_DIR",
    ),
    "toonflow": MediaBackendSpec(
        name="toonflow",
        display_name="Toonflow",
        repo_url="https://github.com/HBAI-Ltd/Toonflow-app",
        modes=("script-to-animation", "storyboard", "character workflow"),
        strengths=("short drama workflow", "scriptwriting", "character and storyboard panels"),
        min_vram_gb=None,
        local_setup="Set ARES_TOONFLOW_URL to a running local Toonflow app URL.",
        bridge_kind="http",
        env_var="ARES_TOONFLOW_URL",
    ),
    "open-generative-ai": MediaBackendSpec(
        name="open-generative-ai",
        display_name="Open Generative AI",
        repo_url="https://github.com/Anil-matcha/Open-Generative-AI",
        modes=("image-generation", "video-generation", "model-catalog"),
        strengths=("studio UI", "many model integrations", "self-hosted deployment shape"),
        min_vram_gb=None,
        local_setup="Set ARES_OPEN_GENERATIVE_AI_URL to a running local Open Generative AI service URL.",
        bridge_kind="http",
        env_var="ARES_OPEN_GENERATIVE_AI_URL",
    ),
}


def backend_names() -> list[str]:
    return sorted(BACKENDS)


def get_backend(name: str) -> MediaBackendSpec:
    normalized = name.strip().lower()
    if normalized not in BACKENDS:
        raise ValueError(f"Unknown media backend: {name}")
    return BACKENDS[normalized]


def media_backend_status(name: str) -> MediaBackendStatus:
    spec = get_backend(name)
    if spec.name == "procedural":
        return MediaBackendStatus(spec, True, "Built into Ares.", "Ares will render the artifact directly.")
    if spec.name == "remotion":
        return MediaBackendStatus(
            spec,
            True,
            "Ares can export Remotion-ready project files.",
            "Run npm install and npm run preview inside the generated remotion folder.",
        )
    if spec.env_var is None:
        return MediaBackendStatus(spec, False, "No configuration variable is defined.", "Use the procedural backend.")

    value = os.environ.get(spec.env_var, "").strip()
    if not value:
        return MediaBackendStatus(spec, False, f"{spec.env_var} is not set.", spec.local_setup)
    if spec.bridge_kind == "command":
        path = Path(value).expanduser()
        if path.exists():
            return MediaBackendStatus(spec, True, f"{spec.env_var} points to {path}.", build_launch_hint(spec, path))
        return MediaBackendStatus(spec, False, f"{spec.env_var} points to a missing path: {path}", spec.local_setup)
    return MediaBackendStatus(spec, True, f"{spec.env_var} is configured.", build_launch_hint(spec, value))


def choose_backend(preferred: str = "auto", brief: str = "") -> MediaBackendStatus:
    requested = preferred.strip().lower()
    if requested and requested != "auto":
        status = media_backend_status(requested)
        return status if status.configured else media_backend_status("procedural")

    text = brief.lower()
    priority = ["procedural"]
    if "remotion" in text or "react video" in text or "programmatic video" in text:
        priority = ["remotion", "procedural"]
    elif any(word in text for word in ("drama", "script", "episode", "character", "toon", "animation")):
        priority = ["toonflow", "vimax", "cogvideo", "procedural"]
    elif any(word in text for word in ("realistic", "cinematic", "film", "motion", "camera")):
        priority = ["hunyuanvideo", "cogvideo", "vimax", "procedural"]
    elif any(word in text for word in ("image", "poster", "thumbnail", "product")):
        priority = ["open-generative-ai", "cogvideo", "procedural"]

    for name in priority:
        status = media_backend_status(name)
        if status.configured:
            return status
    return media_backend_status("procedural")


def build_launch_hint(spec: MediaBackendSpec, target: Path | str) -> str:
    if spec.name == "vimax":
        return f"Run ViMax from {target} and use the generated storyboard.md as the project brief."
    if spec.name == "hunyuanvideo":
        return (
            f"From {target}, run sample_video.py with the Ares enhanced prompt, "
            "--flow-reverse, --use-cpu-offload, and a save path inside the artifact folder."
        )
    if spec.name == "cogvideo":
        return f"From {target}, run the CogVideoX inference or Diffusers path with the Ares enhanced prompt."
    if spec.name == "toonflow":
        return f"Send the script/storyboard package to the running Toonflow service at {target}."
    if spec.name == "open-generative-ai":
        return f"Send the prompt package to the running Open Generative AI studio at {target}."
    if spec.name == "remotion":
        return "Run npm install and npm run preview inside the generated remotion folder."
    return "Ares will render the artifact directly."


def backend_prompt_package(brief: str, backend: MediaBackendSpec) -> dict[str, object]:
    camera_language = (
        "Use clear subject motion, stable composition, consistent identity, "
        "cinematic lighting, and concise visual details."
    )
    if backend.name == "hunyuanvideo":
        prompt = f"{brief}. {camera_language} Add camera movement, foreground/background depth, and temporal continuity."
    elif backend.name == "cogvideo":
        prompt = f"{brief}. Expand into a long descriptive video prompt with motion, scene details, and style consistency."
    elif backend.name == "toonflow":
        prompt = f"Turn this into a short animated drama scene plan with characters, shots, and dialogue: {brief}"
    elif backend.name == "open-generative-ai":
        prompt = f"{brief}. Produce image and video variants with style, aspect ratio, seed, and model notes."
    elif backend.name == "vimax":
        prompt = f"Create an idea-to-video plan with story, shots, characters, storyboard, and render checkpoints: {brief}"
    elif backend.name == "remotion":
        prompt = f"Turn this into a data-driven React video composition with animated scenes and captions: {brief}"
    else:
        prompt = f"{brief}. {camera_language}"
    return {
        "backend": asdict(backend),
        "original_brief": brief,
        "enhanced_prompt": prompt,
        "handoff_ready": backend.name != "procedural",
    }


def format_backend_statuses() -> str:
    lines = ["# Ares Media Backends", ""]
    for name in backend_names():
        status = media_backend_status(name)
        marker = "ready" if status.configured else "not configured"
        vram = "unknown" if status.spec.min_vram_gb is None else f"{status.spec.min_vram_gb}GB+"
        lines.extend(
            [
                f"## {status.spec.display_name}",
                f"Status: {marker}",
                f"Modes: {', '.join(status.spec.modes)}",
                f"Minimum VRAM: {vram}",
                f"Reason: {status.reason}",
                f"Next: {status.launch_hint}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"
