from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str | None = None
    confidence: float | None = None


@runtime_checkable
class SpeechToText(Protocol):
    """Abstraction over speech-to-text backends.

    Implementations must be async and must not block the event loop.
    """

    async def transcribe(self, audio: bytes) -> TranscriptionResult: ...
