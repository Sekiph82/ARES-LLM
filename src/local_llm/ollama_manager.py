from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from local_llm.app_config import load_config
from local_llm.ollama_client import OllamaClient


@dataclass(frozen=True)
class OllamaModelStatus:
    model: str
    installed: bool
    installed_models: tuple[str, ...]
    message: str


def installed_models(client: OllamaClient) -> list[str]:
    return sorted(client.list_models())


def model_matches(requested: str, installed: str) -> bool:
    return requested == installed or (":" not in requested and installed == f"{requested}:latest")


def model_status(model: str, client: OllamaClient) -> OllamaModelStatus:
    models = installed_models(client)
    installed = any(model_matches(model, candidate) for candidate in models)
    return OllamaModelStatus(
        model=model,
        installed=installed,
        installed_models=tuple(models),
        message=f"{model} is installed." if installed else f"{model} is not installed.",
    )


def test_model(model: str, client: OllamaClient) -> str:
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": "Reply with one short sentence."},
            {"role": "user", "content": "Say that Ares is ready."},
        ],
        temperature=0.0,
        num_ctx=512,
    )
    return response.strip()


def create_ares_coder(repo: Path, model_name: str = "ares-coder", modelfile: Path | None = None) -> subprocess.CompletedProcess[str]:
    modelfile = modelfile or repo / "ollama" / "Modelfile"
    return subprocess.run(
        ["ollama", "create", model_name, "-f", str(modelfile)],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def pull_model(model: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["ollama", "pull", model],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def format_model_status(status: OllamaModelStatus) -> str:
    lines = [status.message]
    if status.installed_models:
        lines.append("Installed models:")
        lines.extend(f"- {model}" for model in status.installed_models)
    else:
        lines.append("No installed models reported by Ollama.")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage Ares Ollama models.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=None)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--create-ares-coder", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.repo)
    model = args.model or config.default_model
    client = OllamaClient(base_url=config.ollama_base_url, timeout=60)
    if args.list:
        print("\n".join(installed_models(client)))
    if args.status:
        print(format_model_status(model_status(model, client)))
    if args.test:
        print(test_model(model, client))
    if args.create_ares_coder:
        completed = create_ares_coder(args.repo, model_name=config.default_model)
        print(completed.stdout.strip())
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
