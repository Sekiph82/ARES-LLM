from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class AgentSession:
    id: str
    created_at: str
    model: str
    mode: str
    task: str
    prompt_chars: int
    response_chars: int
    included_files: int
    total_files: int
    estimated_prompt_tokens: int
    estimated_response_tokens: int
    response_preview: str


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def append_agent_session(
    repo: Path,
    model: str,
    mode: str,
    task: str,
    prompt: str,
    response: str,
    included_files: int,
    total_files: int,
) -> AgentSession:
    session = AgentSession(
        id=str(uuid4()),
        created_at=datetime.now().isoformat(timespec="seconds"),
        model=model,
        mode=mode,
        task=task,
        prompt_chars=len(prompt),
        response_chars=len(response),
        included_files=included_files,
        total_files=total_files,
        estimated_prompt_tokens=estimate_tokens(prompt),
        estimated_response_tokens=estimate_tokens(response),
        response_preview=response[:2000],
    )
    out_path = repo / "runs" / "agent" / "sessions.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(session), ensure_ascii=False) + "\n")
    return session


def load_agent_sessions(repo: Path, limit: int = 50) -> list[dict[str, object]]:
    path = repo / "runs" / "agent" / "sessions.jsonl"
    if not path.exists():
        return []

    sessions: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            sessions.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return sessions[-limit:]
