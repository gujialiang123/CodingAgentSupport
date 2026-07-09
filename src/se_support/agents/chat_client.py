"""Chat-client abstraction so the agent loop is model-agnostic and testable.

* :class:`OpenAIChatClient` talks to any OpenAI-compatible endpoint -- including a
  local vLLM server (``--base-url http://localhost:8000/v1``) or a hosted API.
  Switching from the 4090 smoke model to a pinned API snapshot is a one-line
  config change, exactly as planned.
* :class:`ScriptedChatClient` replays a fixed list of responses, so the agent
  loop and support conditions can be tested with **no GPU and no network**.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ChatClient(Protocol):
    model: str

    def complete(self, messages: list[dict[str, str]]) -> str:
        ...


class ScriptedChatClient:
    """Returns preset responses in order (for tests)."""

    def __init__(self, responses: list[str], model: str = "scripted") -> None:
        self._responses = list(responses)
        self._i = 0
        self.model = model

    def complete(self, messages: list[dict[str, str]]) -> str:
        if self._i >= len(self._responses):
            return "SUBMIT"
        resp = self._responses[self._i]
        self._i += 1
        return resp


class OpenAIChatClient:
    """OpenAI-compatible client (works against vLLM's OpenAI server)."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - exercised only with the extra
            raise ImportError(
                "openai package required for OpenAIChatClient; install `.[llm]`"
            ) from exc
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = OpenAI(base_url=base_url, api_key=api_key or "EMPTY")

    def complete(self, messages: list[dict[str, str]]) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return resp.choices[0].message.content or ""
