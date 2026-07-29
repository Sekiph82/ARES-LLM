from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from local_llm.design_system import load_design_system
from local_llm.memory import load_memory
from local_llm.ollama_client import OllamaClient
from local_llm.repo_context import build_repo_context, format_repo_context
from local_llm.session_log import AgentSession, append_agent_session


DEFAULT_MODEL = "ares-coder"

MODE_INSTRUCTIONS = {
    "answer": "Answer the user's exact question first. Be concise, specific, and avoid generic repository summaries.",
    "plan": "Create a short implementation plan with risks, files likely touched, and verification steps.",
    "patch": "Propose a small unified diff. Include only changes you can justify from the context.",
    "review": "Review the repository context for bugs, risks, and missing tests. Findings first.",
    "reason": "Think through the task step by step privately, then present a clear final answer and verification plan.",
    "design": "Design and implement dynamic websites or apps. Use the design contract, include concrete files, states, interactions, and verification steps.",
}

SYSTEM_PROMPT = """You are Ares, a careful local coding agent for this user's projects.
You are local-first, practical, and honest about uncertainty.
Inspect repository context before suggesting changes.
Prefer small changes, explicit files, and testable verification steps.
When code changes are requested, use unified diff blocks.
For website and app work, follow the repository DESIGN.md contract and produce real, runnable UI files.
Keep the user's task more important than the surrounding repository context.
Do not claim you executed commands or edited files unless tool output confirms it."""


@dataclass(frozen=True)
class AgentResult:
    response: str
    prompt: str
    mode: str
    model: str
    included_files: int
    total_files: int
    session: AgentSession


def ask_agent(
    task: str,
    repo: Path,
    model: str = DEFAULT_MODEL,
    mode: str = "answer",
    max_files: int = 30,
    max_chars_per_file: int = 4000,
    max_total_chars: int = 24000,
    temperature: float = 0.2,
    num_ctx: int = 8192,
    client: OllamaClient | None = None,
) -> AgentResult:
    if mode not in MODE_INSTRUCTIONS:
        choices = ", ".join(sorted(MODE_INSTRUCTIONS))
        raise ValueError(f"Unknown mode {mode!r}. Choose one of: {choices}")

    repo = repo.resolve()
    repo_context = build_repo_context(
        repo,
        task=task,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
    )
    context = format_repo_context(repo_context)
    design_system = load_design_system(repo)
    memory = load_memory(repo)
    user_prompt = f"""Mode:
{mode}

Mode instructions:
{MODE_INSTRUCTIONS[mode]}

Design system:
{design_system}

Ares memory:
{memory}

Task:
{task}

Repository context:
{context}

Now answer this exact task:
{task}
"""

    client = client or OllamaClient()
    response = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        num_ctx=num_ctx,
    )
    session = append_agent_session(
        repo,
        model=model,
        mode=mode,
        task=task,
        prompt=user_prompt,
        response=response,
        included_files=len(repo_context.files),
        total_files=repo_context.total_files,
    )
    return AgentResult(
        response=response,
        prompt=user_prompt,
        mode=mode,
        model=model,
        included_files=len(repo_context.files),
        total_files=repo_context.total_files,
        session=session,
    )
