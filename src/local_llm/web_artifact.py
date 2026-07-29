from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from local_llm.agent_core import DEFAULT_MODEL
from local_llm.design_system import load_design_system
from local_llm.ollama_client import OllamaClient


FILE_BLOCK_RE = re.compile(
    r"^--- FILE: (?P<path>[A-Za-z0-9_./ -]+) ---\s*\n(?P<content>.*?)\n--- END FILE ---",
    re.MULTILINE | re.DOTALL,
)
FENCED_FILE_RE = re.compile(
    r"^(?:#{1,6}\s*)?(?:FILE:\s*)?(?P<path>[A-Za-z0-9_./ -]+\.(?:html|css|js|json|md|txt|svg)):?\s*\n"
    r"```[A-Za-z0-9_+-]*\s*\n(?P<content>.*?)\n```",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
FENCE_WITH_PATH_RE = re.compile(
    r"^```[A-Za-z0-9_+-]*\s+(?P<path>[A-Za-z0-9_./ -]+\.(?:html|css|js|json|md|txt|svg))\s*\n"
    r"(?P<content>.*?)\n```",
    re.IGNORECASE | re.MULTILINE | re.DOTALL,
)
SAFE_EXTENSIONS = {".html", ".css", ".js", ".json", ".md", ".txt", ".svg"}
REQUIRED_FILES = {"index.html", "styles.css", "app.js", "README.md"}


@dataclass(frozen=True)
class ArtifactFile:
    path: str
    content: str


@dataclass(frozen=True)
class WebArtifactResult:
    root: Path
    files: list[ArtifactFile]
    used_fallback: bool
    quality_issues: list[str]
    model_response: str

    @property
    def entry_file(self) -> Path:
        return self.root / "index.html"


def slugify(text: str, fallback: str = "ares-web-app") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:48].strip("-") or fallback)


def is_safe_artifact_path(path: str) -> bool:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    if candidate.suffix.lower() not in SAFE_EXTENSIONS:
        return False
    return len(candidate.parts) <= 3


def parse_artifact_files(response: str) -> list[ArtifactFile]:
    files: list[ArtifactFile] = []
    seen: set[str] = set()
    patterns = (FILE_BLOCK_RE, FENCED_FILE_RE, FENCE_WITH_PATH_RE)
    for pattern in patterns:
        for match in pattern.finditer(response):
            add_artifact_file(files, seen, match.group("path"), match.group("content"))
    return files


def add_artifact_file(files: list[ArtifactFile], seen: set[str], path: str, content: str) -> None:
    normalized_path = path.strip().replace("\\", "/")
    normalized_content = content.strip() + "\n"
    if not is_safe_artifact_path(normalized_path) or normalized_path in seen:
        return
    files.append(ArtifactFile(path=normalized_path, content=normalized_content))
    seen.add(normalized_path)


def has_required_files(files: list[ArtifactFile]) -> bool:
    return REQUIRED_FILES.issubset({file.path for file in files})


def quality_issues(files: list[ArtifactFile]) -> list[str]:
    by_path = {file.path: file.content for file in files}
    issues: list[str] = []
    if not has_required_files(files):
        issues.append("missing required files")
        return issues

    html = by_path["index.html"].lower()
    css = by_path["styles.css"].lower()
    js = by_path["app.js"].lower()

    if "styles.css" not in html or "app.js" not in html:
        issues.append("html does not wire css and javascript")
    if len(by_path["styles.css"]) < 2200:
        issues.append("css is too thin for a polished responsive UI")
    if len(by_path["app.js"]) < 900:
        issues.append("javascript is too thin for a dynamic app")
    if "addeventlistener" not in js and "onclick" not in js:
        issues.append("javascript has no clear interaction handlers")
    if "@media" not in css:
        issues.append("css has no responsive media query")
    if css.count("#") < 6:
        issues.append("visual palette is underdeveloped")
    return issues


def build_generation_prompt(brief: str, design_system: str) -> str:
    return f"""You are Ares, a local coding and design agent.
Create a polished, dynamic, self-contained website or app from the brief.

Follow this design contract:
{design_system}

Brief:
{brief}

Return exactly these files using this format:
--- FILE: index.html ---
...content...
--- END FILE ---
--- FILE: styles.css ---
...content...
--- END FILE ---
--- FILE: app.js ---
...content...
--- END FILE ---
--- FILE: README.md ---
...content...
--- END FILE ---

Rules:
- Do not wrap the answer in Markdown fences.
- Use real HTML, CSS, and JavaScript.
- The artifact must run by opening index.html.
- Include real interactions and realistic sample content.
- Keep the UI responsive and visually polished.
"""


def fallback_files(brief: str) -> list[ArtifactFile]:
    title = title_from_brief(brief)
    safe_title = escape(title)
    safe_brief = escape(brief)
    return [
        ArtifactFile(
            "index.html",
            f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="app-shell">
    <header class="topbar">
      <div>
        <p class="eyebrow">Ares generated app</p>
        <h1>{safe_title}</h1>
      </div>
      <button id="themeToggle" class="icon-button" aria-label="Toggle contrast">Contrast</button>
    </header>

    <section class="workspace">
      <aside class="panel controls">
        <label>
          Project brief
          <textarea id="briefInput" rows="6">{safe_brief}</textarea>
        </label>
        <label>
          Focus
          <select id="focusSelect">
            <option value="build">Build</option>
            <option value="design">Design</option>
            <option value="launch">Launch</option>
          </select>
        </label>
        <label>
          Intensity
          <input id="intensity" type="range" min="1" max="5" value="3">
        </label>
        <button id="generateBtn">Generate plan</button>
      </aside>

      <section class="panel preview">
        <div class="preview-header">
          <h2>Live Plan</h2>
          <span id="scoreBadge">Ready</span>
        </div>
        <div id="planList" class="plan-list"></div>
      </section>
    </section>

    <section class="metrics">
      <article><strong id="metricPages">4</strong><span>screens</span></article>
      <article><strong id="metricTasks">12</strong><span>tasks</span></article>
      <article><strong id="metricScore">86</strong><span>design score</span></article>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
""",
        ),
        ArtifactFile(
            "styles.css",
            """* {
  box-sizing: border-box;
}

:root {
  --bg: #f4f5f7;
  --surface: #ffffff;
  --text: #16191d;
  --muted: #66707c;
  --border: #d9dde3;
  --accent: #b3202a;
  --info: #2364aa;
  --success: #1c7c54;
  --shadow: 0 18px 45px rgba(16, 24, 40, 0.08);
}

body.high-contrast {
  --bg: #101216;
  --surface: #181c22;
  --text: #f6f7f9;
  --muted: #b8c0ca;
  --border: #343b46;
  --accent: #ff4d5b;
}

body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, Segoe UI, Arial, sans-serif;
}

button,
select,
textarea,
input {
  font: inherit;
}

.app-shell {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 28px 0;
}

.topbar,
.workspace,
.metrics {
  display: grid;
  gap: 16px;
}

.topbar {
  grid-template-columns: 1fr auto;
  align-items: center;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2 {
  margin: 0;
  letter-spacing: 0;
}

h1 {
  font-size: clamp(30px, 4vw, 56px);
  line-height: 1;
}

h2 {
  font-size: 20px;
}

.icon-button,
button {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--text);
  color: var(--surface);
  cursor: pointer;
  min-height: 42px;
  padding: 0 14px;
}

.workspace {
  grid-template-columns: 340px 1fr;
  align-items: stretch;
}

.panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow);
}

.controls {
  display: grid;
  gap: 14px;
  padding: 18px;
}

label {
  display: grid;
  gap: 7px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

textarea,
select,
input[type="range"] {
  width: 100%;
}

textarea,
select {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  padding: 11px;
}

.preview {
  background: transparent;
  border: 0;
  box-shadow: none;
  min-height: 430px;
  padding: 0;
}

.preview-header,
.plan-item,
.metrics {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
}

#scoreBadge {
  border-radius: 999px;
  background: rgba(179, 32, 42, 0.12);
  color: var(--accent);
  font-size: 12px;
  font-weight: 800;
  padding: 7px 10px;
}

.plan-list {
  display: grid;
  gap: 12px;
  margin-top: 18px;
}

.plan-item {
  border: 1px solid var(--border);
  border-radius: 8px;
  min-height: 76px;
  padding: 14px;
}

.plan-item p {
  margin: 4px 0 0;
  color: var(--muted);
}

.plan-item span {
  color: var(--info);
  font-weight: 800;
}

.metrics {
  grid-template-columns: repeat(3, 1fr);
  margin-top: 16px;
}

.metrics article {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 18px;
}

.metrics strong {
  display: block;
  font-size: 28px;
}

.metrics span {
  color: var(--muted);
}

@media (max-width: 820px) {
  .workspace,
  .topbar,
  .metrics {
    grid-template-columns: 1fr;
  }
}
""",
        ),
        ArtifactFile(
            "app.js",
            """const planList = document.querySelector("#planList");
const briefInput = document.querySelector("#briefInput");
const focusSelect = document.querySelector("#focusSelect");
const intensity = document.querySelector("#intensity");
const generateBtn = document.querySelector("#generateBtn");
const scoreBadge = document.querySelector("#scoreBadge");
const themeToggle = document.querySelector("#themeToggle");

const focusTasks = {
  build: ["Map the user journey", "Create the primary workflow", "Add responsive states", "Run a launch checklist"],
  design: ["Define visual hierarchy", "Tune spacing and contrast", "Add interaction feedback", "Polish mobile layout"],
  launch: ["Write release copy", "Prepare analytics events", "Check accessibility", "Package the final files"],
};

function renderPlan() {
  const focus = focusSelect.value;
  const level = Number(intensity.value);
  const tasks = focusTasks[focus];
  planList.innerHTML = "";
  tasks.forEach((task, index) => {
    const item = document.createElement("article");
    item.className = "plan-item";
    item.innerHTML = `
      <div>
        <strong>${task}</strong>
        <p>${briefInput.value.slice(0, 120) || "No brief entered yet."}</p>
      </div>
      <span>${index + level}/5</span>
    `;
    planList.appendChild(item);
  });
  const score = Math.min(99, 72 + level * 5 + focus.length);
  scoreBadge.textContent = `${score}% ready`;
  document.querySelector("#metricScore").textContent = score;
  document.querySelector("#metricTasks").textContent = tasks.length * level;
}

generateBtn.addEventListener("click", renderPlan);
focusSelect.addEventListener("change", renderPlan);
intensity.addEventListener("input", renderPlan);
themeToggle.addEventListener("click", () => {
  document.body.classList.toggle("high-contrast");
});

renderPlan();
""",
        ),
        ArtifactFile(
            "README.md",
            f"""# {title}

Generated by Ares as a local dynamic website/app artifact.

Open `index.html` in a browser. The app is self-contained and includes
responsive layout, controls, dynamic rendering, and a contrast mode.

## Original Brief

{brief}
""",
        ),
    ]


def title_from_brief(brief: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", brief)
    if not words:
        return "Ares Dynamic App"
    return " ".join(words[:6]).title()


def write_artifact_files(root: Path, files: list[ArtifactFile], manifest: dict[str, object]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for file in files:
        target = root / file.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file.content, encoding="utf-8")
    (root / "ares-artifact.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def create_web_artifact(
    brief: str,
    repo: Path,
    model: str = DEFAULT_MODEL,
    client: OllamaClient | None = None,
) -> WebArtifactResult:
    repo = repo.resolve()
    design_system = load_design_system(repo)
    prompt = build_generation_prompt(brief, design_system)
    client = client or OllamaClient(timeout=300)

    response = ""
    files: list[ArtifactFile] = []
    used_fallback = False
    try:
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You create complete local frontend artifacts as plain files.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.35,
            num_ctx=8192,
        )
        files = parse_artifact_files(response)
    except Exception as exc:
        response = f"Ares model generation failed: {exc}"

    issues = quality_issues(files)
    if issues:
        files = fallback_files(brief)
        used_fallback = True
        issues = quality_issues(files)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root = repo / "artifacts" / f"{slugify(brief)}-{timestamp}"
    manifest = {
        "name": root.name,
        "kind": "web-app",
        "entry_file": "index.html",
        "created_at": timestamp,
        "brief": brief,
        "model": model,
        "used_fallback": used_fallback,
        "quality_issues": issues,
        "files": [file.path for file in files],
    }
    write_artifact_files(root, files, manifest)
    return WebArtifactResult(
        root=root,
        files=files,
        used_fallback=used_fallback,
        quality_issues=issues,
        model_response=response,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local dynamic website/app artifact with Ares.")
    parser.add_argument("brief", nargs="+", help="Website or app brief.")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = create_web_artifact(" ".join(args.brief), repo=args.repo, model=args.model)
    print(f"Created artifact: {result.root}")
    print(f"Entry file: {result.entry_file}")
    if result.used_fallback:
        print("Used the built-in polished template because the model output did not pass the artifact gate.")


if __name__ == "__main__":
    main()
