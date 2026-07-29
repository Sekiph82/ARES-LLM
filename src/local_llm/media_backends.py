from __future__ import annotations

import os
import shutil
import importlib.util
from dataclasses import asdict, dataclass
from pathlib import Path

from local_llm.video_encode import resolve_ffmpeg


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
    "ffmpeg": MediaBackendSpec(
        name="ffmpeg",
        display_name="FFmpeg Encoder",
        repo_url="https://github.com/FFmpeg/FFmpeg",
        modes=("mp4-export", "gif-conversion", "audio-video-muxing", "media-inspection"),
        strengths=("industry standard media tooling", "local MP4 output", "audio/video composition"),
        min_vram_gb=None,
        local_setup="Install FFmpeg on PATH or set ARES_FFMPEG_PATH to ffmpeg.exe.",
        bridge_kind="command",
        env_var="ARES_FFMPEG_PATH",
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
    "moneyprinterturbo": MediaBackendSpec(
        name="moneyprinterturbo",
        display_name="MoneyPrinterTurbo",
        repo_url="https://github.com/harry0703/MoneyPrinterTurbo",
        modes=("topic-to-short-video", "script-assets-voice", "social-video-workflow"),
        strengths=("one-topic short video workflow", "automated asset pipeline", "creator-oriented packaging"),
        min_vram_gb=None,
        local_setup="Set ARES_MONEYPRINTER_DIR to a local MoneyPrinterTurbo checkout.",
        bridge_kind="command",
        env_var="ARES_MONEYPRINTER_DIR",
    ),
    "imaginairy": MediaBackendSpec(
        name="imaginairy",
        display_name="imaginAIry",
        repo_url="https://github.com/brycedrennan/imaginAIry",
        modes=("text-to-image", "image-to-video", "image-editing", "upscaling"),
        strengths=("Pythonic image generation", "Stable Diffusion workflows", "Stable Video Diffusion CLI"),
        min_vram_gb=8,
        local_setup="Install imaginairy/aimg in a separate environment, or set ARES_IMAGINAIRY_CMD.",
        bridge_kind="command",
        env_var="ARES_IMAGINAIRY_CMD",
    ),
    "infinitetalk": MediaBackendSpec(
        name="infinitetalk",
        display_name="InfiniteTalk",
        repo_url="https://github.com/MeiGen-AI/InfiniteTalk",
        modes=("audio-driven-video", "talking-avatar", "video-dubbing", "image-audio-to-video"),
        strengths=("long talking videos", "lip sync", "identity-preserving dubbing"),
        min_vram_gb=None,
        local_setup="Set ARES_INFINITETALK_DIR to a local InfiniteTalk checkout with its model environment installed.",
        bridge_kind="command",
        env_var="ARES_INFINITETALK_DIR",
    ),
    "timm": MediaBackendSpec(
        name="timm",
        display_name="PyTorch Image Models",
        repo_url="https://github.com/huggingface/pytorch-image-models",
        modes=("image-classification", "embedding-backbones", "visual-qa-scoring"),
        strengths=("large model zoo", "pretrained vision backbones", "image quality/classification checks"),
        min_vram_gb=None,
        local_setup="Install timm in the Python environment when Ares needs pretrained visual scoring.",
        bridge_kind="python-package",
    ),
    "image-processing-learning": MediaBackendSpec(
        name="image-processing-learning",
        display_name="Deep Learning For Image Processing",
        repo_url="https://github.com/WZMIAOMIAO/deep-learning-for-image-processing",
        modes=("classification-learning", "detection-learning", "segmentation-learning", "keypoint-learning"),
        strengths=("computer vision learning roadmap", "classification/detection/segmentation references"),
        min_vram_gb=None,
        local_setup="Reference backend only. Ares uses these ideas for future image QA and model training notes.",
        bridge_kind="reference",
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
    if spec.name == "ffmpeg":
        ffmpeg = resolve_ffmpeg()
        return MediaBackendStatus(
            spec,
            ffmpeg.available,
            ffmpeg.reason,
            "Ares will create video.mp4 from generated frames." if ffmpeg.available else spec.local_setup,
        )
    if spec.name == "remotion":
        return MediaBackendStatus(
            spec,
            True,
            "Ares can export Remotion-ready project files.",
            "Run npm install and npm run preview inside the generated remotion folder.",
        )
    if spec.name == "imaginairy":
        override = os.environ.get("ARES_IMAGINAIRY_CMD", "").strip()
        if override:
            command_path = Path(override).expanduser()
            if command_path.exists():
                return MediaBackendStatus(spec, True, f"ARES_IMAGINAIRY_CMD points to {command_path}.", build_launch_hint(spec, command_path))
            if shutil.which(override):
                return MediaBackendStatus(spec, True, f"ARES_IMAGINAIRY_CMD resolves to {override}.", build_launch_hint(spec, override))
            return MediaBackendStatus(spec, False, f"ARES_IMAGINAIRY_CMD is set but was not found: {override}", spec.local_setup)
        found = shutil.which("aimg") or shutil.which("imagine")
        if found:
            return MediaBackendStatus(spec, True, f"imaginAIry command was found at {found}.", build_launch_hint(spec, found))
        return MediaBackendStatus(spec, False, "aimg/imagine was not found on PATH.", spec.local_setup)
    if spec.name == "timm":
        found = importlib.util.find_spec("timm") is not None
        return MediaBackendStatus(
            spec,
            found,
            "Python package timm is installed." if found else "Python package timm is not installed.",
            "Use timm models for future visual QA scoring." if found else spec.local_setup,
        )
    if spec.name == "image-processing-learning":
        return MediaBackendStatus(spec, True, "Reference backend is available through documented Ares research notes.", spec.local_setup)
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
    if any(word in text for word in ("talking", "avatar", "lip sync", "dub", "dubbing", "audio driven")):
        priority = ["infinitetalk", "remotion", "procedural"]
    elif any(word in text for word in ("short video", "viral", "youtube shorts", "tiktok", "reels")):
        priority = ["moneyprinterturbo", "remotion", "ffmpeg", "procedural"]
    elif any(word in text for word in ("stable diffusion", "sdxl", "upscale", "image edit")):
        priority = ["imaginairy", "open-generative-ai", "procedural"]
    elif "remotion" in text or "react video" in text or "programmatic video" in text:
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
    if spec.name == "ffmpeg":
        return "Ares will call FFmpeg to encode generated PNG frames into video.mp4."
    if spec.name == "moneyprinterturbo":
        return f"Use {target} as the short-video automation workspace and hand it Ares' topic/script package."
    if spec.name == "imaginairy":
        return f"Use {target} to generate source images or image-to-video clips from Ares' enhanced prompt."
    if spec.name == "infinitetalk":
        return f"From {target}, run InfiniteTalk with Ares' avatar/audio/video handoff package."
    if spec.name == "timm":
        return "Use timm backbones for future visual classification and artifact QA scoring."
    if spec.name == "image-processing-learning":
        return "Use the repo as a learning/reference map for classification, detection, segmentation, and keypoint tasks."
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
    elif backend.name == "ffmpeg":
        prompt = f"Create a clean video assembly plan with frame timing, captions, audio slots, and MP4 export settings: {brief}"
    elif backend.name == "moneyprinterturbo":
        prompt = f"Create a short-video production package: hook, script, scene list, captions, voiceover notes, keywords, and aspect ratio for: {brief}"
    elif backend.name == "imaginairy":
        prompt = f"{brief}. Generate Stable Diffusion-ready prompts, negative prompts, seed guidance, size, style, and optional image-to-video instructions."
    elif backend.name == "infinitetalk":
        prompt = f"Create an audio-driven talking-video package with avatar description, voice/audio requirements, expressions, and dubbing notes for: {brief}"
    elif backend.name == "timm":
        prompt = f"Create a visual QA checklist and candidate image classification labels for: {brief}"
    elif backend.name == "image-processing-learning":
        prompt = f"Map this task to computer vision learning areas: classification, detection, segmentation, keypoints, and evaluation for: {brief}"
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
