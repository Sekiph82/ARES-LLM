from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from local_llm.repo_context import DEFAULT_EXCLUDES, DEFAULT_SUFFIXES, should_exclude


@dataclass(frozen=True)
class PythonSymbol:
    kind: str
    name: str
    line: int


@dataclass(frozen=True)
class IndexedFile:
    path: Path
    size: int
    symbols: list[PythonSymbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RepoIndex:
    files: list[IndexedFile]
    git_status: str
    git_diff_stat: str


def build_repo_index(root: Path, suffixes: set[str] | None = None, max_files: int = 500) -> RepoIndex:
    suffixes = suffixes or (DEFAULT_SUFFIXES | {".css", ".html", ".js"})
    indexed: list[IndexedFile] = []
    for path in sorted(root.rglob("*")):
        if len(indexed) >= max_files:
            break
        if not path.is_file() or should_exclude(path, root):
            continue
        if path.suffix.lower() not in suffixes:
            continue
        rel_path = path.relative_to(root)
        symbols: list[PythonSymbol] = []
        imports: list[str] = []
        if path.suffix.lower() == ".py":
            symbols, imports = extract_python_symbols(path)
        indexed.append(IndexedFile(path=rel_path, size=path.stat().st_size, symbols=symbols, imports=imports))
    return RepoIndex(files=indexed, git_status=git_status(root), git_diff_stat=git_diff_stat(root))


def extract_python_symbols(path: Path) -> tuple[list[PythonSymbol], list[str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return [], []

    symbols: list[PythonSymbol] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(PythonSymbol("class", node.name, node.lineno))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(PythonSymbol("function", node.name, node.lineno))
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append("." * node.level + module)
    symbols.sort(key=lambda item: (item.line, item.kind, item.name))
    return symbols, sorted(set(imports))


def git_status(root: Path) -> str:
    return run_git(root, ["git", "status", "--short"]) or "Working tree clean."


def git_diff_stat(root: Path) -> str:
    return run_git(root, ["git", "diff", "--stat"]) or "No unstaged diff."


def run_git(root: Path, command: list[str]) -> str:
    try:
        process = subprocess.run(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"Git command failed: {exc}"
    return process.stdout.strip()


def format_repo_index(index: RepoIndex, max_symbols_per_file: int = 12) -> str:
    lines: list[str] = []
    for file in index.files:
        lines.append(f"{file.path.as_posix()} ({file.size} bytes)")
        if file.symbols:
            symbols = ", ".join(
                f"{symbol.kind} {symbol.name}:{symbol.line}" for symbol in file.symbols[:max_symbols_per_file]
            )
            lines.append(f"  symbols: {symbols}")
        if file.imports:
            lines.append(f"  imports: {', '.join(file.imports[:10])}")
    return "\n".join(lines)
