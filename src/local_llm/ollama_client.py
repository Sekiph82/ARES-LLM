from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaClient:
    base_url: str = "http://127.0.0.1:11434"
    timeout: float = 300.0

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        num_ctx: int = 8192,
    ) -> str:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }
        data = self._post_json("/api/chat", payload)
        try:
            return data["message"]["content"]
        except KeyError as exc:
            raise RuntimeError(f"Unexpected Ollama response: {data}") from exc

    def list_models(self) -> list[str]:
        data = self._get_json("/api/tags")
        return [model["name"] for model in data.get("models", [])]

    def _post_json(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return self._open_json(request)

    def _get_json(self, path: str) -> dict:
        request = urllib.request.Request(f"{self.base_url}{path}", method="GET")
        return self._open_json(request)

    def _open_json(self, request: urllib.request.Request) -> dict:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise RuntimeError(
                f"Ollama did not respond within {self.timeout:.0f} seconds. "
                "Try a shorter prompt, fewer context files, or close other running Ares requests."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Could not connect to Ollama. Start it with `ollama serve` or open the Ollama app."
            ) from exc
