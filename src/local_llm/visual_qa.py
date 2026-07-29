from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class VisualQAResult:
    ok: bool
    skipped: bool
    screenshots: list[str]
    issues: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_visual_qa(entry_file: Path, out_dir: Path) -> VisualQAResult:
    try:
        from PIL import Image
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        return VisualQAResult(
            ok=True,
            skipped=True,
            screenshots=[],
            issues=[f"Visual QA skipped because optional browser dependencies are unavailable: {exc}"],
        )

    screenshots_dir = out_dir / "visual-qa"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    screenshots: list[str] = []
    issues: list[str] = []
    viewports = {"desktop": (1440, 1000), "mobile": (390, 844)}

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            for name, (width, height) in viewports.items():
                page = browser.new_page(viewport={"width": width, "height": height})
                page.goto(entry_file.resolve().as_uri(), wait_until="networkidle")
                screenshot_path = screenshots_dir / f"{name}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                screenshots.append(str(screenshot_path))
                if is_blank_image(screenshot_path, Image):
                    issues.append(f"{name} screenshot appears blank")
                page.close()
            browser.close()
    except Exception as exc:
        return VisualQAResult(ok=False, skipped=False, screenshots=screenshots, issues=[str(exc)])

    return VisualQAResult(ok=not issues, skipped=False, screenshots=screenshots, issues=issues)


def is_blank_image(path: Path, image_module) -> bool:
    image = image_module.open(path).convert("RGB")
    extrema = image.getextrema()
    flat_channels = [high - low for low, high in extrema]
    return max(flat_channels) < 8
