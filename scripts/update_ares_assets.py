from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update Ares PNG and ICO assets from a source image.")
    parser.add_argument("--source", type=Path, default=Path.home() / "Desktop" / "Ares images.png")
    parser.add_argument("--assets-dir", type=Path, default=Path("assets"))
    parser.add_argument(
        "--desktop-symbol-ratio",
        type=float,
        default=0.76,
        help="How much of the full logo height to keep for the desktop icon symbol crop.",
    )
    return parser.parse_args()


def content_bbox(image: Image.Image, *, alpha_threshold: int = 32, coverage: float = 0.006) -> tuple[int, int, int, int]:
    alpha = np.asarray(image.getchannel("A"))
    mask = alpha > alpha_threshold
    if not mask.any():
        return (0, 0, image.width, image.height)

    rows = mask.sum(axis=1)
    cols = mask.sum(axis=0)
    row_threshold = max(2, int(image.width * coverage))
    col_threshold = max(2, int(image.height * coverage))

    ys = np.where(rows >= row_threshold)[0]
    xs = np.where(cols >= col_threshold)[0]
    if ys.size == 0 or xs.size == 0:
        bbox = Image.fromarray(mask.astype("uint8") * 255).getbbox()
        return bbox or (0, 0, image.width, image.height)

    return (int(xs[0]), int(ys[0]), int(xs[-1] + 1), int(ys[-1] + 1))


def trim_content(image: Image.Image) -> Image.Image:
    return image.crop(content_bbox(image))


def fit_canvas(image: Image.Image, size: tuple[int, int], *, fill: float = 0.96) -> Image.Image:
    base = image.copy()
    base.thumbnail((int(size[0] * fill), int(size[1] * fill)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (255, 255, 255, 0))
    canvas.alpha_composite(base, ((size[0] - base.width) // 2, (size[1] - base.height) // 2))
    return canvas


def desktop_symbol(full_logo: Image.Image, symbol_ratio: float) -> Image.Image:
    left, top, right, bottom = content_bbox(full_logo)
    height = bottom - top
    symbol_bottom = top + int(height * symbol_ratio)
    symbol_bottom = max(top + 1, min(symbol_bottom, bottom))
    symbol = full_logo.crop((left, top, right, symbol_bottom))
    return trim_content(symbol)


def main() -> None:
    args = parse_args()
    args.assets_dir.mkdir(parents=True, exist_ok=True)

    image = Image.open(args.source).convert("RGBA")
    image = trim_content(image)

    logo = fit_canvas(image, (260, 220), fill=0.96)
    logo.save(args.assets_dir / "ares_logo.png")

    desktop_mark = desktop_symbol(image, args.desktop_symbol_ratio)
    desktop_preview = fit_canvas(desktop_mark, (256, 256), fill=0.98)
    desktop_preview.save(args.assets_dir / "ares_desktop_icon.png")
    desktop_preview.save(
        args.assets_dir / "ares_desktop.ico",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    icon = fit_canvas(desktop_mark, (256, 256), fill=0.98)
    icon.save(
        args.assets_dir / "ares.ico",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )

    print(f"Updated Ares assets from {args.source}")


if __name__ == "__main__":
    main()
