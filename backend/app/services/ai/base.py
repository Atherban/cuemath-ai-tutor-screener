from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class AIResponse:
    text: str
    finish_reason: str = "stop"
    usage: dict[str, int] | None = None


@runtime_checkable
class AIProvider(Protocol):
    """Abstraction over any chat-capable language model backend.

    The interview engine depends only on this protocol, never on a vendor SDK.
    `max_tokens` overrides the configured default when provided.
    """

    async def generate_response(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AIResponse: ...

    async def generate_text(
        self,
        prompt: str,
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str: ...
