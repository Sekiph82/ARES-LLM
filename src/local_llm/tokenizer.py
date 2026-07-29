from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class Tokenizer(Protocol):
    @property
    def vocab_size(self) -> int: ...

    def encode(self, text: str) -> list[int]: ...

    def decode(self, token_ids: list[int] | tuple[int, ...]) -> str: ...

    def encode_with_spans(self, text: str) -> tuple[list[int], list[tuple[int, int]]]: ...

    def save(self, path: str | Path) -> None: ...


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

    def encode_with_spans(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        return self.encode(text), [(idx, idx + 1) for idx in range(len(text))]

    def decode(self, token_ids: list[int] | tuple[int, ...]) -> str:
        try:
            return "".join(self.itos[int(idx)] for idx in token_ids)
        except KeyError as exc:
            raise ValueError(f"Token id {exc.args[0]} is outside the vocabulary") from exc

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"type": "char", "itos": {str(idx): ch for idx, ch in self.itos.items()}}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "CharTokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        itos = {int(idx): ch for idx, ch in payload["itos"].items()}
        stoi = {ch: idx for idx, ch in itos.items()}
        return cls(stoi=stoi, itos=itos)


@dataclass(frozen=True)
class BPETokenizer:
    """A compact character-pair BPE tokenizer for laptop-scale experiments."""

    stoi: dict[str, int]
    itos: dict[int, str]
    merges: tuple[tuple[str, str], ...]

    @classmethod
    def train(cls, text: str, vocab_size: int = 512, min_pair_freq: int = 2) -> "BPETokenizer":
        if not text:
            raise ValueError("Cannot train a BPE tokenizer on empty text.")
        tokens = list(text)
        vocab = set(tokens)
        merges: list[tuple[str, str]] = []
        target_vocab_size = max(len(vocab), vocab_size)

        while len(vocab) < target_vocab_size:
            counts: dict[tuple[str, str], int] = {}
            for left, right in zip(tokens, tokens[1:]):
                counts[(left, right)] = counts.get((left, right), 0) + 1
            if not counts:
                break
            best_pair, best_count = max(counts.items(), key=lambda item: (item[1], item[0]))
            if best_count < min_pair_freq:
                break
            merged = "".join(best_pair)
            tokens = merge_tokens(tokens, best_pair, merged)
            vocab.add(merged)
            merges.append(best_pair)

        ordered_vocab = sorted(vocab, key=lambda value: (len(value), value))
        stoi = {token: idx for idx, token in enumerate(ordered_vocab)}
        itos = {idx: token for token, idx in stoi.items()}
        return cls(stoi=stoi, itos=itos, merges=tuple(merges))

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def encode(self, text: str) -> list[int]:
        ids, _ = self.encode_with_spans(text)
        return ids

    def encode_with_spans(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        missing = sorted(set(text) - {token for token in self.stoi if len(token) == 1})
        if missing:
            printable = ", ".join(repr(ch) for ch in missing[:5])
            raise ValueError(f"Text contains characters outside the vocabulary: {printable}")

        tokens = list(text)
        spans = [(idx, idx + 1) for idx in range(len(text))]
        for left, right in self.merges:
            merged = left + right
            tokens, spans = merge_tokens_with_spans(tokens, spans, (left, right), merged)
        return [self.stoi[token] for token in tokens], spans

    def decode(self, token_ids: list[int] | tuple[int, ...]) -> str:
        try:
            return "".join(self.itos[int(idx)] for idx in token_ids)
        except KeyError as exc:
            raise ValueError(f"Token id {exc.args[0]} is outside the vocabulary") from exc

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "type": "bpe",
            "itos": {str(idx): token for idx, token in self.itos.items()},
            "merges": [list(pair) for pair in self.merges],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "BPETokenizer":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        itos = {int(idx): token for idx, token in payload["itos"].items()}
        stoi = {token: idx for idx, token in itos.items()}
        merges = tuple((str(left), str(right)) for left, right in payload.get("merges", []))
        return cls(stoi=stoi, itos=itos, merges=merges)


def merge_tokens(tokens: list[str], pair: tuple[str, str], merged: str) -> list[str]:
    return merge_tokens_with_spans(tokens, [(0, 0)] * len(tokens), pair, merged)[0]


def merge_tokens_with_spans(
    tokens: list[str],
    spans: list[tuple[int, int]],
    pair: tuple[str, str],
    merged: str,
) -> tuple[list[str], list[tuple[int, int]]]:
    next_tokens: list[str] = []
    next_spans: list[tuple[int, int]] = []
    idx = 0
    while idx < len(tokens):
        if idx + 1 < len(tokens) and (tokens[idx], tokens[idx + 1]) == pair:
            next_tokens.append(merged)
            next_spans.append((spans[idx][0], spans[idx + 1][1]))
            idx += 2
        else:
            next_tokens.append(tokens[idx])
            next_spans.append(spans[idx])
            idx += 1
    return next_tokens, next_spans


def build_tokenizer(text: str, kind: str = "char", bpe_vocab_size: int = 512) -> Tokenizer:
    if kind == "char":
        return CharTokenizer.from_text(text)
    if kind == "bpe":
        return BPETokenizer.train(text, vocab_size=bpe_vocab_size)
    raise ValueError(f"Unknown tokenizer kind: {kind}")


def load_tokenizer(path: str | Path) -> Tokenizer:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    kind = payload.get("type", "char")
    if kind == "char":
        return CharTokenizer.load(path)
    if kind == "bpe":
        return BPETokenizer.load(path)
    raise ValueError(f"Unknown tokenizer type in {path}: {kind}")
