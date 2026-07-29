from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


MEMORY_HEADER = """# Ares Memory

This local file is Ares' practical self-learning layer. It stores durable
lessons, project preferences, successful workflows, and shop-management notes.
It is not a replacement for model training; it is retrieved and included in
future prompts so Ares can adapt without unsafe unattended retraining.
"""


@dataclass(frozen=True)
class MemoryEntry:
    created_at: str
    title: str
    body: str


def memory_path(repo: Path) -> Path:
    return repo / "data" / "ares_memory.md"


def ensure_memory(repo: Path) -> Path:
    path = memory_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(MEMORY_HEADER + "\n", encoding="utf-8")
    return path


def load_memory(repo: Path, max_chars: int = 6000) -> str:
    path = ensure_memory(repo)
    text = path.read_text(encoding="utf-8")
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def append_memory(repo: Path, title: str, body: str) -> MemoryEntry:
    entry = MemoryEntry(
        created_at=datetime.now().isoformat(timespec="seconds"),
        title=title.strip() or "Lesson",
        body=body.strip(),
    )
    path = ensure_memory(repo)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n## {entry.created_at} - {entry.title}\n\n{entry.body}\n")
    return entry


def summarize_memory_source(source: str, text: str, max_chars: int = 1400) -> str:
    clean = " ".join(text.split())
    if len(clean) > max_chars:
        clean = clean[:max_chars].rstrip() + "..."
    return f"Source: {source}\n\n{clean}"
