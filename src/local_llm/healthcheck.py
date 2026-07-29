from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from local_llm.app_config import load_config
from local_llm.ollama_client import OllamaClient
from local_llm.ollama_manager import model_matches
from local_llm.video_encode import resolve_ffmpeg


@dataclass(frozen=True)
class HealthItem:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class HealthReport:
    ok: bool
    items: list[HealthItem]

    def to_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "items": [asdict(item) for item in self.items]}


def run_healthcheck(repo: Path, model: str | None = None, client: OllamaClient | None = None) -> HealthReport:
    repo = repo.resolve()
    config = load_config(repo)
    selected_model = model or config.default_model
    items = [
        check_imports(),
        check_writable(repo / "artifacts", "Artifacts directory"),
        check_writable(repo / "runs", "Runs directory"),
        check_git(repo),
        check_ffmpeg(),
        check_playwright(),
        check_ollama(selected_model, client or OllamaClient(base_url=config.ollama_base_url, timeout=5)),
    ]
    ok = all(item.status in {"pass", "warn"} for item in items)
    return HealthReport(ok=ok, items=items)


def check_imports() -> HealthItem:
    missing = [name for name in ("torch", "PIL", "numpy") if importlib.util.find_spec(name) is None]
    if missing:
        return HealthItem("Python package imports", "fail", f"Missing packages: {', '.join(missing)}")
    return HealthItem("Python package imports", "pass", "Required Python packages are importable.")


def check_writable(path: Path, name: str) -> HealthItem:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".ares-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return HealthItem(name, "pass", f"Writable: {path}")
    except OSError as exc:
        return HealthItem(name, "fail", f"Not writable: {exc}")


def check_git(repo: Path) -> HealthItem:
    if not (repo / ".git").exists():
        return HealthItem("Git repository", "warn", "No .git directory found.")
    git = shutil.which("git")
    if not git:
        return HealthItem("Git repository", "fail", "git executable was not found on PATH.")
    process = subprocess.run(
        [git, "status", "--short"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        return HealthItem("Git repository", "fail", process.stdout.strip() or "git status failed.")
    summary = process.stdout.strip() or "Working tree clean."
    return HealthItem("Git repository", "pass", summary)


def check_ffmpeg() -> HealthItem:
    status = resolve_ffmpeg()
    if status.available:
        return HealthItem("FFmpeg", "pass", f"Available at {status.executable}.")
    return HealthItem("FFmpeg", "warn", status.message)


def check_playwright() -> HealthItem:
    if importlib.util.find_spec("playwright") is None:
        return HealthItem("Playwright", "warn", "Python package is not installed; visual QA will be skipped.")
    return HealthItem("Playwright", "pass", "Python package is installed.")


def check_ollama(model: str, client: OllamaClient) -> HealthItem:
    if not shutil.which("ollama"):
        return HealthItem("Ollama", "fail", "ollama executable was not found on PATH.")
    try:
        models = client.list_models()
    except RuntimeError as exc:
        return HealthItem("Ollama", "fail", str(exc))
    if any(model_matches(model, candidate) for candidate in models):
        return HealthItem("Ollama", "pass", f"Model is installed: {model}")
    if models:
        return HealthItem("Ollama", "warn", f"{model} is not installed. Installed: {', '.join(models)}")
    return HealthItem("Ollama", "warn", f"No Ollama models installed. Recommended model: {model}")


def format_health_report(report: HealthReport) -> str:
    lines = [f"Ares health: {'READY' if report.ok else 'NEEDS ATTENTION'}", ""]
    for item in report.items:
        lines.append(f"[{item.status.upper()}] {item.name}: {item.message}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether Ares local tools are ready.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=None)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_healthcheck(args.repo, model=args.model)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_health_report(report))
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
