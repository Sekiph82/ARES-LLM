from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CharTokenizer:
    """A minimal character-level tokenizer for first LLM experiments."""

    stoi: dict[str, int]
    itos: dict[int, str]

    @classmethod
    def from_text(cls, text: str) -> "CharTokenizer":
        chars = sorted(set(text))
        stoi = {ch: idx for idx, ch in enumerate(chars)}
        itos = {idx: ch for ch, idx in stoi.items()}
        return cls(stoi=stoi, itos=itos)

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def encode(self, text: str) -> list[int]:
        missing = sorted(set(text) - set(self.stoi))
        if missing:
            printable = ", ".join(repr(ch) for ch in missing[:5])
            raise ValueError(f"Text contains characters outside the vocabulary: {printable}")
        return [self.stoi[ch] for ch in text]

    def decode(self, token_ids: list[int] | tuple[int, ...]) -> str:
        try:
            return "".join(self.itos[int(idx)] for idx in token_ids)
        except KeyError as exc:
            raise ValueError(f"Token id {exc.args[0]} is outside the vocabulary") from exc

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"itos": {str(idx): ch for idx, ch in self.itos.items()}}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CharTokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        itos = {int(idx): ch for idx, ch in payload["itos"].items()}
        stoi = {ch: idx for idx, ch in itos.items()}
        return cls(stoi=stoi, itos=itos)
