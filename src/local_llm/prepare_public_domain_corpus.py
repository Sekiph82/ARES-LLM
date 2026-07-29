from __future__ import annotations

import argparse
import re
import urllib.request
from pathlib import Path


DEFAULT_URLS = [
    "https://www.gutenberg.org/cache/epub/11/pg11.txt",
    "https://www.gutenberg.org/cache/epub/84/pg84.txt",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and clean public-domain text for Ares training.")
    parser.add_argument("--url", action="append", default=[], help="Public-domain plain-text URL. Can be repeated.")
    parser.add_argument("--output", type=Path, default=Path("data/public_domain_corpus.txt"))
    parser.add_argument("--max-chars", type=int, default=2_000_000)
    return parser.parse_args()


def download_text(url: str, timeout: int = 60) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Ares local training corpus builder"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_gutenberg_text(text: str) -> str:
    start_match = re.search(r"\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*?\*\*\*", text, re.I | re.S)
    end_match = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*", text, re.I | re.S)
    if start_match:
        text = text[start_match.end() :]
        end_match = re.search(r"\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK.*", text, re.I | re.S)
    if end_match:
        text = text[: end_match.start()]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip() + "\n"


def build_public_domain_corpus(urls: list[str], max_chars: int) -> str:
    chunks = []
    for url in urls:
        chunks.append(f"\n\n# Source: {url}\n")
        chunks.append(clean_gutenberg_text(download_text(url)))
        if sum(len(chunk) for chunk in chunks) >= max_chars:
            break
    return "".join(chunks)[:max_chars].strip() + "\n"


def main() -> None:
    args = parse_args()
    urls = args.url or DEFAULT_URLS
    args.output.parent.mkdir(parents=True, exist_ok=True)
    corpus = build_public_domain_corpus(urls, args.max_chars)
    args.output.write_text(corpus, encoding="utf-8")
    print(f"Wrote {len(corpus):,} public-domain characters to {args.output}")


if __name__ == "__main__":
    main()
