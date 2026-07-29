from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DIFF_BLOCK_RE = re.compile(r"```(?:diff|patch)\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class PatchBundle:
    patches: list[str]

    @property
    def has_patches(self) -> bool:
        return bool(self.patches)


def extract_unified_diffs(text: str) -> PatchBundle:
    patches = [block.strip() + "\n" for block in DIFF_BLOCK_RE.findall(text) if looks_like_diff(block)]
    if not patches and looks_like_diff(text):
        patches = [text.strip() + "\n"]
    return PatchBundle(patches=patches)


def looks_like_diff(text: str) -> bool:
    return ("diff --git " in text and "@@" in text) or ("--- " in text and "+++ " in text and "@@" in text)


def save_patches(bundle: PatchBundle, out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, patch in enumerate(bundle.patches, start=1):
        path = out_dir / f"{stem}-{index}.patch"
        path.write_text(patch, encoding="utf-8")
        paths.append(path)
    return paths
