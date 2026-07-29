from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXCLUDES = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "runs",
    "checkpoints",
    "node_modules",
    "dist",
    "build",
}

DEFAULT_SUFFIXES = {
    ".py",
    ".md",
    ".toml",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
}


@dataclass(frozen=True)
class RepoFile:
    path: Path
    text: str
    score: int = 0


@dataclass(frozen=True)
class RepoContext:
    tree: str
    files: list[RepoFile]
    total_files: int
    included_chars: int


def collect_repo_files(
    root: Path,
    task: str = "",
    max_files: int = 40,
    max_chars_per_file: int = 6000,
    max_total_chars: int = 60000,
    suffixes: set[str] | None = None,
) -> list[RepoFile]:
    return build_repo_context(
        root,
        task=task,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
        suffixes=suffixes,
    ).files


def build_repo_context(
    root: Path,
    task: str = "",
    max_files: int = 40,
    max_chars_per_file: int = 6000,
    max_total_chars: int = 60000,
    suffixes: set[str] | None = None,
) -> RepoContext:
    suffixes = suffixes or DEFAULT_SUFFIXES
    candidates: list[RepoFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or should_exclude(path, root):
            continue
        if path.suffix.lower() not in suffixes:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        if len(text) > max_chars_per_file:
            text = text[:max_chars_per_file] + "\n...[truncated]\n"
        rel_path = path.relative_to(root)
        candidates.append(RepoFile(path=rel_path, text=text, score=score_file(rel_path, text, task)))

    selected: list[RepoFile] = []
    included_chars = 0
    for file in sorted(candidates, key=lambda item: (-item.score, item.path.as_posix())):
        if len(selected) >= max_files:
            break
        if included_chars + len(file.text) > max_total_chars and selected:
            continue
        selected.append(file)
        included_chars += len(file.text)

    return RepoContext(
        tree=format_tree(candidates),
        files=selected,
        total_files=len(candidates),
        included_chars=included_chars,
    )


def should_exclude(path: Path, root: Path) -> bool:
    relative_parts = path.relative_to(root).parts
    return any(part in DEFAULT_EXCLUDES for part in relative_parts)


def score_file(path: Path, text: str, task: str) -> int:
    path_text = path.as_posix().lower()
    score = 0
    if path.name.lower() in {"readme.md", "pyproject.toml", "requirements.txt", "modelfile"}:
        score += 50
    if path.parts and path.parts[0] in {"src", "tests", "scripts", "ollama"}:
        score += 20
    if path.suffix.lower() == ".py":
        score += 10

    terms = task_terms(task)
    if terms:
        text_sample = text[:2000].lower()
        score += sum(20 for term in terms if term in path_text)
        score += sum(5 for term in terms if term in text_sample)
    return score


def task_terms(task: str) -> set[str]:
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", task.lower())
    ignored = {"the", "and", "for", "with", "this", "that", "from", "into", "ares"}
    counts = Counter(word for word in words if word not in ignored)
    return {word for word, _ in counts.most_common(12)}


def format_tree(files: list[RepoFile], max_entries: int = 120) -> str:
    paths = [file.path.as_posix() for file in sorted(files, key=lambda item: item.path.as_posix())]
    shown = paths[:max_entries]
    extra = len(paths) - len(shown)
    lines = shown
    if extra > 0:
        lines.append(f"... {extra} more files")
    return "\n".join(lines)


def format_repo_context(context: RepoContext | list[RepoFile]) -> str:
    if isinstance(context, RepoContext):
        files = context.files
        chunks = [
            "## Repository Map",
            context.tree,
            "",
            f"## Included Files ({len(files)} of {context.total_files}, {context.included_chars} chars)",
        ]
    else:
        files = context
        chunks = []

    for file in files:
        score_note = f" score={file.score}" if file.score else ""
        chunks.append(f"### {file.path.as_posix()}{score_note}\n```text\n{file.text}\n```")
    return "\n\n".join(chunks)
