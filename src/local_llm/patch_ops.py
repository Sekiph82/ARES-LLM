from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PATCH_PATH_RE = re.compile(r"^(?:---|\+\+\+) [ab]/(.+)$", re.MULTILINE)
DIFF_GIT_PATH_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class PatchApplyResult:
    ok: bool
    message: str
    backup_dir: Path | None = None
    changed_paths: tuple[Path, ...] = ()


def patch_paths(patch_text: str) -> list[Path]:
    paths: set[str] = set()
    for left, right in DIFF_GIT_PATH_RE.findall(patch_text):
        for raw in (left, right):
            if raw != "/dev/null":
                paths.add(raw.strip())
    for raw in PATCH_PATH_RE.findall(patch_text):
        if raw != "/dev/null":
            paths.add(raw.strip())
    return sorted((Path(path) for path in paths), key=lambda path: path.as_posix())


def is_safe_relative_path(path: Path) -> bool:
    return not path.is_absolute() and ".." not in path.parts


def assess_patch_safety(repo: Path, patch_text: str, max_files: int = 20, max_existing_bytes: int = 1_000_000) -> PatchApplyResult:
    paths = patch_paths(patch_text)
    if not paths:
        return PatchApplyResult(ok=False, message="No file paths found in patch.")
    if len(paths) > max_files:
        return PatchApplyResult(ok=False, message=f"Patch touches too many files: {len(paths)} > {max_files}.")
    for path in paths:
        if not is_safe_relative_path(path):
            return PatchApplyResult(ok=False, message=f"Unsafe patch path: {path}", changed_paths=tuple(paths))
        parts = set(path.parts)
        if parts & {".git", ".venv", "runs", "dist", "build", "__pycache__"}:
            return PatchApplyResult(ok=False, message=f"Patch touches generated or internal path: {path}", changed_paths=tuple(paths))
        if path.name.lower() in {".env", ".env.local"}:
            return PatchApplyResult(ok=False, message=f"Patch touches a secret-bearing file: {path}", changed_paths=tuple(paths))
        existing = repo / path
        if existing.exists() and existing.is_file() and existing.stat().st_size > max_existing_bytes:
            return PatchApplyResult(ok=False, message=f"Patch target is too large for safe apply: {path}", changed_paths=tuple(paths))
    return PatchApplyResult(ok=True, message="Patch safety assessment passed.", changed_paths=tuple(paths))


def backup_patch_targets(repo: Path, paths: list[Path], label: str = "patch") -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = repo / "runs" / "backups" / f"{label}-{timestamp}"
    for rel_path in paths:
        if not is_safe_relative_path(rel_path):
            raise ValueError(f"Unsafe patch path: {rel_path}")
        source = repo / rel_path
        if not source.exists():
            continue
        target = backup_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def check_patch(repo: Path, patch_text: str) -> PatchApplyResult:
    if not patch_text.strip():
        return PatchApplyResult(ok=False, message="No patch text to apply.")
    safety = assess_patch_safety(repo, patch_text)
    if not safety.ok:
        return safety

    process = subprocess.run(
        ["git", "apply", "--check", "-"],
        input=patch_text,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return PatchApplyResult(
        ok=process.returncode == 0,
        message=process.stdout.strip() or "Patch check passed.",
        changed_paths=safety.changed_paths,
    )


def apply_patch_with_backup(repo: Path, patch_text: str, label: str = "patch") -> PatchApplyResult:
    check = check_patch(repo, patch_text)
    if not check.ok:
        return check

    paths = patch_paths(patch_text)
    backup_dir = backup_patch_targets(repo, paths, label=label)
    process = subprocess.run(
        ["git", "apply", "-"],
        input=patch_text,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if process.returncode != 0:
        return PatchApplyResult(
            ok=False,
            message=process.stdout.strip() or "Patch apply failed.",
            backup_dir=backup_dir,
            changed_paths=tuple(paths),
        )
    changed = ", ".join(path.as_posix() for path in paths) or "working tree"
    return PatchApplyResult(ok=True, message=f"Applied patch to {changed}.", backup_dir=backup_dir, changed_paths=tuple(paths))
